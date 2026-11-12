"""Patch 0215: asynchronous GPU submission, with fences, waits and deferred buffer release.

Every submission used to return only after the GPU had finished it (0202 measured ~1.8 ms a
submission; 0212b: 8.2 ms of a 19.4 ms frame spent handing commands on). Now:
- the ring writer waits only for room in the ring (the CP must have read past the words to be
  written), publishes WPTR and returns;
- completion is the fence the CP writes at the end of each submission (CACHE_FLUSH_TS to the fill
  page), read without the lock; sweet_a618_render_wait() spins 10 us for 8 ms then sleeps, checks the
  GPU's health every millisecond, and stops the GPU (as before) when no fence completes for 500 ms;
- SweetAdreno records each BO's last fence; MSM_WAIT_FENCE and MSM_GEM_CPU_PREP (shared BOs, i.e.
  imported IOSurfaces; NOSYNC answers busy) wait for real; a BO closed while the GPU may still use
  it (Mesa drops its references at flush, not at completion) is kept until its fence completes;
  closing the client waits for the GPU first.
As on the K20 Pro port (Topaz kernel: fences, deferred release of buffers given back while the GPU
is at them).
"""
import re
import subprocess
import tempfile
from pathlib import Path

REPO = Path('D:/ios-sweet/src/ios-sweet')
GIT = ['git', '-c', 'core.autocrlf=false', '-c', 'core.safecrlf=false']
NAME = '0215-sweet-a618-async-submit.patch'
FILES = {
    'iokit/Kernel/arm/sweet_a618_render_ring.inc': 'xnu/gpu/sweet_a618_render_ring.inc',
    'iokit/Kernel/arm/sweet_a618_renderer.inc': 'xnu/gpu/sweet_a618_renderer.inc',
    'iokit/Kernel/arm/sweet_a618_render_bridge.h': 'xnu/gpu/sweet_a618_render_bridge.h',
    'iokit/Kernel/arm/SweetAdreno.cpp': 'xnu/gpu/SweetAdreno.cpp',
}
base = {m: subprocess.check_output(GIT + ['show', 'HEAD:' + m], cwd=REPO).decode() for m in FILES.values()}
assert not any('\r' in v for v in base.values())
new = dict(base)


def edit(mirror, before, after):
    path = 'xnu/gpu/' + mirror
    assert new[path].count(before) == 1, (mirror, new[path].count(before), before[:80])
    new[path] = new[path].replace(before, after)


# ---- the ring writer: wait for room, publish, return ----------------------------------------
R = 'sweet_a618_render_ring.inc'
ring = new['xnu/gpu/' + R]
start = ring.index('    if (a618_cp_guard(s, run) || a618_cp_read(run, 0x806) != tail ||')
stop = ring.index('    unsigned dirty = 0;')
ring = ring[:start] + r'''    if (a618_cp_guard(s, run) || a618_cp_read(run, 0x807) != tail)
        return -3;
    /*
     * Asynchronous (0215): earlier submissions may still be running. Wait until the CP has read past
     * every word about to be written: with RPTR at or behind tail the free part is [tail, end of ring)
     * and [0, RPTR); with RPTR ahead of tail (it is still in the previous lap) only [tail, RPTR). WPTR
     * must not become RPTR (that would read as an empty ring). Look every 10 us for 8 ms, then sleep.
     */
    {
        uint64_t pause_ticks = 0, spin_ticks = 0, limit_ticks = 0;
        nanoseconds_to_absolutetime(10000, &pause_ticks);
        nanoseconds_to_absolutetime(8000000, &spin_ticks);
        nanoseconds_to_absolutetime(500000000, &limit_ticks);
        const uint64_t began = mach_absolute_time();
        for (;;) {
            const uint32_t rptr = a618_cp_read(run, 0x806);
            if (rptr >= words)
                return -5;
            const bool room = wrap ? rptr <= tail && end < rptr : rptr <= tail || end < rptr;
            if (room)
                break;
            if (a618_cp_guard(s, run))
                return -3;
            const uint64_t now = mach_absolute_time();
            if (now - began >= limit_ticks)
                return -4;
            if (now - began >= spin_ticks) {
                IOSleep(1);
            } else {
                while (mach_absolute_time() - now < pause_ticks)
                    __asm__ volatile("yield");
            }
        }
    }

''' + ring[stop:]
start = ring.index('    mmio_write32(a618_cp_register(run, 0x807), end);')
ring = ring[:start] + r'''    mmio_write32(a618_cp_register(run, 0x807), end);
    if (complete(s))
        return -3;
    if (wrap)
        IOLog("SWEET CA: ring wrap tail=%u end=%u pages=%02x\n", tail, end, dirty);
    tail = end;
    return 0;
}
'''
ring = ring.replace('''/* Kernel ring writer for the renderer's own packets. All callers hold the
 * GPU submit lock. This is the full 32 KiB ring configured by CP_RB_CNTL.
 * After publishing WPTR any failure must permanently stop submissions. */''', '''/* Kernel ring writer for the renderer's own packets. All callers hold the
 * GPU submit lock. This is the full 32 KiB ring configured by CP_RB_CNTL.
 * It returns once WPTR is published (0215: the GPU works on while the CPU goes
 * on). After publishing WPTR any failure must permanently stop submissions. */''')
