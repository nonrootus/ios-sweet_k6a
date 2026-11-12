"""Patch 0219: the USB device survives a bus reset; RNDIS notifications and answers are queued.

0218n on Windows 10: RNDIS came up (packet filter 0xb, 868 frames in, 36 out, 475 76-byte SETs)
and after about four minutes the phone stopped answering on USB: Windows showed "device descriptor
request failed" and the console stopped. The log's last control requests were two 76-byte
SEND_ENCAPSULATED_COMMANDs with no GET_ENCAPSULATED_RESPONSE between them, i.e. Windows did not
get (or gave up on) a RESPONSE_AVAILABLE. The gadget had three ways to wedge there:
 - rndis_notify() started the interrupt endpoint again while its previous notification was still
   in flight (Start Transfer on a busy endpoint fails, the notification is lost);
 - one answer buffer: a second command before the first answer was read overwrote it;
 - a USB reset only cleared the address: EP0 stayed in its data or status stage with no SETUP
   TRB armed, so after Windows reset the port its GET_DESCRIPTOR never completed.
Now: one RESPONSE_AVAILABLE at a time (the rest are sent as each completes), up to four unread
answers, the transfer resource index of every started transfer is kept, a bus reset ends every
active transfer (Linux dwc3_gadget_reset_interrupt / dwc3_ep0_stall_and_restart), unconfigures the
device and arms SETUP again, and a control data stage the host abandons (XferNotReady for the other
direction) stalls and restarts EP0. The first SETs log their OID.
Base: CI build tree 40478936434 plus 0180, 0211, 0216 and 0218 for bsd/dev/sweet_usb.c.
"""

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

REPO = Path('D:/ios-sweet/src/ios-sweet')
TREE = Path('D:/ios-sweet/build/xnu-buildtree-40478936434/xnu')
GIT = ['git', '-c', 'core.autocrlf=false', '-c', 'core.safecrlf=false']
NAME = '0219-sweet-usb-reset-and-rndis-queue.patch'
USB = 'bsd/dev/sweet_usb.c'

with tempfile.TemporaryDirectory(prefix='make-0219-', dir='D:/ios-sweet/build') as scratch:
    work = Path(scratch)
    (work / USB).parent.mkdir(parents=True)
    shutil.copyfile(TREE / USB, work / USB)
    for earlier, only in (('0180-sweet-usb-console-and-b3a8-evidence.patch', True), ('0211-sweet-usb-console-and-rndis.patch', False), ('0216-sweet-usb-rndis-first.patch', False), ('0218-sweet-usb-rndis-no-zlp-answers.patch', False)):
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


