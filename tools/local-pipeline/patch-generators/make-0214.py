"""Patch 0214: the GPU's runtime health check no longer requires CPU idle to be off.

0212 enabled CPU idle (WFI) after the GPU bring-up, and the very first GPU submission failed:
'SWEET CA: submit disabled rc=-3'. Every submission's guard (a618_cp_guard -> GMU health ->
post_check -> boot_check(s, 3)) also required idle_enable FALSE, a bring-up rule. After the GMU is
up (phase 3), WFI idle is clock gating only (no PSCI suspend, no cluster power collapse, no RPMh
sleep set), so phase 3 ignores idle_enable; phases 0..2 (bring-up) still require it off.
"""
import re
import subprocess
import tempfile
from pathlib import Path

REPO = Path('D:/ios-sweet/src/ios-sweet')
GIT = ['git', '-c', 'core.autocrlf=false', '-c', 'core.safecrlf=false']
NAME = '0214-sweet-gpu-runtime-allows-cpu-idle.patch'
FILES = {'iokit/Kernel/arm/sweet_gpu_gmu_start.cpp': 'xnu/gpu/sweet_gpu_gmu_start.cpp'}
base = {m: subprocess.check_output(GIT + ['show', 'HEAD:' + m], cwd=REPO).decode() for m in FILES.values()}
new = dict(base)
M = 'xnu/gpu/sweet_gpu_gmu_start.cpp'


def edit(before, after):
    assert new[M].count(before) == 1, (new[M].count(before), before[:80])
    new[M] = new[M].replace(before, after)


edit("""    if (phase>3 || idle_enable || power_check(s,phase) ||
""", """    /* CPU idle off during bring-up (phases 0..2); at run time (3) WFI idle is clock gating only. */
    if (phase>3 || (idle_enable && phase<3) || power_check(s,phase) ||
""")
for mirror in FILES.values():
    (REPO / mirror).write_bytes(new[mirror].encode())

with tempfile.TemporaryDirectory(prefix='make-0214-', dir='D:/ios-sweet/build') as scratch:
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
lines.insert(last + 1, '# 0214: the GPU runtime health check no longer requires CPU idle off.')
lines.insert(last + 2, 'git -C dxb/xnu apply --reverse --check "$GITHUB_WORKSPACE/xnu/patches/' + NAME + '"')
script.write_bytes('\n'.join(lines).encode())

verify = REPO / 'tools/verify-gmu-service-patch.py'
source = verify.read_bytes().decode().replace('\r\n', '\n').split('\n')
at = [i for i, line in enumerate(source) if '0212-sweet-gpu-bringup-accepts-wfi.patch' in line]
assert len(at) == 1 and not any(NAME in line for line in source)
source.insert(at[0] + 1, "PATCHES += (('xnu/patches/" + NAME + "', {'iokit/Kernel/arm/sweet_gpu_gmu_start.cpp'}),)")
verify.write_bytes('\n'.join(source).encode())
print('verify list and reversal script updated')