new['xnu/gpu/' + R] = ring

# ---- the renderer: submitted and completed fences, waiting ----------------------------------
N = 'sweet_a618_renderer.inc'
edit(N, '''/* Private synchronous CoreAnimation queue. The existing 0170 fill is the
 * hardware proof before this is armed. No reset, teardown, OOB release or
 * submission retry occurs after any uncertain result. */''', '''/* Private CoreAnimation queue, asynchronous since 0215: a submission returns
 * once it is in the ring; its fence is written by the CP when it is done. The
 * existing 0170 fill is the hardware proof before this is armed. No reset,
 * teardown, OOB release or submission retry occurs after any uncertain result. */''')
edit(N, '''    unsigned tail;
    uint32_t fence;
    bool ready, poisoned;
} a618_renderer;
''', '''    unsigned tail;
    uint32_t fence;                 /* the last one submitted */
    volatile uint32_t *done;        /* the last one completed, written by the CP (fill page word 16) */
    bool ready, poisoned;
} a618_renderer;
''')
edit(N, '''extern "C" uint32_t sweet_a618_render_completed(void)
{
    return sweet_a618_render_ready() ?
        __atomic_load_n(&a618_renderer.fence,__ATOMIC_ACQUIRE) : 0;
}
''', r'''extern "C" uint32_t sweet_a618_render_completed(void)
{
    return sweet_a618_render_ready() && a618_renderer.done ? *a618_renderer.done : 0;
}

extern "C" uint32_t sweet_a618_render_submitted(void)
{
    return __atomic_load_n(&a618_renderer.fence,__ATOMIC_ACQUIRE);
}

/*
 * Wait until the CP has completed fence: 0 done, -4 not within max_ms (0: only look), -1 never
 * submitted, -3 the GPU is unhealthy or has stopped completing work (submissions stop for good).
 */
extern "C" int sweet_a618_render_wait(uint32_t fence,unsigned max_ms)
{
    if(!fence)return 0;
    if(!sweet_a618_render_ready() || !a618_renderer.done)return -3;
    auto reached=[&](uint32_t value){return static_cast<int32_t>(value-fence)>=0;};
    uint32_t seen=*a618_renderer.done;
    if(reached(seen))return 0;
    if(!reached(sweet_a618_render_submitted()))return -1;
    if(!max_ms)return -4;
    uint64_t pause=0,spin=0,limit=0,stalled=0,guard=0;
    nanoseconds_to_absolutetime(10000,&pause);
    nanoseconds_to_absolutetime(8000000,&spin);
    nanoseconds_to_absolutetime(static_cast<uint64_t>(max_ms)*1000000,&limit);
    nanoseconds_to_absolutetime(500000000,&stalled);
    nanoseconds_to_absolutetime(1000000,&guard);
    const uint64_t began=mach_absolute_time();
    uint64_t progress=began,checked=began;
    for(;;){
        const uint32_t value=*a618_renderer.done;
        const uint64_t now=mach_absolute_time();
        if(reached(value)){
            static uint64_t waited_ticks,longest_ticks;
            static unsigned waits;
            const uint64_t waited=now-began;
            waited_ticks+=waited;
            if(waited>longest_ticks)longest_ticks=waited;
            if(++waits==1024){
                uint64_t mean_ns=0,longest_ns=0;
                absolutetime_to_nanoseconds(waited_ticks/waits,&mean_ns);
                absolutetime_to_nanoseconds(longest_ticks,&longest_ns);
                IOLog("SWEET CA: fence waits mean %llu us longest %llu us over %u waits\n",
                    mean_ns/1000,longest_ns/1000,waits);
                waited_ticks=longest_ticks=0;waits=0;
            }
            return 0;
        }
        if(value!=seen){seen=value;progress=now;}
        if(now-progress>=stalled || (now-checked>=guard && a618_cp_guard(&probe,a618_renderer.run))){
            __atomic_store_n(&a618_renderer.poisoned,true,__ATOMIC_RELEASE);
            IOLog("SWEET CA: GPU stopped completing work at fence %u (waiting for %u, submitted %u)\n",
                value,fence,sweet_a618_render_submitted());
            return -3;
        }
        if(now-checked>=guard)checked=now;
        if(now-began>=limit)return -4;
        if(now-began>=spin){
            IOSleep(1);
        }else{
            while(mach_absolute_time()-now<pause)
                __asm__ volatile("yield");
        }
    }
}
''')
edit(N, '''    a618_renderer.run=run;
    a618_renderer.tail=tail;
''', '''    a618_renderer.run=run;
    a618_renderer.tail=tail;
    a618_renderer.done=&words[16];
''')
edit(N, '''    int rc=a618_render_ring(&probe,a618_renderer.run,packet,used,a618_renderer.tail);
    void *fill=nullptr;
    if(!rc && a618_cp_buffer(a618_fill_buffer,0,SWEET_A618_DATA_PAGES,&fill))rc=-5;
    if(!rc && static_cast<volatile uint32_t *>(fill)[16]!=next)rc=-5;
    if(rc){
''', '''    int rc=a618_render_ring(&probe,a618_renderer.run,packet,used,a618_renderer.tail);
    if(rc){
''')
edit('sweet_a618_render_bridge.h', '''extern "C" uint32_t sweet_a618_render_completed(void);
''', '''extern "C" uint32_t sweet_a618_render_completed(void);
/* 0215: submissions return before the GPU is done; these tell and wait for completion. */
extern "C" uint32_t sweet_a618_render_submitted(void);
extern "C" int sweet_a618_render_wait(uint32_t fence, unsigned max_ms);
''')

