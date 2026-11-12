"""Patch 0223: ENDPOINT_HALT clear only resets the data sequence (Clear Stall), as Linux 4.x dwc3 did.

0222n: Windows clears the halt of the RNDIS endpoints (0x83, 0x03, 0x84) whenever it starts the
RNDIS function, as it also did on 0219n. 0222 answered that with End Transfer + Clear Stall +
restarting the endpoint at once; right after the third one the USB console fell silent for good
(the network still answered a TCP connect, then scp stopped after 57 s). Linux only sends Clear
Stall after the End Transfer completion event has arrived (DWC3_EP_END_TRANSFER_PENDING); this
gadget waited 100 us. The kernel this phone shipped with (Linux 4.14 dwc3) handled the request
with Clear Stall alone, leaving the started transfer in place, and that is what this does now.
Set halt keeps Set Stall. The failed-TX-start fix and the 2 s TX watchdog of 0222 stay.
Base: CI build tree 40478936434 plus 0180, 0211, 0216, 0218, 0219 and 0222 for bsd/dev/sweet_usb.c.
"""



import re
import shutil
import subprocess
import tempfile
from pathlib import Path

REPO = Path('D:/ios-sweet/src/ios-sweet')
TREE = Path('D:/ios-sweet/build/xnu-buildtree-40478936434/xnu')
GIT = ['git', '-c', 'core.autocrlf=false', '-c', 'core.safecrlf=false']
NAME = '0223-sweet-usb-halt-clear-stall-only.patch'
USB = 'bsd/dev/sweet_usb.c'

with tempfile.TemporaryDirectory(prefix='make-0223-', dir='D:/ios-sweet/build') as scratch:
    work = Path(scratch)
    (work / USB).parent.mkdir(parents=True)
    shutil.copyfile(TREE / USB, work / USB)
    for earlier, only in (('0180-sweet-usb-console-and-b3a8-evidence.patch', True), ('0211-sweet-usb-console-and-rndis.patch', False), ('0216-sweet-usb-rndis-first.patch', False), ('0218-sweet-usb-rndis-no-zlp-answers.patch', False), ('0219-sweet-usb-reset-and-rndis-queue.patch', False), ('0222-sweet-usb-endpoint-halt-and-tx-watchdog.patch', False)):
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
		ud_end_transfer(ep);
		(void)ud_epcmd(ep, DEPCMD_SETSTALL, 0, 0, 0);
		return;
	}
	ud_end_transfer(ep);
	(void)ud_epcmd(ep, DEPCMD_CLEARSTALL, 0, 0, 0);
	if (!ud.configured) {
		return;
	}
	if (ud.net && ep == ud.ep_nrx) {
		ud_rx_arm();
	} else if (ud.net && ep == ud.ep_ntx) {
		lck_mtx_lock(ud.lock);
		ud.net_tx_busy = false;
		ud_tx_kick_locked();
		lck_mtx_unlock(ud.lock);
	} else if (ud.rndis && ep == ud.ep_nint) {
		ud.nint_busy = false;
		if (ud.nint_pending) {
			ud.nint_pending--;
			rndis_notify();
		}
	} else if (ud.serial && ep == EP_RX) {
		ud_serial_rx_arm();
	} else if (ud.serial && ep == EP_TX) {
		ud.tx_busy = false;
	}
}
''', '''	if (halt) {
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
''')

with tempfile.TemporaryDirectory(prefix='make-0223-', dir='D:/ios-sweet/build') as scratch:
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
    (Path('D:/ios-sweet/build') / 'sweet_usb.new0223.c').write_bytes(new.encode())
print(NAME, len(text.splitlines()), 'lines, forward and reverse verified')

script = REPO / 'tools/check-sweet-patch-reversal.sh'
lines = script.read_bytes().decode().replace('\r\n', '\n').split('\n')
assert not any(NAME in line for line in lines)
at = [i for i, line in enumerate(lines) if '0222-sweet-usb-endpoint-halt-and-tx-watchdog.patch' in line and 'apply --reverse' in line]
assert len(at) == 1
for i in at:
    if '--exclude=' + USB not in lines[i]:
        lines[i] = lines[i].replace(' --check ', ' --check --exclude=' + USB + ' ', 1)
last = max(i for i, line in enumerate(lines) if 'apply --reverse --check' in line or 'grep -F' in line)
lines.insert(last + 1, '# 0223: ENDPOINT_HALT clear is Clear Stall only (Linux 4.14 dwc3).')
lines.insert(last + 2, 'git -C dxb/xnu apply --reverse --check "$GITHUB_WORKSPACE/xnu/patches/' + NAME + '"')
script.write_bytes('\n'.join(lines).encode())
print('reversal script updated')
