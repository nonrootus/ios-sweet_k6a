"""Patch 0216: RNDIS first in the sweetusb=4 composite device, so Windows' RNDIS driver starts.

0215n (sweetusb=4) on Windows 10 19045: the composite parent and the ACM console (MI_00, usbser)
started, the RNDIS function (MI_02, wceisvista.inf / usbrndis6) failed with Code 10
(STATUS_UNSUCCESSFUL, Kernel-PnP event 411) before sending a single class request: the console shows
no SEND_ENCAPSULATED_COMMAND at all. Windows' RNDIS driver expects its function to start at
interface 0 of the configuration (as on Android tethering, where RNDIS always comes first), so the
RNDIS function now takes interfaces 0/1 and the ACM console 2/3. The endpoints stay as they were.
The product ID moves to pid.codes 1209:0004 (private test ID), so Windows does not reuse the device
nodes it made for the 0003 layout (usbser on MI_00).
Base: CI build tree 40478936434 plus 0180 and 0211 for bsd/dev/sweet_usb.c.
"""
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

REPO = Path('D:/ios-sweet/src/ios-sweet')
TREE = Path('D:/ios-sweet/build/xnu-buildtree-40478936434/xnu')
GIT = ['git', '-c', 'core.autocrlf=false', '-c', 'core.safecrlf=false']
NAME = '0216-sweet-usb-rndis-first.patch'
USB = 'bsd/dev/sweet_usb.c'

with tempfile.TemporaryDirectory(prefix='make-0216-', dir='D:/ios-sweet/build') as scratch:
    work = Path(scratch)
    (work / USB).parent.mkdir(parents=True)
    shutil.copyfile(TREE / USB, work / USB)
    for earlier, only in (('0180-sweet-usb-console-and-b3a8-evidence.patch', True), ('0211-sweet-usb-console-and-rndis.patch', False)):
        patch = work / earlier
        patch.write_bytes(subprocess.check_output(GIT + ['show', 'HEAD:xnu/patches/' + earlier], cwd=REPO))
        subprocess.run(GIT + ['apply'] + (['--include=' + USB] if only else []) + [patch.name], cwd=work, check=True)
    base = (work / USB).read_bytes().decode()
assert '\r' not in base and 'ud_combo_cfg_desc' in base
new = base


def edit(before, after, count=1):
    global new
    assert new.count(before) == count, (new.count(before), before[:90])
    new = new.replace(before, after)