edit('''	uint8_t     rndis_resp[512];
	uint32_t    rndis_resp_len;
''', '''	uint8_t     rndis_resp[512];        /* the answer being built */
	uint32_t    rndis_resp_len;
	uint8_t     rndis_q[4][512];        /* answers not read yet, oldest first */
	uint32_t    rndis_q_len[4];
	unsigned    rndis_q_head, rndis_q_count;
	bool        nint_busy;              /* a RESPONSE_AVAILABLE in flight */
	unsigned    nint_pending;           /* ... and how many more to send after it */
	uint8_t     rsc[16];                /* each physical endpoint's transfer resource index */
	bool        active[16];             /* a transfer started there and not completed */
''')
edit('''	uint64_t tpa = ud.dma_pa + trb;
	return ud_epcmd(ep, DEPCMD_STARTTRANSFER, (uint32_t)(tpa >> 32), (uint32_t)tpa, 0);
}
''', '''	uint64_t tpa = ud.dma_pa + trb;
	int err = ud_epcmd(ep, DEPCMD_STARTTRANSFER, (uint32_t)(tpa >> 32), (uint32_t)tpa, 0);
	if (!err && ep < 16) {
		ud.rsc[ep] = (uint8_t)((dwc_rd(DEPCMD(ep)) >> 16) & 0x7f);
		ud.active[ep] = true;
	}
	return err;
}
''')
edit('''static void
ud_stall(void)
{
	ud_epcmd(0, DEPCMD_SETSTALL, 0, 0, 0);
	ud_start_setup();
}
''', '''static void
ud_stall(void)
{
	ud_epcmd(0, DEPCMD_SETSTALL, 0, 0, 0);
	ud_start_setup();
}

#define DEPCMD_ENDTRANSFER      8
#define DEPCMD_HIPRI_FORCERM    (1u << 11)

/* End the transfer running on physical endpoint ep, if any. */
static void
ud_end_transfer(unsigned ep)
{
	if (ep >= 16 || !ud.active[ep]) {
		return;
	}
	ud.active[ep] = false;
	(void)ud_epcmd(ep, DEPCMD_ENDTRANSFER | DEPCMD_HIPRI_FORCERM | ((uint32_t)ud.rsc[ep] << 16), 0, 0, 0);
	delay(100);     /* as Linux dwc3: the command completes before the controller is done with it */
}
''')
edit('''	uint8_t *n = (uint8_t *)(ud.dma + ud.buf_nnotify);
	memset(n, 0, 8);
	n[0] = 1;
	ud_start_trb(ud.ep_nint, ud.trb_nint, ud.buf_nnotify, 8, TRBCTL_NORMAL);
}
''', '''	/* One at a time on the interrupt endpoint; the others go as each one completes. */
	if (ud.nint_busy) {
		ud.nint_pending++;
		return;
	}
	uint8_t *n = (uint8_t *)(ud.dma + ud.buf_nnotify);
	memset(n, 0, 8);
	n[0] = 1;
	ud.nint_busy = ud_start_trb(ud.ep_nint, ud.trb_nint, ud.buf_nnotify, 8, TRBCTL_NORMAL) == 0;
}
''')
edit('''		rndis_put32(r, RNDIS_SET | RNDIS_CMPLT);
''', '''		static unsigned sets_logged;
		if (sets_logged++ < 16) {
			printf("SWEET USB: RNDIS set OID 0x%08x (%u bytes) -> 0x%x\\n", oid, blen, status);
		}
		rndis_put32(r, RNDIS_SET | RNDIS_CMPLT);
''')
edit('''	default:
		return;
	}
	rndis_notify();
}
''', '''	default:
		return;
	}
	if (ud.rndis_q_count == 4) {
		printf("SWEET USB: RNDIS answers not read, the oldest dropped\\n");
		ud.rndis_q_head = (ud.rndis_q_head + 1) % 4;
		ud.rndis_q_count--;
	}
	unsigned slot = (ud.rndis_q_head + ud.rndis_q_count) % 4;
	memcpy(ud.rndis_q[slot], r, ud.rndis_resp_len);
	ud.rndis_q_len[slot] = ud.rndis_resp_len;
	ud.rndis_q_count++;
	ud.rndis_resp_len = 0;
	rndis_notify();
}
''')
edit('''			if (ud.rndis_resp_len) {
				n = ud.rndis_resp_len;
				memcpy(data, ud.rndis_resp, n);
				ud.rndis_resp_len = 0;
''', '''			if (ud.rndis_q_count) {
				n = ud.rndis_q_len[ud.rndis_q_head];
				memcpy(data, ud.rndis_q[ud.rndis_q_head], n);
				ud.rndis_q_head = (ud.rndis_q_head + 1) % 4;
				ud.rndis_q_count--;
''')
edit('''static void
ud_event(uint32_t ev)
{
	if (ev & 1) {                   /* device event */
		uint32_t type = (ev >> 8) & 0xf;
		if (type == 1) {        /* USB reset */
			dwc_wr(DCFG, dwc_rd(DCFG) & ~(0x7fu << 3));
			printf("SWEET USB: bus reset\\n");
''', '''/*
 * USB reset (Linux dwc3_gadget_reset_interrupt): the host may reset the bus in the middle of a
 * control transfer (Windows does when a request times out). Every transfer still running ends,
 * the device is unconfigured and SETUP is armed again. Before this EP0 stayed in its data or
 * status stage and the host's next GET_DESCRIPTOR never completed.
 */
static void
ud_bus_reset(void)
{
	static unsigned resets;
	bool was = ud.configured || ud.state != EP0_SETUP;

	if (ud.net && ud.lock != NULL) {
		lck_mtx_lock(ud.lock);
	}
	for (unsigned ep = 2; ep < 16; ep++) {
		ud_end_transfer(ep);
	}
	ud.configured = false;
	ud.net_tx_busy = false;
	ud.tx_busy = false;
	if (ud.net && ud.lock != NULL) {
		lck_mtx_unlock(ud.lock);
	}
	ud.serial_dtr = false;
	ud.serial_line_out = false;
	ud.rndis_cmd_out = false;
	ud.rndis_filter = 0;
	ud.rndis_resp_len = 0;
	ud.rndis_q_head = ud.rndis_q_count = 0;
	ud.nint_busy = false;
	ud.nint_pending = 0;
	if (ud.state != EP0_SETUP) {
		ud_end_transfer(0);
		ud_end_transfer(1);
		ud_start_setup();
	}
	if (resets++ < 16) {
		printf("SWEET USB: bus reset%s\\n", was ? ": transfers ended, SETUP armed again" : "");
	}
}

static void
ud_event(uint32_t ev)
{
	if (ev & 1) {                   /* device event */
		uint32_t type = (ev >> 8) & 0xf;
		if (type == 1) {        /* USB reset */
			dwc_wr(DCFG, dwc_rd(DCFG) & ~(0x7fu << 3));
			ud_bus_reset();
''')
edit('''	unsigned status = (ev >> 12) & 0xf;

	if (ud.net && ep == ud.ep_nrx && type == 1) {
''', '''	unsigned status = (ev >> 12) & 0xf;

	if (type == 1 && ep < 16) {
		ud.active[ep] = false;
	}
	if (ud.rndis && ep == ud.ep_nint && type == 1) {
		ud.nint_busy = false;
		if (ud.nint_pending) {
			ud.nint_pending--;
			rndis_notify();
		}
		return;
	}
	if (ud.net && ep == ud.ep_nrx && type == 1) {
''')
edit('''	if (type == 3 && status == 2) { /* XferNotReady, control status phase */
''', '''	if (type == 3 && status == 1 && ud.state == EP0_DATA && ep != (ud.data_in ? 1u : 0u)) {
		/* XferNotReady for the other direction: the host gave the data stage up (Linux dwc3) */
		ud_end_transfer(0);
		ud_end_transfer(1);
		ud_stall();
		return;
	}
	if (type == 3 && status == 2) { /* XferNotReady, control status phase */
''')

