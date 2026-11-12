"""Patch 0209: CPU idle (WFI) after the GPU is up, when the boot-arg wfi is not 0.

jtag=1 keeps idle_enable FALSE: the GMU/GPU bring-up guards require no CPU idle at all. So idle
cores spun forever and the phone ran warm doing nothing (owner: warm while lying idle). Once the
GPU and the CPU governor are started (all before this point in bsd_init), idle is enabled if
wfi != 0: cores wait in WFI, which is clock gating only (no PSCI suspend, so no cluster power
collapse and no RPMh sleep set under the GPU's votes). Images keep wfi=0 unless SWEET_WFI=1.
Base: CI build tree 40478936434 plus the chain below for bsd_init.c.
"""
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

REPO = Path('D:/ios-sweet/src/ios-sweet')
TREE = Path('D:/ios-sweet/build/xnu-buildtree-40478936434/xnu')
GIT = ['git', '-c', 'core.autocrlf=false', '-c', 'core.safecrlf=false']
NAME = '0209-sweet-cpu-idle-after-gpu.patch'
INIT = 'bsd/kern/bsd_init.c'
CHAIN = ['0181-sweet-renderer-ramdisk.patch', '0188-sweet-promote-staged-apps.patch', '0189-sweet-launchservices-store-once.patch',
         '0191-sweet-cpu-frequency-governor.patch', '0193-sweet-launchservices-store-extension-points.patch',
         '0194-sweet-amfi-iokit-service.patch', '0198-sweet-mesa-renderer-overlay.patch',
         '0199-sweet-dark-mode-preference-aside.patch', '0201-sweet-accessibility-preference-aside.patch',
         '0204-sweet-mobilegestalt-cache-aside.patch']

with tempfile.TemporaryDirectory(prefix='make-0209-', dir='D:/ios-sweet/build') as scratch:
    work = Path(scratch)
    (work / INIT).parent.mkdir(parents=True)
    shutil.copyfile(TREE / INIT, work / INIT)
    for name in CHAIN:
        patch = work / name
        patch.write_bytes(subprocess.check_output(GIT + ['show', 'HEAD:xnu/patches/' + name], cwd=REPO))
        if INIT not in subprocess.check_output(GIT + ['apply', '--numstat', name], cwd=work, text=True):
            continue
        subprocess.run(GIT + ['apply', '--include=' + INIT, name], cwd=work, check=True)
    base = (work / INIT).read_bytes().decode()

before = r'''		extern void sweet_cpufreq_start(void);
		sweet_cpufreq_start();
'''
after = r'''		extern void sweet_cpufreq_start(void);
		sweet_cpufreq_start();
		/*
		 * jtag=1 keeps idle_enable FALSE, so the GPU bring-up above ran with no CPU idle (its
		 * guards require that), and idle cores went on spinning: warm while doing nothing. With
		 * wfi != 0 they wait in WFI from here on: clock gating only, no PSCI suspend, so no
		 * cluster power collapse and no RPMh sleep set under the GPU's votes.
		 */
		extern boolean_t idle_enable;
		unsigned int sweet_wfi = 1;
		(void)PE_parse_boot_argn("wfi", &sweet_wfi, sizeof(sweet_wfi));
		if (sweet_wfi != 0 && !idle_enable) {
			idle_enable = TRUE;
			printf("SWEET IDLE: CPU idle enabled after GPU start (wfi=%u)\n", sweet_wfi);
		} else {
			printf("SWEET IDLE: CPU idle unchanged (wfi=%u idle_enable=%d)\n", sweet_wfi, idle_enable);
		}
'''
assert base.count(before) == 1, base.count(before)
new = base.replace(before, after)

with tempfile.TemporaryDirectory(prefix='make-0209-', dir='D:/ios-sweet/build') as scratch:
    work = Path(scratch)
    for side, data in (('a', base), ('b', new)):
        path = work / side / INIT
        path.parent.mkdir(parents=True)
        path.write_bytes(data.encode())
    done = subprocess.run(GIT + ['diff', '--no-index', '--no-color', '--no-prefix', '-U3', 'a', 'b'], cwd=work, capture_output=True)
    assert done.returncode == 1, done.stderr
    text = re.sub(r'^diff --git .*\n(index .*\n)?', '', done.stdout.decode(), flags=re.M)
    assert text.startswith('--- a/') and '\r' not in text
    output = REPO / 'xnu/patches' / NAME
    output.write_bytes(text.encode())
    check = work / 'check' / INIT
    check.parent.mkdir(parents=True)
    check.write_bytes(base.encode())
    subprocess.run(GIT + ['apply', str(output)], cwd=work / 'check', check=True)
    assert check.read_bytes() == new.encode()
    subprocess.run(GIT + ['apply', '--reverse', str(output)], cwd=work / 'check', check=True)
print(NAME, len(text.splitlines()), 'lines, forward and reverse verified')

script = REPO / 'tools/check-sweet-patch-reversal.sh'
lines = script.read_bytes().decode().replace('\r\n', '\n').split('\n')
assert not any(NAME in line for line in lines)
at = [i for i, line in enumerate(lines) if '0191-sweet-cpu-frequency-governor.patch' in line and 'apply --reverse' in line]
assert len(at) == 1
if '--exclude=' + INIT not in lines[at[0]]:
    lines[at[0]] = lines[at[0]].replace(' --check ', ' --check --exclude=' + INIT + ' ', 1)
last = max(i for i, line in enumerate(lines) if 'apply --reverse --check' in line or 'grep -F' in line)
lines.insert(last + 1, '# 0209: CPU idle (WFI) after the GPU is up when wfi != 0.')
lines.insert(last + 2, 'git -C dxb/xnu apply --reverse --check "$GITHUB_WORKSPACE/xnu/patches/' + NAME + '"')
script.write_bytes('\n'.join(lines).encode())
print('reversal script updated')
