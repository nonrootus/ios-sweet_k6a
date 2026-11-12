"""Patch 0208: GPU buffers come from wired system memory entered into the GPU window, as on K20.

Every recent boot (0205..0207g) ran the fixed 256 MiB pinned pool out within 100..280 frames:
'BO pool has no contiguous range' (e.g. 768 units wanted with 1673 free), 19..29 GL out-of-memory
errors, layers dropping out, and twice backboardd crashing on a failed allocation (the freezes).
A BO had to be one contiguous run of the pool because its GPU VA was its pool offset.

Now GEM_NEW first takes a write-combined IOBufferMemoryDescriptor of its own and enters its pages
into the 512 MiB window of 0206/0207 (no physical contiguity; a cleared VA range is reused only
after a TLB invalidation). Only if that fails does it fall back to the pool. Command buffers may
live there too, so sweet_a618_render_submit accepts IBs in either range. Submissions are still
synchronous and hold the client lock, so the GPU is idle when a BO is closed.
"""
import re
import subprocess
import tempfile
from pathlib import Path

REPO = Path('D:/ios-sweet/src/ios-sweet')
GIT = ['git', '-c', 'core.autocrlf=false', '-c', 'core.safecrlf=false']
NAME = '0208-sweet-a618-system-memory-buffers.patch'
FILES = {
    'iokit/Kernel/arm/SweetAdreno.cpp': 'xnu/gpu/SweetAdreno.cpp',
    'iokit/Kernel/arm/sweet_a618_renderer.inc': 'xnu/gpu/sweet_a618_renderer.inc',
}
base = {m: subprocess.check_output(GIT + ['show', 'HEAD:' + m], cwd=REPO).decode() for m in FILES.values()}
new = dict(base)


def edit(mirror, before, after):
    path = 'xnu/gpu/' + mirror
    assert new[path].count(before) == 1, (mirror, new[path].count(before), before[:80])
    new[path] = new[path].replace(before, after)


