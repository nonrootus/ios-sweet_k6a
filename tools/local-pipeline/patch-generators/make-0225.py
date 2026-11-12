"""Patch 0225: the TX watchdog only logs; it no longer ends the transfer.

0224n (halt requests acknowledged only, as on 0219n) still lost the USB console and the network
right after the RNDIS start, like 0222n and 0223n. What the three had in common was 0222's TX
watchdog: a network TX transfer older than 2 s was ended (End Transfer, 100 us) and the next one
started at once. At the RNDIS start Windows resets the pipes and does not read the bulk IN pipe for
a few seconds, so the watchdog fired there; DWC3 wants the End Transfer completion event before
the next Start Transfer on that endpoint (Linux DWC3_EP_END_TRANSFER_PENDING), and without it the
whole controller stopped. The watchdog now logs a TX transfer pending for 2 s (once a stall) and
leaves it alone; the pending transfer completes when the host reads again, as on 0219n.
The fix that stays: a failed TX start no longer leaves the endpoint busy for ever.
Base: CI build tree 40478936434 plus 0180, 0211, 0216, 0218, 0219, 0222, 0223, 0224 for bsd/dev/sweet_usb.c.
"""





import re
import shutil
import subprocess
import tempfile
from pathlib import Path

REPO = Path('D:/ios-sweet/src/ios-sweet')
TREE = Path('D:/ios-sweet/build/xnu-buildtree-40478936434/xnu')
GIT = ['git', '-c', 'core.autocrlf=false', '-c', 'core.safecrlf=false']
NAME = '0225-sweet-usb-tx-watchdog-logs-only.patch'
USB = 'bsd/dev/sweet_usb.c'

with tempfile.TemporaryDirectory(prefix='make-0225-', dir='D:/ios-sweet/build') as scratch:
    work = Path(scratch)
    (work / USB).parent.mkdir(parents=True)
    shutil.copyfile(TREE / USB, work / USB)
    for earlier, only in (('0180-sweet-usb-console-and-b3a8-evidence.patch', True), ('0211-sweet-usb-console-and-rndis.patch', False), ('0216-sweet-usb-rndis-first.patch', False), ('0218-sweet-usb-rndis-no-zlp-answers.patch', False), ('0219-sweet-usb-reset-and-rndis-queue.patch', False), ('0222-sweet-usb-endpoint-halt-and-tx-watchdog.patch', False), ('0223-sweet-usb-halt-clear-stall-only.patch', False), ('0224-sweet-usb-halt-acknowledged-only.patch', False)):
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


edit('''/*
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
''', '''/*
 * A network TX transfer pending for over 2 s is only logged (once a stall). Ending it and
 * starting the next one right away (0222..0224) stopped the whole controller at the RNDIS start,
 * when Windows resets the pipes and does not read for a few seconds; the transfer completes by
 * itself once the host reads again.
 */
static void
ud_tx_watchdog(void)
{
	static uint64_t limit, reported;
	static unsigned logged;
	if (limit == 0) {
		nanoseconds_to_absolutetime(2 * NSEC_PER_SEC, &limit);
	}
	if (!ud.net || !ud.net_tx_busy || mach_absolute_time() - ud.tx_started < limit ||
	    reported == ud.tx_started) {
		return;
	}
	reported = ud.tx_started;
	if (logged++ < 16) {
		printf("SWEET USB: ue0 TX pending for 2 s (frame %llu)\\n", ud.tx_frames);
	}
}
''')

with tempfile.TemporaryDirectory(prefix='make-0225-', dir='D:/ios-sweet/build') as scratch:
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
    (Path('D:/ios-sweet/build') / 'sweet_usb.new0225.c').write_bytes(new.encode())
print(NAME, len(text.splitlines()), 'lines, forward and reverse verified')

script = REPO / 'tools/check-sweet-patch-reversal.sh'
lines = script.read_bytes().decode().replace('\r\n', '\n').split('\n')
assert not any(NAME in line for line in lines)
at = [i for i, line in enumerate(lines) if '0224-sweet-usb-halt-acknowledged-only.patch' in line and 'apply --reverse' in line]
assert len(at) == 1
for i in at:
    if '--exclude=' + USB not in lines[i]:
        lines[i] = lines[i].replace(' --check ', ' --check --exclude=' + USB + ' ', 1)
last = max(i for i, line in enumerate(lines) if 'apply --reverse --check' in line or 'grep -F' in line)
lines.insert(last + 1, '# 0225: the USB TX watchdog only logs.')
lines.insert(last + 2, 'git -C dxb/xnu apply --reverse --check "$GITHUB_WORKSPACE/xnu/patches/' + NAME + '"')
script.write_bytes('\n'.join(lines).encode())
print('reversal script updated')