edit('''/* sweetusb=4: console (ACM, interfaces 0/1) and RNDIS (interfaces 2/3), each behind an IAD. */
static const uint8_t ud_combo_dev_desc[18] = {
	18, 1, 0x00, 0x02, 0xef, 0x02, 0x01, 64,
	0x09, 0x12, 0x03, 0x00, 0x00, 0x01, 1, 2, 3, 1,
};
static const uint8_t ud_combo_cfg_desc[] = {
	9, 2, 141, 0, 4, 1, 0, 0x80, 250,
	8, 0x0b, 0, 2, 0x02, 0x02, 0x01, 0,       /* IAD: ACM console */
	9, 4, 0, 0, 1, 0x02, 0x02, 0x01, 0,
	5, 0x24, 0x00, 0x10, 0x01,
	5, 0x24, 0x01, 0, 1,
	4, 0x24, 0x02, 2,
	5, 0x24, 0x06, 0, 1,
	7, 5, 0x82, 0x03, 16, 0, 9,
	9, 4, 1, 0, 2, 0x0a, 0, 0, 0,
	7, 5, 0x81, 0x02, 0x00, 0x02, 0,
	7, 5, 0x01, 0x02, 0x00, 0x02, 0,
	8, 0x0b, 2, 2, 0xe0, 0x01, 0x03, 0,       /* IAD: RNDIS (wireless controller / RNDIS) */
	9, 4, 2, 0, 1, 0xe0, 0x01, 0x03, 0,
	5, 0x24, 0x00, 0x10, 0x01,
	5, 0x24, 0x01, 0, 3,
	4, 0x24, 0x02, 0,
	5, 0x24, 0x06, 2, 3,
	7, 5, 0x84, 0x03, 8, 0, 9,
	9, 4, 3, 0, 2, 0x0a, 0, 0, 0,
	7, 5, 0x83, 0x02, 0x00, 0x02, 0,
	7, 5, 0x03, 0x02, 0x00, 0x02, 0,
};
''', '''/*
 * sweetusb=4: RNDIS (interfaces 0/1) and the ACM console (interfaces 2/3), each behind an IAD.
 * RNDIS comes first: Windows' RNDIS driver (usbrndis6) failed to start (Code 10, no class request
 * sent) while it sat at interfaces 2/3. Product 1209:0004 for this layout.
 */
#define UD_RNDIS_IF     0
#define UD_COMBO_ACM_IF 2
static const uint8_t ud_combo_dev_desc[18] = {
	18, 1, 0x00, 0x02, 0xef, 0x02, 0x01, 64,
	0x09, 0x12, 0x04, 0x00, 0x00, 0x01, 1, 2, 3, 1,
};
static const uint8_t ud_combo_cfg_desc[] = {
	9, 2, 141, 0, 4, 1, 0, 0x80, 250,
	8, 0x0b, 0, 2, 0xe0, 0x01, 0x03, 0,       /* IAD: RNDIS (wireless controller / RNDIS) */
	9, 4, 0, 0, 1, 0xe0, 0x01, 0x03, 0,
	5, 0x24, 0x00, 0x10, 0x01,
	5, 0x24, 0x01, 0, 1,
	4, 0x24, 0x02, 0,
	5, 0x24, 0x06, 0, 1,
	7, 5, 0x84, 0x03, 8, 0, 9,
	9, 4, 1, 0, 2, 0x0a, 0, 0, 0,
	7, 5, 0x83, 0x02, 0x00, 0x02, 0,
	7, 5, 0x03, 0x02, 0x00, 0x02, 0,
	8, 0x0b, 2, 2, 0x02, 0x02, 0x01, 0,       /* IAD: ACM console */
	9, 4, 2, 0, 1, 0x02, 0x02, 0x01, 0,
	5, 0x24, 0x00, 0x10, 0x01,
	5, 0x24, 0x01, 0, 3,
	4, 0x24, 0x02, 2,
	5, 0x24, 0x06, 2, 3,
	7, 5, 0x82, 0x03, 16, 0, 9,
	9, 4, 3, 0, 2, 0x0a, 0, 0, 0,
	7, 5, 0x81, 0x02, 0x00, 0x02, 0,
	7, 5, 0x01, 0x02, 0x00, 0x02, 0,
};
''')
edit('''	if (ud.rndis && (type & 0x60) == 0x20 && (index & 0xff) == 2) {
''', '''	/* The console's control interface: 0 alone, UD_COMBO_ACM_IF beside RNDIS. */
	const uint16_t acm_if = ud.rndis ? UD_COMBO_ACM_IF : 0;
	if (ud.rndis && (type & 0x60) == 0x20 && (index & 0xff) == UD_RNDIS_IF) {
''')
edit('''		if (type == 0x21 && req == 0x20 && index == 0 && length == sizeof(ud.serial_line)) {
''', '''		if (type == 0x21 && req == 0x20 && index == acm_if && length == sizeof(ud.serial_line)) {
''')
edit('''		} else if (type == 0xa1 && req == 0x21 && index == 0) {
''', '''		} else if (type == 0xa1 && req == 0x21 && index == acm_if) {
''')
edit('''		} else if (type == 0x21 && req == 0x22 && index == 0 && length == 0) {
''', '''		} else if (type == 0x21 && req == 0x22 && index == acm_if && length == 0) {
''')

with tempfile.TemporaryDirectory(prefix='make-0216-', dir='D:/ios-sweet/build') as scratch:
    work = Path(scratch)
    for side, data in (('a', base), ('b', new)):
        path = work / side / USB
        path.parent.mkdir(parents=True)
        path.write_bytes(data.encode())
    done = subprocess.run(GIT + ['diff', '--no-index', '--no-color', '--no-prefix', '-U3', 'a', 'b'], cwd=work, capture_output=True)
    assert done.returncode == 1, done.stderr
    text = re.sub(r'^diff --git .*\n(index .*\n)?', '', done.stdout.decode(), flags=re.M)
    assert text.startswith('--- a/') and '\r' not in text
    output = REPO / 'xnu/patches' / NAME
    output.write_bytes(text.encode())
    check = work / 'check' / USB
    check.parent.mkdir(parents=True)
    check.write_bytes(base.encode())
    subprocess.run(GIT + ['apply', str(output)], cwd=work / 'check', check=True)
    assert check.read_bytes() == new.encode()
    subprocess.run(GIT + ['apply', '--reverse', str(output)], cwd=work / 'check', check=True)
    (Path('D:/ios-sweet/build') / 'sweet_usb.new0216.c').write_bytes(new.encode())
print(NAME, len(text.splitlines()), 'lines, forward and reverse verified')

script = REPO / 'tools/check-sweet-patch-reversal.sh'
lines = script.read_bytes().decode().replace('\r\n', '\n').split('\n')
assert not any(NAME in line for line in lines)
at = [i for i, line in enumerate(lines) if '0211-sweet-usb-console-and-rndis.patch' in line and 'apply --reverse' in line]
assert len(at) == 1
for i in at:
    if '--exclude=' + USB not in lines[i]:
        lines[i] = lines[i].replace(' --check ', ' --check --exclude=' + USB + ' ', 1)
last = max(i for i, line in enumerate(lines) if 'apply --reverse --check' in line or 'grep -F' in line)
lines.insert(last + 1, '# 0216: RNDIS first in the sweetusb=4 composite device (Windows RNDIS starts).')
lines.insert(last + 2, 'git -C dxb/xnu apply --reverse --check "$GITHUB_WORKSPACE/xnu/patches/' + NAME + '"')
script.write_bytes('\n'.join(lines).encode())
print('reversal script updated')
