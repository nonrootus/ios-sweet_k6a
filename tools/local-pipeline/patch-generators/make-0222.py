"""Patch 0222: the USB network keeps going: endpoint halt requests, failed TX starts, a TX watchdog.

0219n, Windows ICS over RNDIS, copying apps to the phone with scp: a 55 MB transfer went through,
then a 180 MB one stopped and later a 67 MB one too (sshd reset, then 192.168.137.2 unreachable
until the cable was replugged). The console showed the phone's TX counter stuck while RX still
counted, then CLEAR_FEATURE(ENDPOINT_HALT) from Windows for 0x83, 0x03 and 0x84 (it resets a pipe
after an error). Three faults in the gadget:
 - ud_tx_kick_locked() marked the network IN endpoint busy before Start Transfer and ignored its
   failure: one failed start and ue0 never sent again;
 - CLEAR_FEATURE / SET_FEATURE(ENDPOINT_HALT) were only acknowledged: the running transfer stayed,
   the data sequence was not reset (DWC3 Clear Stall), so after Windows reset a pipe the two sides
   disagreed and the link stopped;
 - nothing noticed a network TX transfer that never completes.
Now a failed start drops the frame and leaves the endpoint idle; ENDPOINT_HALT clear ends the
transfer, issues Clear Stall and restarts that endpoint's work (RX re-armed, TX queue kicked,
RNDIS notification re-sent), set issues Set Stall (Linux __dwc3_gadget_ep_set_halt); and a TX
transfer older than 2 s is ended and the queue goes on.
Base: CI build tree 40478936434 plus 0180, 0211, 0216, 0218 and 0219 for bsd/dev/sweet_usb.c.
"""


import re
import shutil
import subprocess
import tempfile
from pathlib import Path

REPO = Path('D:/ios-sweet/src/ios-sweet')
TREE = Path('D:/ios-sweet/build/xnu-buildtree-40478936434/xnu')
GIT = ['git', '-c', 'core.autocrlf=false', '-c', 'core.safecrlf=false']
NAME = '0222-sweet-usb-endpoint-halt-and-tx-watchdog.patch'
USB = 'bsd/dev/sweet_usb.c'

with tempfile.TemporaryDirectory(prefix='make-0222-', dir='D:/ios-sweet/build') as scratch:
    work = Path(scratch)
    (work / USB).parent.mkdir(parents=True)
    shutil.copyfile(TREE / USB, work / USB)
    for earlier, only in (('0180-sweet-usb-console-and-b3a8-evidence.patch', True), ('0211-sweet-usb-console-and-rndis.patch', False), ('0216-sweet-usb-rndis-first.patch', False), ('0218-sweet-usb-rndis-no-zlp-answers.patch', False), ('0219-sweet-usb-reset-and-rndis-queue.patch', False)):
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