A = 'SweetAdreno.cpp'
edit(A, '''    unsigned pool_first, pool_units;
''', '''    unsigned pool_first, pool_units;
    IOBufferMemoryDescriptor *backing;  /* a window BO's own memory */
''')
edit(A, '''        return initPoolRange(address,0,units) && (pool_units=0,true);
    }
''', '''        return initPoolRange(address,0,units) && (pool_units=0,true);
    }

    /* Wired, write-combined memory of its own (a window BO): released with the BO. */
    bool initBacking(IOBufferMemoryDescriptor *buffer,unsigned units)
    {
        if(!initPoolRange(buffer->getBytesNoCopy(),0,units))return false;
        pool_units=0;
        backing=buffer;
        buffer->retain();
        return true;
    }
''')
edit(A, '''        const unsigned first=pool_first, units=pool_units;
        IOGeneralMemoryDescriptor::free();
        if(units)pool_return(first,units);
''', '''        const unsigned first=pool_first, units=pool_units;
        IOBufferMemoryDescriptor *own=backing;
        backing=nullptr;
        IOGeneralMemoryDescriptor::free();
        if(units)pool_return(first,units);
        if(own)own->release();
''')
edit(A, '''    void dropBO(sweet_bo *bo);
''', '''    void dropBO(sweet_bo *bo);
    IOReturn newWindowBO(uint64_t bytes,uint32_t flags,uint32_t *handle);
''')
edit(A, '''    auto *memory=bo->memory;
    if(bo->surface)import_release(*bo);
    bo->memory=nullptr;
    memory->release();
}
''', r'''    auto *memory=bo->memory;
    if(bo->surface){
        import_release(*bo);
    }else if(bo->import_pages){
        /* A window BO: its leaves go now; its VA range waits for the next invalidation. */
        sweet_a618_import_unmap(bo->import_first,bo->import_pages);
        import_forget(bo->import_first,bo->import_pages,true);
        window_bytes-=bo->size;
        window_bos--;
    }
    bo->memory=nullptr;
    memory->release();
}

/*
 * A BO of wired system memory, write-combined like the pool, entered page by page into the GPU
 * window: no contiguous run of the pinned pool is needed, and the pool no longer bounds the total.
 * kIOReturnUnsupported or kIOReturnNoMemory: the caller falls back to the pool.
 */
IOReturn SweetAdrenoUserClient::newWindowBO(uint64_t bytes,uint32_t flags,uint32_t *handle_out)
{
    if(!sweet_a618_import_ready() || !bytes || (bytes&16383u) || bytes>static_cast<uint64_t>(kImportPages)*4096u)
        return kIOReturnUnsupported;
    auto *buffer=IOBufferMemoryDescriptor::inTaskWithOptions(kernel_task,
        kIODirectionInOut | kIOMemoryMapperNone | kIOMapWriteCombineCache,bytes,16384u);
    void *cpu=buffer ? buffer->getBytesNoCopy():nullptr;
    auto *bo=cpu ? OSTypeAlloc(SweetAdrenoBO):nullptr;
    if(!bo || !bo->initBacking(buffer,static_cast<unsigned>(bytes/16384u))){
        if(bo)bo->release();
        if(buffer)buffer->release();
        return kIOReturnNoMemory;
    }
    buffer->release(); // the BO holds it
    const unsigned pages=static_cast<unsigned>(bytes/4096u);
    const size_t list_bytes=pages*sizeof(uint64_t);
    auto *physical=static_cast<uint64_t *>(IOMallocData(list_bytes));
    bool ok=physical!=nullptr;
    for(unsigned i=0;ok && i<pages;i++){
        IOByteCount length=0;
        const addr64_t page=buffer->getPhysicalSegment(static_cast<IOByteCount>(i)*4096u,&length,kIOMemoryMapperNone);
        ok=page && !(page&4095u) && length>=4096u;
        physical[i]=page;
    }
    bzero(cpu,bytes);
    __asm__ volatile("dsb sy" ::: "memory"); // Cleared in memory before the GPU can see it.
    int first=-1;
    if(ok){
        IOLockLock(pool_lock);
        first=import_reserve(pages);
        IOLockUnlock(pool_lock);
    }
    const bool mapped=first>=0 && !sweet_a618_import_map(static_cast<unsigned>(first),physical,pages);
    if(physical)IOFreeData(physical,list_bytes);
    if(!mapped){
        if(first>=0)import_forget(static_cast<unsigned>(first),pages,false);
        static unsigned refused;
        if(refused++<8)IOLog("SWEET CA: window BO of %llu KB refused (%s); pool used instead, %u window BOs, %llu MB\n",
            bytes>>10,!ok ? "no physical pages" : first<0 ? "no room in the window" : "leaves refused",
            window_bos,window_bytes>>20);
        bo->release();
        return kIOReturnNoMemory;
    }
    sweet_bo entry={bo,bytes,SWEET_A618_IMPORT_IOVA+static_cast<uint64_t>(first)*4096u,flags,
        nullptr,static_cast<unsigned>(first),pages,0,0};
    unsigned handle=0;
    IOLockLock(lock);
    for(unsigned i=0;i<kHandles;i++){
        unsigned candidate=(next_handle+i)%kHandles;
        if(!bos[candidate].memory){handle=candidate+1;break;}
    }
    window_bos++;
    window_bytes+=bytes;
    if(handle){
        bos[handle-1]=entry;
        next_handle=handle%kHandles;
    }else{
        dropBO(&entry);
    }
    IOLockUnlock(lock);
    if(!handle)return kIOReturnNoMemory;
    *handle_out=handle;
    window_made++;
    if(window_logs<8 || window_made%1024==0){
        window_logs++;
        IOLog("SWEET CA: window BO %llu KB at GPU VA %llx; %u window BOs, %llu MB; %u made\n",
            bytes>>10,static_cast<unsigned long long>(entry.iova),window_bos,window_bytes>>20,window_made);
    }
    return kIOReturnSuccess;
}
''')
edit(A, '''static unsigned import_count,import_logs,import_flushes;
''', '''static unsigned import_count,import_logs,import_flushes;
static unsigned window_bos,window_logs,window_made;   /* BOs of system memory in the window */
static uint64_t window_bytes;
''')
edit(A, '''        const unsigned units=static_cast<unsigned>(bytes/16384u);
''', '''        /* System memory in the GPU window first; a contiguous run of the pinned pool if that fails. */
        if(newWindowBO(bytes,r.gem_new.flags,&r.gem_new.handle)==kIOReturnSuccess)break;
        const unsigned units=static_cast<unsigned>(bytes/16384u);
''')
edit('sweet_a618_renderer.inc', '''        const uint64_t base=SWEET_A618_RENDER_IOVA;
        const uint64_t end=base+SWEET_A618_RENDER_BYTES;
        const uint64_t bytes=static_cast<uint64_t>(dwords[i])*4;
''', '''        /* Command buffers live in the pinned pool or in the window of system memory (SweetAdreno.cpp). */
        const bool pool=iova[i]>=SWEET_A618_RENDER_IOVA && iova[i]<SWEET_A618_RENDER_IOVA+SWEET_A618_RENDER_BYTES;
        const uint64_t base=pool ? SWEET_A618_RENDER_IOVA : SWEET_A618_IMPORT_IOVA;
        const uint64_t end=pool ? base+SWEET_A618_RENDER_BYTES : base+static_cast<uint64_t>(SWEET_A618_IMPORT_PAGES)*4096u;
        const uint64_t bytes=static_cast<uint64_t>(dwords[i])*4;
''')

