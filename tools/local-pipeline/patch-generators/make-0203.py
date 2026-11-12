"""Patch 0203: the thread that drives the GPU stays on an A76 core.

0202's log: mean GPU wait 1766 us a submission, so the frame's other half is CPU work
(CoreAnimation and Mesa on the render thread). Nothing kept that thread on the two A76 cores;
the scheduler has no big/little knowledge here. Each thread that submits GPU work is bound to
core 7 (MPIDR Aff1 = 7, as in sweet_cpufreq.c) the first time it does, at most four threads.
Whether the A76 is faster for this work is not measured: this is the test of it.
"""
import re
import subprocess
import tempfile
from pathlib import Path

REPO = Path('D:/ios-sweet/src/ios-sweet')
GIT = ['git', '-c', 'core.autocrlf=false', '-c', 'core.safecrlf=false']
NAME = '0203-sweet-a618-gpu-thread-on-a76.patch'
TARGET = 'iokit/Kernel/arm/SweetAdreno.cpp'
MIRROR = 'xnu/gpu/SweetAdreno.cpp'

base = subprocess.check_output(GIT + ['show', 'HEAD:' + MIRROR], cwd=REPO).decode()
assert '\r' not in base
new = base


def edit(before, after):
    global new
    assert new.count(before) == 1, (new.count(before), before[:70])
    new = new.replace(before, after)


edit('''#include <kern/task.h>
#include <sys/proc.h>
#include <sys/systm.h>
''', '''#include <kern/task.h>
#include <sys/proc.h>
#include <sys/systm.h>
extern "C" {
#include <arm/machine_routines.h>
}
''')
edit('''class SweetAdrenoUserClient : public IOUserClient {
    OSDeclareDefaultStructors(SweetAdrenoUserClient);
    task_t owner;
''', r'''/*
 * The thread that submits GPU work does the CPU half of every frame. Keep it on an A76:
 * core 7 is MPIDR Aff1 = 7 (sweet_cpufreq.c). The scheduler knows nothing of big and little
 * here. These are the kernel's own functions; their headers are not visible to IOKit.
 */
extern "C" void *sweet_thread_bind(void *processor) __asm("_thread_bind");
extern "C" void *sweet_cpu_to_processor(int cpu) __asm("_cpu_to_processor");
extern "C" int sweet_thread_block(void *continuation) __asm("_thread_block");

static void bind_thread_to_fast_core(void)
{
    const ml_topology_info_t *topology=ml_get_topology_info();
    for(unsigned i=0;i<topology->num_cpus;i++){
        if(((topology->cpus[i].phys_id>>8)&0xffu)!=7u)continue;
        void *processor=sweet_cpu_to_processor(topology->cpus[i].cpu_id);
        if(!processor)return;
        sweet_thread_bind(processor);
        sweet_thread_block(nullptr);
        IOLog("SWEET CA: GPU thread bound to A76 core 7 (cpu %d)\n",topology->cpus[i].cpu_id);
        return;
    }
}

class SweetAdrenoUserClient : public IOUserClient {
    OSDeclareDefaultStructors(SweetAdrenoUserClient);
    IOThread bound_threads[4];
    unsigned bound_count;
    task_t owner;
''')
edit('''IOReturn SweetAdrenoUserClient::submit(msm_gem_submit *request)
{
''', '''IOReturn SweetAdrenoUserClient::submit(msm_gem_submit *request)
{
    /* Outside the lock: this may switch processors. A rare race only binds a thread twice. */
    const IOThread self=IOThreadSelf();
    bool seen=false;
    for(unsigned i=0;i<bound_count;i++)seen|=bound_threads[i]==self;
    if(!seen && bound_count<4){
        bound_threads[bound_count++]=self;
        bind_thread_to_fast_core();
    }
''')
(REPO / MIRROR).write_bytes(new.encode())

with tempfile.TemporaryDirectory(prefix='make-0203-', dir='D:/ios-sweet/build') as scratch:
    work = Path(scratch)
    for side, data in (('a', base), ('b', new)):
        path = work / side / TARGET
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data.encode())
    done = subprocess.run(GIT + ['diff', '--no-index', '--no-color', '--no-prefix', '-U3', 'a', 'b'], cwd=work, capture_output=True)
    assert done.returncode == 1, done.stderr
    text = re.sub(r'^diff --git .*\n(index .*\n)?', '', done.stdout.decode(), flags=re.M)
    assert text.startswith('--- a/') and '\r' not in text
    output = REPO / 'xnu/patches' / NAME
    output.write_bytes(text.encode())
    check = work / 'check' / TARGET
    check.parent.mkdir(parents=True, exist_ok=True)
    check.write_bytes(base.encode())
    subprocess.run(GIT + ['apply', str(output)], cwd=work / 'check', check=True)
    assert check.read_bytes() == new.encode()
    subprocess.run(GIT + ['apply', '--reverse', str(output)], cwd=work / 'check', check=True)
print(NAME, len(text.splitlines()), 'lines, forward and reverse verified')

verify = REPO / 'tools/verify-gmu-service-patch.py'
source = verify.read_bytes().decode().replace('\r\n', '\n')
anchor = "PATCHES += (('xnu/patches/0202-sweet-a618-fast-gpu-wait.patch', {'iokit/Kernel/arm/sweet_a618_render_ring.inc'}),)\n"
assert source.count(anchor) == 1 and NAME not in source
source = source.replace(anchor, anchor + "PATCHES += (('xnu/patches/" + NAME + "', {'" + TARGET + "'}),)\n")
verify.write_bytes(source.encode())

script = REPO / 'tools/check-sweet-patch-reversal.sh'
lines = script.read_bytes().decode().replace('\r\n', '\n').split('\n')
assert not any(NAME in line for line in lines)
at = [i for i, line in enumerate(lines) if '0184-sweet-direct-frames-stay-on-panel.patch' in line and 'apply --reverse' in line]
assert len(at) == 1, at
if '--exclude=' + TARGET not in lines[at[0]]:
    lines[at[0]] = lines[at[0]].replace(' --check ', ' --check --exclude=' + TARGET + ' ', 1)
last = max(i for i, line in enumerate(lines) if 'apply --reverse --check' in line or 'grep -F' in line)
lines.insert(last + 1, '# 0203: the thread that submits GPU work stays on an A76 core.')
lines.insert(last + 2, 'git -C dxb/xnu apply --reverse --check "$GITHUB_WORKSPACE/xnu/patches/' + NAME + '"')
script.write_bytes('\n'.join(lines).encode())
print('verify list and reversal script updated')