with tempfile.TemporaryDirectory(prefix='make-0219-', dir='D:/ios-sweet/build') as scratch:
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
    (Path('D:/ios-sweet/build') / 'sweet_usb.new0219.c').write_bytes(new.encode())
print(NAME, len(text.splitlines()), 'lines, forward and reverse verified')

script = REPO / 'tools/check-sweet-patch-reversal.sh'
lines = script.read_bytes().decode().replace('\r\n', '\n').split('\n')
assert not any(NAME in line for line in lines)
at = [i for i, line in enumerate(lines) if '0218-sweet-usb-rndis-no-zlp-answers.patch' in line and 'apply --reverse' in line]
assert len(at) == 1
for i in at:
    if '--exclude=' + USB not in lines[i]:
        lines[i] = lines[i].replace(' --check ', ' --check --exclude=' + USB + ' ', 1)
last = max(i for i, line in enumerate(lines) if 'apply --reverse --check' in line or 'grep -F' in line)
lines.insert(last + 1, '# 0219: the USB device survives a bus reset; RNDIS notifications and answers queued.')
lines.insert(last + 2, 'git -C dxb/xnu apply --reverse --check "$GITHUB_WORKSPACE/xnu/patches/' + NAME + '"')
script.write_bytes('\n'.join(lines).encode())
print('reversal script updated')
