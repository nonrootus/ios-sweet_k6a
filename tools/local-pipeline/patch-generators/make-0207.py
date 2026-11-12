"""Patch 0207: the import window's 256 leaf tables come in two allocations of 128.

0206 booted with 'SWEET CA: IOSurface import window unavailable; surfaces stay copied':
sweet_gpu_memory_create_nc refuses more than GPU_MAX_PAGES = 128 pages at once (the same
limit 0197 met for the render pool). The allocator is left as it is.
"""
import re
import subprocess
import tempfile
from pathlib import Path

REPO = Path('D:/ios-sweet/src/ios-sweet')
GIT = ['git', '-c', 'core.autocrlf=false', '-c', 'core.safecrlf=false']
NAME = '0207-sweet-a618-import-tables-in-halves.patch'
FILES = {'iokit/Kernel/arm/sweet_a618_mapping.inc': 'xnu/gpu/sweet_a618_mapping.inc'}
base = {m: subprocess.check_output(GIT + ['show', 'HEAD:' + m], cwd=REPO).decode() for m in FILES.values()}
new = dict(base)
M = 'xnu/gpu/sweet_a618_mapping.inc'


def edit(before, after):
    assert new[M].count(before) == 1, (new[M].count(before), before[:80])
    new[M] = new[M].replace(before, after)


edit('''    sweet_gpu_memory *import_tables_memory;
''', '''    sweet_gpu_memory *import_tables_memory[2];
''')
edit('''            /* IOSurfaces read in place: empty leaf tables now, leaves at run time. Optional. */
            m.import_tables_memory=sweet_gpu_memory_create_nc(SWEET_A618_IMPORT_TABLES);
            bool imports=m.import_tables_memory!=nullptr;
            for(unsigned i=0;imports && i<SWEET_A618_IMPORT_TABLES;i++){
                void *cpu=nullptr;uint64_t pa=0;
                if(sweet_gpu_memory_page(m.import_tables_memory,i,&cpu,&pa))imports=false;
                else m.import_tables[i]={static_cast<uint64_t *>(cpu),pa};
            }
            if(imports && !sweet_a618_import_attach(m.tables,m.import_tables)){
                for(unsigned i=0;i<SWEET_A618_IMPORT_TABLES;i++)
                    if(sweet_gpu_memory_clean(m.import_tables_memory,i))return -5;
''', '''            /* IOSurfaces read in place: empty leaf tables now, leaves at run time. Optional.
             * The allocator takes at most 128 pages at a time (GPU_MAX_PAGES): two halves. */
            constexpr unsigned half=SWEET_A618_IMPORT_TABLES/2;
            static_assert(half*2==SWEET_A618_IMPORT_TABLES && half<=128, "import tables in two allocations");
            bool imports=true;
            for(unsigned h=0;imports && h<2;h++){
                m.import_tables_memory[h]=sweet_gpu_memory_create_nc(half);
                imports=m.import_tables_memory[h]!=nullptr;
                for(unsigned i=0;imports && i<half;i++){
                    void *cpu=nullptr;uint64_t pa=0;
                    if(sweet_gpu_memory_page(m.import_tables_memory[h],i,&cpu,&pa))imports=false;
                    else m.import_tables[h*half+i]={static_cast<uint64_t *>(cpu),pa};
                }
            }
            if(imports && !sweet_a618_import_attach(m.tables,m.import_tables)){
                for(unsigned i=0;i<SWEET_A618_IMPORT_TABLES;i++)
                    if(sweet_gpu_memory_clean(m.import_tables_memory[i/half],i%half))return -5;
''')
for mirror in FILES.values():
    (REPO / mirror).write_bytes(new[mirror].encode())

with tempfile.TemporaryDirectory(prefix='make-0207-', dir='D:/ios-sweet/build') as scratch:
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
lines.insert(last + 1, '# 0207: the import window tables come in two allocations of 128 pages.')
lines.insert(last + 2, 'git -C dxb/xnu apply --reverse --check "$GITHUB_WORKSPACE/xnu/patches/' + NAME + '"')
script.write_bytes('\n'.join(lines).encode())

verify = REPO / 'tools/verify-gmu-service-patch.py'
source = verify.read_bytes().decode().replace('\r\n', '\n').split('\n')
at = [i for i, line in enumerate(source) if '0206-sweet-a618-iosurface-zero-copy.patch' in line]
assert len(at) == 1 and not any(NAME in line for line in source)
source.insert(at[0] + 1, "PATCHES += (('xnu/patches/" + NAME + "', {'iokit/Kernel/arm/sweet_a618_mapping.inc'}),)")
verify.write_bytes('\n'.join(source).encode())
print('verify list and reversal script updated')
