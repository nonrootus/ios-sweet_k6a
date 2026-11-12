"""Patch 0212: the GPU bring-up accepts wfi=1 as well as wfi=0.

0209 booted with wfi=1 so that 0209 can enable CPU idle (WFI) after the GPU is up, but
sweet_gpu_probe.c refused to start the GMU unless wfi=0 ('SWEET GMU BOOT: requires jtag=1 wfi=0'):
no GPU, CoreAnimation on the CPU (owner: "as if switched to the CPU"). What the bring-up needs is
no CPU idle at all, which jtag=1 (idle_enable FALSE) still guarantees until bsd_init enables it
after the GPU and governor are started; with idle_enable FALSE cpu_idle never runs, so the wfi
value does not matter before then. Both checks now take wfi 0 or 1; jtag=1 stays required.
"""
import re
import subprocess
import tempfile
from pathlib import Path

REPO = Path('D:/ios-sweet/src/ios-sweet')
GIT = ['git', '-c', 'core.autocrlf=false', '-c', 'core.safecrlf=false']
NAME = '0212-sweet-gpu-bringup-accepts-wfi.patch'
FILES = {'bsd/dev/sweet_gpu_probe.c': 'xnu/gpu/sweet_gpu_probe.c'}
base = {m: subprocess.check_output(GIT + ['show', 'HEAD:' + m], cwd=REPO).decode() for m in FILES.values()}
new = dict(base)
M = 'xnu/gpu/sweet_gpu_probe.c'


def edit(before, after):
    assert new[M].count(before) == 1, (new[M].count(before), before[:80])
    new[M] = new[M].replace(before, after)


edit(r"""        if (jtag != 1 || wfi_mode != 0) { printf("SWEET GMU BOOT: requires jtag=1 wfi=0\n"); return; }
""", r"""        /* jtag=1 keeps CPU idle off (idle_enable FALSE) until bsd_init, so wfi=1 is safe here. */
        if (jtag != 1 || wfi_mode > 1) { printf("SWEET GMU BOOT: requires jtag=1 and wfi=0 or 1\n"); return; }
""")
edit("""                                            gmu_retention || jtag != 1 || wfi_mode != 0 || load_arg || smmu_arg)
""", """                                            gmu_retention || jtag != 1 || wfi_mode > 1 || load_arg || smmu_arg)
""")
for mirror in FILES.values():
    (REPO / mirror).write_bytes(new[mirror].encode())

with tempfile.TemporaryDirectory(prefix='make-0212-', dir='D:/ios-sweet/build') as scratch:
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
lines.insert(last + 1, '# 0212: the GPU bring-up accepts wfi=1 too (jtag=1 still keeps CPU idle off until bsd_init).')
lines.insert(last + 2, 'git -C dxb/xnu apply --reverse --check "$GITHUB_WORKSPACE/xnu/patches/' + NAME + '"')
script.write_bytes('\n'.join(lines).encode())

verify = REPO / 'tools/verify-gmu-service-patch.py'
source = verify.read_bytes().decode().replace('\r\n', '\n').split('\n')
at = [i for i, line in enumerate(source) if '0208-sweet-a618-system-memory-buffers.patch' in line]
assert len(at) == 1 and not any(NAME in line for line in source)
source.insert(at[0] + 1, "PATCHES += (('xnu/patches/" + NAME + "', {'bsd/dev/sweet_gpu_probe.c'}),)")
verify.write_bytes('\n'.join(source).encode())
print('verify list and reversal script updated')
