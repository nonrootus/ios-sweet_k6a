"""Patch 0218: no RNDIS response a whole number of EP0 packets long (Windows waited for more).

0216n: Windows 10 now starts its RNDIS driver: INITIALIZE (24 bytes) and its completion, then a
28-byte QUERY (OID_GEN_SUPPORTED_LIST) and GET_ENCAPSULATED_RESPONSE with wLength 4096, and then
nothing; the adapter failed with Code 10. The answer, 24 bytes + 26 OIDs = 128 bytes, is exactly
two 64-byte EP0 packets and shorter than wLength, so the host waits for a zero-length packet that
this driver never sends. Linux's gadget lists 28 OIDs (136 bytes). The list gets
OID_GEN_VENDOR_DRIVER_VERSION (as Linux's rndis.c: 1), so it is 132 bytes; and any other response
of a multiple of 64 bytes shorter than wLength gets one zero byte more (MessageLength still says
the real length) rather than a stalled control transfer.
Base: CI build tree 40478936434 plus 0180, 0211 and 0216 for bsd/dev/sweet_usb.c.
"""
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

REPO = Path('D:/ios-sweet/src/ios-sweet')
TREE = Path('D:/ios-sweet/build/xnu-buildtree-40478936434/xnu')
GIT = ['git', '-c', 'core.autocrlf=false', '-c', 'core.safecrlf=false']
NAME = '0218-sweet-usb-rndis-no-zlp-answers.patch'
USB = 'bsd/dev/sweet_usb.c'

with tempfile.TemporaryDirectory(prefix='make-0218-', dir='D:/ios-sweet/build') as scratch:
    work = Path(scratch)
    (work / USB).parent.mkdir(parents=True)
    shutil.copyfile(TREE / USB, work / USB)
    for earlier, only in (('0180-sweet-usb-console-and-b3a8-evidence.patch', True), ('0211-sweet-usb-console-and-rndis.patch', False), ('0216-sweet-usb-rndis-first.patch', False)):
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


edit('''		0x01010101, 0x01010102, 0x01010103, 0x01010104,
''', '''		0x00010116,
		0x01010101, 0x01010102, 0x01010103, 0x01010104,
''')
edit('''	case 0x0001010e: value = ud.rndis_filter; break;
''', '''	case 0x0001010e: value = ud.rndis_filter; break;
	case 0x00010116: value = 1; break;                      /* vendor driver version (as Linux) */
''')
edit('''			if (ud.rndis_resp_len) {
				n = ud.rndis_resp_len;
				memcpy(data, ud.rndis_resp, n);
				ud.rndis_resp_len = 0;
''', '''			if (ud.rndis_resp_len) {
				n = ud.rndis_resp_len;
				memcpy(data, ud.rndis_resp, n);
				ud.rndis_resp_len = 0;
				/* A whole number of 64-byte packets shorter than wLength would need a
				 * zero-length packet to end it, which EP0 here does not send: one zero byte
				 * more instead (MessageLength still gives the response's own length). */
				if ((n % 64) == 0 && n < length && n < sizeof(ud.rndis_resp)) {
					data[n++] = 0;
				}
''')

with tempfile.TemporaryDirectory(prefix='make-0218-', dir='D:/ios-sweet/build') as scratch:
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
    (Path('D:/ios-sweet/build') / 'sweet_usb.new0218.c').write_bytes(new.encode())
print(NAME, len(text.splitlines()), 'lines, forward and reverse verified')

script = REPO / 'tools/check-sweet-patch-reversal.sh'
lines = script.read_bytes().decode().replace('\r\n', '\n').split('\n')
assert not any(NAME in line for line in lines)
at = [i for i, line in enumerate(lines) if '0216-sweet-usb-rndis-first.patch' in line and 'apply --reverse' in line]
assert len(at) == 1
for i in at:
    if '--exclude=' + USB not in lines[i]:
        lines[i] = lines[i].replace(' --check ', ' --check --exclude=' + USB + ' ', 1)
last = max(i for i, line in enumerate(lines) if 'apply --reverse --check' in line or 'grep -F' in line)
lines.insert(last + 1, '# 0218: RNDIS answers never a whole number of EP0 packets (no ZLP needed).')
lines.insert(last + 2, 'git -C dxb/xnu apply --reverse --check "$GITHUB_WORKSPACE/xnu/patches/' + NAME + '"')
script.write_bytes('\n'.join(lines).encode())
print('reversal script updated')
