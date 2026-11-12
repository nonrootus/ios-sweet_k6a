"""Patch 0202: wait for the GPU by looking again at once, not by sleeping a millisecond.

Every submission is synchronous: a618_render_ring published WPTR and then looked at the CP with
IOSleep(1) between looks. On the phone a submission of a panel field took 1905..2017 us whatever
the work (0201: 14 samples, median 1960), about 4 submissions a frame on average (ring wraps) and
probably many more in frames with blurs (25..40 ms unaccounted; not measured per frame). Now the CP is
looked at every 10 us for 8 ms, and only then in 1 ms sleeps. The limit becomes 500 ms of real time
(the old 101 sleeps of ~2 ms were ~200 ms; a timeout poisons the GPU until reboot, so never shorter).
Every 4096 submissions the kernel logs the average and longest wait.
"""
import re
import subprocess
import tempfile
from pathlib import Path

REPO = Path('D:/ios-sweet/src/ios-sweet')
GIT = ['git', '-c', 'core.autocrlf=false', '-c', 'core.safecrlf=false']
NAME = '0202-sweet-a618-fast-gpu-wait.patch'
TARGET = 'iokit/Kernel/arm/sweet_a618_render_ring.inc'
MIRROR = 'xnu/gpu/sweet_a618_render_ring.inc'

base = subprocess.check_output(GIT + ['show', 'HEAD:' + MIRROR], cwd=REPO).decode()
assert '\r' not in base
before = '''    for (unsigned waited_ms = 0; waited_ms <= 100; ++waited_ms) {
        uint32_t status = UINT32_MAX, busy = UINT32_MAX;
'''
after = '''    /*
     * A sleep between looks made every submission take about 2 ms however little the GPU had
     * to do. Look again every 10 us for the first 8 ms; then sleep. A timeout stops the GPU
     * until reboot, so the limit stays well above the ~200 ms the old sleeps came to.
     */
    uint64_t pause_ticks = 0, spin_ticks = 0, limit_ticks = 0;
    nanoseconds_to_absolutetime(10000, &pause_ticks);
    nanoseconds_to_absolutetime(8000000, &spin_ticks);
    nanoseconds_to_absolutetime(500000000, &limit_ticks);
    const uint64_t began = mach_absolute_time();
    for (;;) {
        uint32_t status = UINT32_MAX, busy = UINT32_MAX;
'''
first = base.index('static int a618_render_ring(')
new = base[:first] + '#include <mach/mach_time.h>' + chr(10) + chr(10) + base[first:]
assert new.count(before) == 1
new = new.replace(before, after)
before = r'''                IOLog("SWEET CA: ring wrap tail=%u end=%u pages=%02x\n", tail, end, dirty);
            tail = end;
            return 0;
        }
        if (waited_ms < 100)
            IOSleep(1);
    }
    return -4;
}
'''
after = r'''                IOLog("SWEET CA: ring wrap tail=%u end=%u pages=%02x\n", tail, end, dirty);
            tail = end;
            /* Under the submit lock, so plain counters do. */
            static uint64_t waited_ticks, longest_ticks;
            static unsigned waits;
            const uint64_t waited = mach_absolute_time() - began;
            waited_ticks += waited;
            if (waited > longest_ticks)
                longest_ticks = waited;
            if (++waits == 4096) {
                uint64_t mean_ns = 0, longest_ns = 0;
                absolutetime_to_nanoseconds(waited_ticks / waits, &mean_ns);
                absolutetime_to_nanoseconds(longest_ticks, &longest_ns);
                IOLog("SWEET CA: GPU wait mean %llu us longest %llu us over %u submissions\n",
                    mean_ns / 1000, longest_ns / 1000, waits);
                waited_ticks = longest_ticks = 0;
                waits = 0;
            }
            return 0;
        }
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
'''
assert new.count(before) == 1
new = new.replace(before, after)
(REPO / MIRROR).write_bytes(new.encode())

with tempfile.TemporaryDirectory(prefix='make-0202-', dir='D:/ios-sweet/build') as scratch:
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
anchor = "PATCHES += (('xnu/patches/0195-sweet-a618-render-pool-256m.patch', {'bsd/dev/sweet_a618_render_pool.h'}),)\n"
assert source.count(anchor) == 1 and NAME not in source
source = source.replace(anchor, anchor + "PATCHES += (('xnu/patches/" + NAME + "', {'" + TARGET + "'}),)\n")
verify.write_bytes(source.encode())

script = REPO / 'tools/check-sweet-patch-reversal.sh'
lines = script.read_bytes().decode().replace('\r\n', '\n').split('\n')
assert not any(NAME in line for line in lines)
at = [i for i, line in enumerate(lines) if '0174-sweet-a618-mesa-client.patch' in line and 'apply --reverse' in line]
assert len(at) == 1, at
if '--exclude=' + TARGET not in lines[at[0]]:
    lines[at[0]] = lines[at[0]].replace(' --check ', ' --check --exclude=' + TARGET + ' ', 1)
last = max(i for i, line in enumerate(lines) if 'apply --reverse --check' in line or 'grep -F' in line)
lines.insert(last + 1, '# 0202: the GPU is waited for by looking again at once, not by sleeping 1 ms.')
lines.insert(last + 2, 'git -C dxb/xnu apply --reverse --check "$GITHUB_WORKSPACE/xnu/patches/' + NAME + '"')
script.write_bytes('\n'.join(lines).encode())
print('verify list and reversal script updated')
