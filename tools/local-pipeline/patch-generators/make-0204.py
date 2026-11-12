"""Patch 0204: set MobileGestalt's cache aside once, for the sRGB device tree.

The device tree now says artwork-display-gamut = sRGB (image builder, SWEET_SRGB=1), as the K20
Pro port does: its answer HasExtendedColorDisplay decides whether CoreAnimation and UIKit use
10-bit w30r/b3a8 surfaces, which the CPU has to convert, or plain BGRA. The cache of MobileGestalt
was written while the tree said P3. It is renamed with a suffix, never replaced or deleted
(sweet_kernel_rename_below uses VFS_RENAME_EXCL, so this happens only once).
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
NAME = '0204-sweet-mobilegestalt-cache-aside.patch'
INIT = 'bsd/kern/bsd_init.c'
CHAIN = ['0181-sweet-renderer-ramdisk.patch', '0188-sweet-promote-staged-apps.patch', '0189-sweet-launchservices-store-once.patch',
         '0191-sweet-cpu-frequency-governor.patch', '0193-sweet-launchservices-store-extension-points.patch',
         '0194-sweet-amfi-iokit-service.patch', '0198-sweet-mesa-renderer-overlay.patch',
         '0199-sweet-dark-mode-preference-aside.patch', '0201-sweet-accessibility-preference-aside.patch']

with tempfile.TemporaryDirectory(prefix='make-0204-', dir='D:/ios-sweet/build') as scratch:
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

before = r'''	printf("SWEET APPS: accessibility preferences set aside rc=%d\n", accessibility);
}
'''
after = r'''	printf("SWEET APPS: accessibility preferences set aside rc=%d\n", accessibility);

	/*
	 * The device tree says the display is sRGB, so that CoreAnimation draws in plain BGRA and
	 * not in 10-bit surfaces. MobileGestalt's cache still holds the answer for a P3 display:
	 * set it aside once and it is made again.
	 */
	int gestalt = sweet_kernel_rename_below("/private/var/containers/Shared/SystemGroup",
	    "Library/Caches/com.apple.MobileGestalt.plist", ".sweet-p3");
	printf("SWEET APPS: MobileGestalt caches set aside for sRGB=%d\n", gestalt);
}
'''
assert base.count(before) == 1, base.count(before)
new = base.replace(before, after)

with tempfile.TemporaryDirectory(prefix='make-0204-', dir='D:/ios-sweet/build') as scratch:
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
at = [i for i, line in enumerate(lines) if '0201-sweet-accessibility-preference-aside.patch' in line and 'apply --reverse' in line]
assert len(at) == 1
if '--exclude=' + INIT not in lines[at[0]]:
    lines[at[0]] = lines[at[0]].replace(' --check ', ' --check --exclude=' + INIT + ' ', 1)
last = max(i for i, line in enumerate(lines) if 'apply --reverse --check' in line or 'grep -F' in line)
lines.insert(last + 1, '# 0204: MobileGestalt cache set aside once for the sRGB device tree.')
lines.insert(last + 2, 'git -C dxb/xnu apply --reverse --check "$GITHUB_WORKSPACE/xnu/patches/' + NAME + '"')
script.write_bytes('\n'.join(lines).encode())
print('reversal script updated')