edit('''	bool        nint_busy;              /* a RESPONSE_AVAILABLE in flight */
''', '''	bool        nint_busy;              /* a RESPONSE_AVAILABLE in flight */
	uint64_t    tx_started;             /* mach time the running network TX transfer started */
''')
edit('''		ud.net_tx_busy = true;
		ud.tx_frames++;
		ud_start_trb(ud.ep_ntx, ud.trb_ntx, ud.buf_ntx, (uint32_t)len, TRBCTL_NORMAL);
	}
}
''', '''		if (ud_start_trb(ud.ep_ntx, ud.trb_ntx, ud.buf_ntx, (uint32_t)len, TRBCTL_NORMAL)) {
			/* Before this the endpoint stayed "busy" for ever and ue0 never sent again. */
			static unsigned failed;
			if (failed++ < 8) {
				printf("SWEET USB: ue0 TX start failed, frame dropped\\n");
			}
			break;
		}
		ud.net_tx_busy = true;
		ud.tx_started = mach_absolute_time();
		ud.tx_frames++;
	}
}
''')
edit('''	} else if (req == 1 || req == 3) { /* CLEAR/SET_FEATURE (halt, remote wakeup) */
	} else {
''', '''	} else if ((req == 1 || req == 3) && type == 0x02 && value == 0) {
		ud_endpoint_halt((uint8_t)index, req == 3);     /* CLEAR/SET_FEATURE(ENDPOINT_HALT) */
	} else if (req == 1 || req == 3) { /* CLEAR/SET_FEATURE (remote wakeup and the like) */
	} else {
''')
edit('''static void
ud_thread(void *arg __unused, wait_result_t wr __unused)
{
	uint32_t ticks = 0;
''', '''/*
 * The network TX transfer has run for over 2 s: the host stopped reading it (a pipe reset, an
 * error). End it, drop the frame and go on with the queue, rather than never sending again.
 */
static void
ud_tx_watchdog(void)
{
	static uint64_t limit;
	if (limit == 0) {
		nanoseconds_to_absolutetime(2 * NSEC_PER_SEC, &limit);
	}
	if (!ud.net || !ud.net_tx_busy || mach_absolute_time() - ud.tx_started < limit) {
		return;
	}
	static unsigned fired;
	lck_mtx_lock(ud.lock);
	if (ud.net_tx_busy && mach_absolute_time() - ud.tx_started >= limit) {
		ud_end_transfer(ud.ep_ntx);
		ud.net_tx_busy = false;
		if (fired++ < 16) {
			printf("SWEET USB: ue0 TX stuck for 2 s: transfer ended, frame dropped\\n");
		}
		ud_tx_kick_locked();
	}
	lck_mtx_unlock(ud.lock);
}

static void
ud_thread(void *arg __unused, wait_result_t wr __unused)
{
	uint32_t ticks = 0;
''')
edit('''		if (ud.serial) {
			ud_serial_tx();
		}
		if (ud.net && (++ticks % 30000) == 0) {
''', '''		if (ud.serial) {
			ud_serial_tx();
		}
		ud_tx_watchdog();
		if (ud.net && (++ticks % 30000) == 0) {
''')
edit('''/*
 * USB reset (Linux dwc3_gadget_reset_interrupt): the host may reset the bus in the middle of a
''', '''#define DEPCMD_CLEARSTALL       5

/*
 * CLEAR_FEATURE / SET_FEATURE(ENDPOINT_HALT) for endpoint address addr (Linux
 * __dwc3_gadget_ep_set_halt). Windows clears the halt of a pipe it reset after an error; the
 * device must then end what runs there, reset the data sequence (Clear Stall) and start again.
 * Before this the request was only acknowledged, the sequence numbers no longer matched and the
 * network stopped until the cable was pulled.
 */
static void
ud_endpoint_halt(uint8_t addr, bool halt)
{
	unsigned ep = ((unsigned)(addr & 0x0f) << 1) | ((addr & 0x80) ? 1u : 0u);
	static unsigned logged;

	if (ep < 2 || ep >= 16) {
		return;
	}
	if (logged++ < 16) {
		printf("SWEET USB: %s halt of endpoint 0x%02x\\n", halt ? "set" : "clear", addr);
	}
	if (halt) {
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

/*
 * USB reset (Linux dwc3_gadget_reset_interrupt): the host may reset the bus in the middle of a
''')
edit('''static void ud_link_event(bool up);
''', '''static void ud_link_event(bool up);
static void ud_endpoint_halt(uint8_t addr, bool halt);
''')

with tempfile.TemporaryDirectory(prefix='make-0222-', dir='D:/ios-sweet/build') as scratch:
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
    (Path('D:/ios-sweet/build') / 'sweet_usb.new0222.c').write_bytes(new.encode())
print(NAME, len(text.splitlines()), 'lines, forward and reverse verified')

script = REPO / 'tools/check-sweet-patch-reversal.sh'
lines = script.read_bytes().decode().replace('\r\n', '\n').split('\n')
assert not any(NAME in line for line in lines)
at = [i for i, line in enumerate(lines) if '0219-sweet-usb-reset-and-rndis-queue.patch' in line and 'apply --reverse' in line]
assert len(at) == 1
for i in at:
    if '--exclude=' + USB not in lines[i]:
        lines[i] = lines[i].replace(' --check ', ' --check --exclude=' + USB + ' ', 1)
last = max(i for i, line in enumerate(lines) if 'apply --reverse --check' in line or 'grep -F' in line)
lines.insert(last + 1, '# 0222: USB network keeps going: endpoint halt requests, failed TX starts, TX watchdog.')
lines.insert(last + 2, 'git -C dxb/xnu apply --reverse --check "$GITHUB_WORKSPACE/xnu/patches/' + NAME + '"')
script.write_bytes('\n'.join(lines).encode())
print('reversal script updated')
