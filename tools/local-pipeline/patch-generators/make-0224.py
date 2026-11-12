"""Patch 0224: ENDPOINT_HALT requests are only acknowledged again (as up to 0219).

0223n (Clear Stall alone) went the same way as 0222n (End Transfer + Clear Stall + restart): at the
RNDIS start Windows cleared the halts of 0x83, 0x03 and 0x84, and right after the third the USB
console stopped and the phone no longer answered over the network. Up to 0219 those requests were
acknowledged without touching the controller, and RNDIS ran (0219n carried internet and a 55 MB
scp). So any DWC3 command on those endpoints at that moment wedges this gadget; the halt requests
go back to being acknowledged only, and logged. What stays from 0222: a failed TX start no longer
leaves the network IN endpoint busy for ever, and a TX transfer older than 2 s is ended (these are
what stopped ue0's TX during big copies on 0219n).
Base: CI build tree 40478936434 plus 0180, 0211, 0216, 0218, 0219, 0222 and 0223 for bsd/dev/sweet_usb.c.
"""




import re
import shutil
import subprocess
import tempfile
from pathlib import Path

REPO = Path('D:/ios-sweet/src/ios-sweet')
TREE = Path('D:/ios-sweet/build/xnu-buildtree-40478936434/xnu')
GIT = ['git', '-c', 'core.autocrlf=false', '-c', 'core.safecrlf=false']
NAME = '0224-sweet-usb-halt-acknowledged-only.patch'
USB = 'bsd/dev/sweet_usb.c'

with tempfile.TemporaryDirectory(prefix='make-0224-', dir='D:/ios-sweet/build') as scratch:
    work = Path(scratch)
    (work / USB).parent.mkdir(parents=True)
    shutil.copyfile(TREE / USB, work / USB)
    for earlier, only in (('0180-sweet-usb-console-and-b3a8-evidence.patch', True), ('0211-sweet-usb-console-and-rndis.patch', False), ('0216-sweet-usb-rndis-first.patch', False), ('0218-sweet-usb-rndis-no-zlp-answers.patch', False), ('0219-sweet-usb-reset-and-rndis-queue.patch', False), ('0222-sweet-usb-endpoint-halt-and-tx-watchdog.patch', False), ('0223-sweet-usb-halt-clear-stall-only.patch', False)):
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


edit('''	if (halt) {
		(void)ud_epcmd(ep, DEPCMD_SETSTALL, 0, 0, 0);
		return;
	}
	/*
	 * Clear Stall alone resets the data sequence; the transfer already started there stays
	 * (Linux 4.14 dwc3, this phone's own kernel). 0222 also ended and restarted it, 100 us apart,
	 * and the console died right after Windows' usual halt clears at RNDIS start.
	 */
	(void)ud_epcmd(ep, DEPCMD_CLEARSTALL, 0, 0, 0);
}
''', '''	/*
	 * Acknowledged only. End Transfer + Clear Stall + restart (0222) and Clear Stall alone (0223)
	 * both silenced the console and the network right after Windows' usual halt clears at the
	 * RNDIS start; acknowledging them, as up to 0219, kept RNDIS running.
	 */
	(void)halt;
}
''')

with tempfile.TemporaryDirectory(prefix='make-0224-', dir='D:/ios-sweet/build') as scratch:
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
    (Path('D:/ios-sweet/build') / 'sweet_usb.new0224.c').write_bytes(new.encode())
print(NAME, len(text.splitlines()), 'lines, forward and reverse verified')

script = REPO / 'tools/check-sweet-patch-reversal.sh'
lines = script.read_bytes().decode().replace('\r\n', '\n').split('\n')
assert not any(NAME in line for line in lines)
at = [i for i, line in enumerate(lines) if '0223-sweet-usb-halt-clear-stall-only.patch' in line and 'apply --reverse' in line]
assert len(at) == 1
for i in at:
    if '--exclude=' + USB not in lines[i]:
        lines[i] = lines[i].replace(' --check ', ' --check --exclude=' + USB + ' ', 1)
last = max(i for i, line in enumerate(lines) if 'apply --reverse --check' in line or 'grep -F' in line)
lines.insert(last + 1, '# 0224: ENDPOINT_HALT requests acknowledged only (as up to 0219).')
lines.insert(last + 2, 'git -C dxb/xnu apply --reverse --check "$GITHUB_WORKSPACE/xnu/patches/' + NAME + '"')
script.write_bytes('\n'.join(lines).encode())
print('reversal script updated')
