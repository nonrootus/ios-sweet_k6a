"""Patch 0217: the threads that submit GPU work alternate between the two A76 cores.

0203 binds each thread that submits GPU work (up to four a client) to A76 core 7. On 0215n all four
of backboardd's rendering threads were bound there ('GPU thread bound to A76 core 7' four times),
so two of them busy at once shared one core while A76 core 6 ran whatever the scheduler gave it.
Now the bound threads alternate, core 7 first, then 6, across all clients, and the log names the
process and the core. With asynchronous submission (0215) the frame time is mostly CPU work
(0215n: 2.4 ms a frame in GL calls, 8.0 ms outside them).
"""
import re
import subprocess
import tempfile
from pathlib import Path

REPO = Path('D:/ios-sweet/src/ios-sweet')
GIT = ['git', '-c', 'core.autocrlf=false', '-c', 'core.safecrlf=false']
NAME = '0217-sweet-gpu-threads-on-both-a76.patch'
FILES = {'iokit/Kernel/arm/SweetAdreno.cpp': 'xnu/gpu/SweetAdreno.cpp'}
base = {m: subprocess.check_output(GIT + ['show', 'HEAD:' + m], cwd=REPO).decode() for m in FILES.values()}
new = dict(base)
M = 'xnu/gpu/SweetAdreno.cpp'


def edit(before, after):
    assert new[M].count(before) == 1, (new[M].count(before), before[:80])
    new[M] = new[M].replace(before, after)


edit("""/*
 * The thread that submits GPU work does the CPU half of every frame. Keep it on an A76:
 * core 7 is MPIDR Aff1 = 7 (sweet_cpufreq.c). The scheduler knows nothing of big and little
 * here. These are the kernel's own functions; their headers are not visible to IOKit.
 */
""", """/*
 * The threads that submit GPU work do the CPU half of every frame. Keep them on the A76s:
 * cores 7 and 6 are MPIDR Aff1 = 7 and 6 (sweet_cpufreq.c). The scheduler knows nothing of big
 * and little here. Bound threads alternate, core 7 first, so two render threads busy at once
 * each have a fast core. These are the kernel's own functions; their headers are not visible
 * to IOKit.
 */
""")
edit("""static void bind_thread_to_fast_core(void)
{
    const ml_topology_info_t *topology=ml_get_topology_info();
    for(unsigned i=0;i<topology->num_cpus;i++){
        if(((topology->cpus[i].phys_id>>8)&0xffu)!=7u)continue;
        void *processor=sweet_cpu_to_processor(topology->cpus[i].cpu_id);
        if(!processor)return;
        sweet_thread_bind(processor);
        sweet_thread_block(nullptr);
        IOLog("SWEET CA: GPU thread bound to A76 core 7 (cpu %d)\\n",topology->cpus[i].cpu_id);
        return;
    }
}
""", """static void bind_thread_to_fast_core(void)
{
    static uint32_t bound_total;
    const uint32_t n=__atomic_fetch_add(&bound_total,1u,__ATOMIC_RELAXED);
    const unsigned core=(n&1u) ? 6u:7u;
    const ml_topology_info_t *topology=ml_get_topology_info();
    for(unsigned i=0;i<topology->num_cpus;i++){
        if(((topology->cpus[i].phys_id>>8)&0xffu)!=core)continue;
        void *processor=sweet_cpu_to_processor(topology->cpus[i].cpu_id);
        if(!processor)return;
        sweet_thread_bind(processor);
        sweet_thread_block(nullptr);
        char name[32]={};
        proc_selfname(name,(int)sizeof(name));
        IOLog("SWEET CA: GPU thread %u of %s bound to A76 core %u (cpu %d)\\n",n+1u,name,core,
            topology->cpus[i].cpu_id);
        return;
    }
}
""")
for mirror in FILES.values():
    (REPO / mirror).write_bytes(new[mirror].encode())

with tempfile.TemporaryDirectory(prefix='make-0217-', dir='D:/ios-sweet/build') as scratch:
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
lines.insert(last + 1, '# 0217: GPU submitting threads alternate between A76 cores 7 and 6.')
lines.insert(last + 2, 'git -C dxb/xnu apply --reverse --check "$GITHUB_WORKSPACE/xnu/patches/' + NAME + '"')
script.write_bytes('\n'.join(lines).encode())

verify = REPO / 'tools/verify-gmu-service-patch.py'
source = verify.read_bytes().decode().replace('\r\n', '\n').split('\n')
at = [i for i, line in enumerate(source) if '0215-sweet-a618-async-submit.patch' in line]
assert len(at) == 1 and not any(NAME in line for line in source)
source.insert(at[0] + 1, "PATCHES += (('xnu/patches/" + NAME + "', {'iokit/Kernel/arm/SweetAdreno.cpp'}),)")
verify.write_bytes('\n'.join(source).encode())
print('verify list and reversal script updated')
