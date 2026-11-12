"""Patch 0210: no L1 clean+invalidate before every idle WFI.

With 0209 idle cores wait in WFI. On a non-Apple arm64 build cpu_idle() first calls
platform_cache_idle_enter(), which cleans and invalidates the whole L1 data cache by set/way
before every WFI. Here WFI is clock gating only (no PSCI CPU_SUSPEND, cores keep power), so the
caches stay coherent and that work is pure cost: time on the way to sleep and a cold L1 after
every wake, many times a second while CoreAnimation's worker threads park and wake. The Galaxy S9
fork of this project (syncmodz/ios-s9, patch 0099) measured and made the same change.
Base: CI build tree 40478936434 (it already holds 0065, the only earlier patch on cpu.c).
"""
import re
import subprocess
import tempfile
from pathlib import Path

REPO = Path('D:/ios-sweet/src/ios-sweet')
TREE = Path('D:/ios-sweet/build/xnu-buildtree-40478936434/xnu')
GIT = ['git', '-c', 'core.autocrlf=false', '-c', 'core.safecrlf=false']
NAME = '0210-sweet-idle-without-l1-flush.patch'
CPU = 'osfmk/arm64/cpu.c'
base = (TREE / CPU).read_bytes().decode()
assert '\r' not in base
new = base


def edit(before, after):
    global new
    assert new.count(before) == 1, (new.count(before), before[:80])
    new = new.replace(before, after)


edit('''	if (wfi) {
#if !defined(APPLE_ARM64_ARCH_FAMILY)
		platform_cache_idle_enter();
#endif
''', '''	if (wfi) {
#if !defined(APPLE_ARM64_ARCH_FAMILY)
#if defined(ARM64_BOARD_CONFIG_SWEET)
		/*
		 * WFI here is clock gating only (no PSCI suspend, the core keeps power), so its caches
		 * stay coherent: cleaning L1 by set/way before every WFI is only cost. sweetidleflush=1
		 * restores it.
		 */
		static int sweet_idle_flush = -1;
		if (__improbable(sweet_idle_flush < 0)) {
			int value = 0;
			sweet_idle_flush = PE_parse_boot_argn("sweetidleflush", &value, sizeof(value)) && value != 0;
		}
		if (sweet_idle_flush) {
			platform_cache_idle_enter();
		}
#else
		platform_cache_idle_enter();
#endif
#endif
''')

with tempfile.TemporaryDirectory(prefix='make-0210-', dir='D:/ios-sweet/build') as scratch:
    work = Path(scratch)
    for side, data in (('a', base), ('b', new)):
        path = work / side / CPU
        path.parent.mkdir(parents=True)
        path.write_bytes(data.encode())
    done = subprocess.run(GIT + ['diff', '--no-index', '--no-color', '--no-prefix', '-U3', 'a', 'b'], cwd=work, capture_output=True)
    assert done.returncode == 1, done.stderr
    text = re.sub(r'^diff --git .*\n(index .*\n)?', '', done.stdout.decode(), flags=re.M)
    assert text.startswith('--- a/') and '\r' not in text
    output = REPO / 'xnu/patches' / NAME
    output.write_bytes(text.encode())
    check = work / 'check' / CPU
    check.parent.mkdir(parents=True)
    check.write_bytes(base.encode())
    subprocess.run(GIT + ['apply', str(output)], cwd=work / 'check', check=True)
    assert check.read_bytes() == new.encode()
    subprocess.run(GIT + ['apply', '--reverse', str(output)], cwd=work / 'check', check=True)
    (Path('D:/ios-sweet/build/xnu-buildtree-40478936434/xnu/osfmk/arm64') / 'cpu.new0210.c').write_bytes(new.encode())
print(NAME, len(text.splitlines()), 'lines, forward and reverse verified')

script = REPO / 'tools/check-sweet-patch-reversal.sh'
lines = script.read_bytes().decode().replace('\r\n', '\n').split('\n')
assert not any(NAME in line for line in lines)
last = max(i for i, line in enumerate(lines) if 'apply --reverse --check' in line or 'grep -F' in line)
lines.insert(last + 1, '# 0210: no L1 clean+invalidate before every idle WFI.')
lines.insert(last + 2, 'git -C dxb/xnu apply --reverse --check "$GITHUB_WORKSPACE/xnu/patches/' + NAME + '"')
script.write_bytes('\n'.join(lines).encode())
print('reversal script updated')