# ---- the user client: per-BO fences, real waits, deferred release ---------------------------
A = 'SweetAdreno.cpp'
edit(A, '''    SweetSurface *surface;unsigned import_first,import_pages;uint32_t seed;uint64_t flushed;
};
''', '''    SweetSurface *surface;unsigned import_first,import_pages;uint32_t seed;uint64_t flushed;
    uint32_t fence;     /* the last submission that named it (0215: the GPU may still be at it) */
};
''')
edit(A, '''static uint64_t import_flushed_bytes,import_flush_ticks;
''', r'''static uint64_t import_flushed_bytes,import_flush_ticks;

static bool fence_done(uint32_t fence)
{
    return !fence || static_cast<int32_t>(sweet_a618_render_completed()-fence)>=0;
}

/* An absolute msm timeout (CLOCK_MONOTONIC) as milliseconds from now, at most 3 s; 0: only look. */
static unsigned timeout_ms(int64_t seconds,int64_t nanoseconds)
{
    uint64_t now=0;
    absolutetime_to_nanoseconds(mach_continuous_time(),&now);
    const int64_t deadline=seconds*1000000000+nanoseconds;
    if(deadline<=static_cast<int64_t>(now))return 0;
    const uint64_t left=(static_cast<uint64_t>(deadline)-now)/1000000;
    return left>3000 ? 3000 : static_cast<unsigned>(left)+1;
}
''')
edit(A, '''    sweet_bo *bos;
''', '''    sweet_bo *bos;
    sweet_bo *zombies;          /* closed BOs the GPU may still be using (0215) */
    unsigned zombie_count;
''')
edit(A, '''    void releaseBOs();
''', '''    void releaseBOs();
    void releaseBO(sweet_bo *bo);
    void reapLocked();
''')
edit(A, '''    lock=IOLockAlloc();
    bos=static_cast<sweet_bo *>(IOMallocZero(kHandles*sizeof(sweet_bo)));
    return lock && bos;
''', '''    lock=IOLockAlloc();
    bos=static_cast<sweet_bo *>(IOMallocZero(kHandles*sizeof(sweet_bo)));
    zombies=static_cast<sweet_bo *>(IOMallocZero(kZombies*sizeof(sweet_bo)));
    return lock && bos && zombies;
''')
edit(A, '''static constexpr unsigned kMaxBOs=1024,kMaxCMDs=64;
''', '''static constexpr unsigned kMaxBOs=1024,kMaxCMDs=64;
static constexpr unsigned kZombies=1024;
''')
edit(A, '''    if(!lock || !bos)return;
    IOLockLock(lock);
    for(unsigned i=0;i<kHandles;i++){
        if(bos[i].memory)dropBO(&bos[i]);
    }
    IOLockUnlock(lock);
''', '''    if(!lock || !bos)return;
    /* The GPU first finishes what it was given: nothing is released under it. */
    (void)sweet_a618_render_wait(sweet_a618_render_submitted(),2000);
    IOLockLock(lock);
    for(unsigned i=0;i<kHandles;i++){
        if(bos[i].memory)releaseBO(&bos[i]);
    }
    for(unsigned i=0;zombies && i<zombie_count;i++)releaseBO(&zombies[i]);
    zombie_count=0;
    IOLockUnlock(lock);
''')
edit(A, '''    if(bos){IOFree(bos,kHandles*sizeof(sweet_bo));bos=nullptr;}
''', '''    if(bos){IOFree(bos,kHandles*sizeof(sweet_bo));bos=nullptr;}
    if(zombies){IOFree(zombies,kZombies*sizeof(sweet_bo));zombies=nullptr;}
''')
edit(A, '''    IOLockLock(lock);
    for(unsigned i=0;i<request->nr_bos;i++){
        sweet_bo *bo=lookup(sb[i].handle);
        if(!bo){result=kIOReturnBadArgument;goto unlock;}
''', '''    IOLockLock(lock);
    reapLocked();
    for(unsigned i=0;i<request->nr_bos;i++){
        sweet_bo *bo=lookup(sb[i].handle);
        if(!bo){result=kIOReturnBadArgument;goto unlock;}
''')
edit(A, '''    if(sweet_a618_render_submit(iova,dwords,count,&request->fence)){
        result=kIOReturnTimeout;goto unlock;
    }
''', '''    if(sweet_a618_render_submit(iova,dwords,count,&request->fence)){
        result=kIOReturnTimeout;goto unlock;
    }
    /* Each BO named is in use until this fence completes (0215: the call does not wait for it). */
    for(unsigned i=0;i<request->nr_bos;i++){
        sweet_bo *bo=lookup(sb[i].handle);
        if(bo)bo->fence=request->fence;
    }
''')
edit(A, '''/* With the client lock held. */
void SweetAdrenoUserClient::dropBO(sweet_bo *bo)
{
    auto *memory=bo->memory;
''', '''/*
 * With the client lock held. Mesa gives a BO back when it flushes the last submission naming it,
 * not when the GPU is done with it: one the GPU may still use is kept (zombies) until its fence.
 */
void SweetAdrenoUserClient::dropBO(sweet_bo *bo)
{
    if(!fence_done(bo->fence) && sweet_a618_render_ready() && zombies){
        if(zombie_count==kZombies){
            (void)sweet_a618_render_wait(zombies[0].fence,500);
            reapLocked();
        }
        if(zombie_count<kZombies){
            zombies[zombie_count++]=*bo;
            bo->memory=nullptr;
            bo->surface=nullptr;
            return;
        }
    }
    releaseBO(bo);
}

/* With the client lock held: release closed BOs whose last submission has completed. */
void SweetAdrenoUserClient::reapLocked()
{
    if(!zombies)return;
    const bool ready=sweet_a618_render_ready();
    unsigned kept=0;
    for(unsigned i=0;i<zombie_count;i++){
        if(fence_done(zombies[i].fence) || !ready)releaseBO(&zombies[i]);
        else zombies[kept++]=zombies[i];
    }
    zombie_count=kept;
}

/* With the client lock held, the GPU done with it. */
void SweetAdrenoUserClient::releaseBO(sweet_bo *bo)
{
    auto *memory=bo->memory;
''')
edit(A, '''    case kCpuPrep:
        if(size<sizeof(r.prep))return kIOReturnBadArgument;
        IOLockLock(lock);result=lookup(r.prep.handle)?kIOReturnSuccess:kIOReturnBadArgument;
        IOLockUnlock(lock);break;
''', '''    case kCpuPrep:{
        if(size<sizeof(r.prep))return kIOReturnBadArgument;
        IOLockLock(lock);
        const sweet_bo *bo=lookup(r.prep.handle);
        const uint32_t fence=bo ? bo->fence : 0;
        IOLockUnlock(lock);
        if(!bo){result=kIOReturnBadArgument;break;}
        if(r.prep.op&4u){               /* MSM_PREP_NOSYNC: only tell */
            result=fence_done(fence) ? kIOReturnSuccess : kIOReturnBusy;
            break;
        }
        result=sweet_a618_render_wait(fence,timeout_ms(r.prep.timeout.seconds,r.prep.timeout.nanoseconds))==0 ?
            kIOReturnSuccess : kIOReturnTimeout;
        break;
    }
''')
edit(A, '''    case kWaitFence:
        if(size<sizeof(r.wait))return kIOReturnBadArgument;
        result=r.wait.fence<=sweet_a618_render_completed()?
            kIOReturnSuccess:kIOReturnTimeout;break;
''', '''    case kWaitFence:
        if(size<sizeof(r.wait))return kIOReturnBadArgument;
        result=sweet_a618_render_wait(r.wait.fence,timeout_ms(r.wait.timeout.seconds,r.wait.timeout.nanoseconds))==0 ?
            kIOReturnSuccess : kIOReturnTimeout;
        IOLockLock(lock);reapLocked();IOLockUnlock(lock);
        break;
''')

for mirror in FILES.values():
    (REPO / mirror).write_bytes(new[mirror].encode())

with tempfile.TemporaryDirectory(prefix='make-0215-', dir='D:/ios-sweet/build') as scratch:
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
lines.insert(last + 1, '# 0215: asynchronous GPU submission with fences and deferred buffer release.')
lines.insert(last + 2, 'git -C dxb/xnu apply --reverse --check "$GITHUB_WORKSPACE/xnu/patches/' + NAME + '"')
script.write_bytes('\n'.join(lines).encode())

verify = REPO / 'tools/verify-gmu-service-patch.py'
source = verify.read_bytes().decode().replace('\r\n', '\n').split('\n')
at = [i for i, line in enumerate(source) if '0214-sweet-gpu-runtime-allows-cpu-idle.patch' in line]
assert len(at) == 1 and not any(NAME in line for line in source)
source.insert(at[0] + 1, "PATCHES += (('xnu/patches/" + NAME + "', {" + ', '.join("'" + t + "'" for t in FILES) + "}),)")
verify.write_bytes('\n'.join(source).encode())
print('verify list and reversal script updated')