for mirror in FILES.values():
    (REPO / mirror).write_bytes(new[mirror].encode())

with tempfile.TemporaryDirectory(prefix='make-0208-', dir='D:/ios-sweet/build') as scratch:
    work = Path(scratch)
    for side, data in (('a', base), ('b', new)):
        for target, mirror in FILES.items():
            path = work / side / target
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data[mirror].encode())
    done = subprocess.run(GIT + ['diff', '--no-index', '--no-color', '--no-prefix', '-U3', 'a', 'b'], cwd=work, capture_output=True)
    assert done.returncode == 1, done.stderr
    text = re.sub(r'^diff --git .*\n(index .*\n)?', '', done.stdout.decode(), flags=re.M)
    assert text.startswith('--- a/') and '\r' not in text
    output = REPO / 'xnu/patches' / NAME
    output.write_bytes(text.encode())
    check = work / 'check'
    for target, mirror in FILES.items():
        path = check / target
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(base[mirror].encode())
    subprocess.run(GIT + ['apply', str(output)], cwd=check, check=True)
    assert all((check / t).read_bytes() == new[m].encode() for t, m in FILES.items())
    script = REPO / 'tools/check-sweet-patch-reversal.sh'
    lines = script.read_bytes().decode().replace('\r\n', '\n').split('\n')
    changed = []
    for at, line in enumerate(lines):
        found = re.search(r'xnu/patches/(\d{4}-[^"]+\.patch)', line)
        if 'apply --reverse' not in line or not found or 'dxb/xnu' not in line:
            continue
        patch = REPO / 'xnu/patches' / found.group(1)
        touched = {l.split('\t')[-1] for l in subprocess.check_output(GIT + ['apply', '--numstat', str(patch)], cwd=check, text=True).splitlines()}
        for target in sorted(touched & set(FILES)):
            if '--exclude=' + target in line:
                continue
            done = subprocess.run(GIT + ['apply', '--reverse', '--check', '--include=' + target, str(patch)], cwd=check, capture_output=True)
            if done.returncode != 0:
                line = line.replace(' --check ', ' --check --exclude=' + target + ' ', 1)
                changed.append((found.group(1), target))
        lines[at] = line
    subprocess.run(GIT + ['apply', '--reverse', str(output)], cwd=check, check=True)
print(NAME, len(text.splitlines()), 'lines, forward and reverse verified; excludes added:', changed)
assert not any(NAME in line for line in lines)
last = max(i for i, line in enumerate(lines) if 'apply --reverse --check' in line or 'grep -F' in line)
lines.insert(last + 1, '# 0208: GPU buffers from wired system memory in the GPU window; the pinned pool is the fallback.')
lines.insert(last + 2, 'git -C dxb/xnu apply --reverse --check "$GITHUB_WORKSPACE/xnu/patches/' + NAME + '"')
script.write_bytes('\n'.join(lines).encode())

verify = REPO / 'tools/verify-gmu-service-patch.py'
source = verify.read_bytes().decode().replace('\r\n', '\n').split('\n')
at = [i for i, line in enumerate(source) if '0207-sweet-a618-import-tables-in-halves.patch' in line]
assert len(at) == 1 and not any(NAME in line for line in source)
source.insert(at[0] + 1, "PATCHES += (('xnu/patches/" + NAME + "', {" + ', '.join("'" + t + "'" for t in FILES) + "}),)")
verify.write_bytes('\n'.join(source).encode())
print('verify list and reversal script updated')
