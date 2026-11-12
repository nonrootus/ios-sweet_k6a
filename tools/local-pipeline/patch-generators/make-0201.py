"""Patch 0201: set the accessibility preferences aside (Bold Text), so SpringBoard starts again.

SpringBoard crashed at every start (pc 0): lock screen -> CSTeachableMomentsContainerView
_addControlCenterTutors -> UIImage _imageWithStylePresets -> CUICatalog imageByStylingImage ->
CUIShapeEffectStack sharedCIContext -> CIContext contextWithOptions -> (no Metal)
internalContextWithEAGLContext -> CI::GLContext::init calls a NULL GL entry (Apple's EAGL has
no driver here). com.apple.uikitservices.userInterfaceStyleMode.plist held
UserInterfaceStyleMode = 2 (dark); the styled image is drawn only then. The file is renamed
with a suffix (never replaced, never deleted), which brings back the light default.
0199 removed dark mode (later boots log rc=2, the file stays gone), yet SpringBoard still crashed
at the same place: the owner had also turned on Bold Text, kept in com.apple.Accessibility.plist
(EnhancedTextLegibilityEnabled), which also makes UIKit style that image. The file is renamed
with a suffix (never replaced, never deleted); accessibility settings return to their defaults.
Base: CI build tree 40478936434 plus 0181, 0188, 0189, 0191, 0193, 0194, 0198, 0199 for bsd_init.c.
"""
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

REPO = Path('D:/ios-sweet/src/ios-sweet')
TREE = Path('D:/ios-sweet/build/xnu-buildtree-40478936434/xnu')
GIT = ['git', '-c', 'core.autocrlf=false', '-c', 'core.safecrlf=false']
NAME = '0201-sweet-accessibility-preference-aside.patch'
INIT = 'bsd/kern/bsd_init.c'
CHAIN = ['0181-sweet-renderer-ramdisk.patch', '0188-sweet-promote-staged-apps.patch', '0189-sweet-launchservices-store-once.patch',
         '0191-sweet-cpu-frequency-governor.patch', '0193-sweet-launchservices-store-extension-points.patch',
         '0194-sweet-amfi-iokit-service.patch', '0198-sweet-mesa-renderer-overlay.patch',
         '0199-sweet-dark-mode-preference-aside.patch']

with tempfile.TemporaryDirectory(prefix='make-0201-', dir='D:/ios-sweet/build') as scratch:
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

before = '''	printf("SWEET APPS: dark mode preference set aside rc=%d\\n", style);
}
'''
after = '''	printf("SWEET APPS: dark mode preference set aside rc=%d\\n", style);

	/*
	 * Bold Text (and the other accessibility settings) also make UIKit style that Control Center
	 * hint through CoreImage: SpringBoard kept crashing after dark mode was gone. Set the
	 * accessibility preferences aside the same way; their defaults come back.
	 */
	int accessibility = sweet_kernel_rename(
	    "/private/var/mobile/Library/Preferences/com.apple.Accessibility.plist",
	    "/private/var/mobile/Library/Preferences/com.apple.Accessibility.plist.sweet-bold");
	printf("SWEET APPS: accessibility preferences set aside rc=%d\\n", accessibility);
}
'''
assert base.count(before) == 1, base.count(before)
new = base.replace(before, after)

with tempfile.TemporaryDirectory(prefix='make-0201-', dir='D:/ios-sweet/build') as scratch:
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
at = [i for i, line in enumerate(lines) if '0199-sweet-dark-mode-preference-aside.patch' in line and 'apply --reverse' in line]
assert len(at) == 1
if '--exclude=' + INIT not in lines[at[0]]:
    lines[at[0]] = lines[at[0]].replace(' --check ', ' --check --exclude=' + INIT + ' ', 1)
last = max(i for i, line in enumerate(lines) if 'apply --reverse --check' in line or 'grep -F' in line)
lines.insert(last + 1, '# 0201: the accessibility preferences (Bold Text) set aside (SpringBoard crashed in CoreImage GL).')
lines.insert(last + 2, 'git -C dxb/xnu apply --reverse --check "$GITHUB_WORKSPACE/xnu/patches/' + NAME + '"')
script.write_bytes('\n'.join(lines).encode())
print('reversal script updated')
