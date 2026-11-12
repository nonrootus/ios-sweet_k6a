"""Writes make-0223.py from make-0222.py (same base handling, 0222 added to the chain, new edits)."""
from pathlib import Path

B = Path('D:/ios-sweet/build')
s = (B / 'make-0222.py').read_text(encoding='utf-8')
doc_end = s.index('"""', 3) + 3
body = s[doc_end:]
head_end = body.index("edit('''")
tail_start = body.rindex("with tempfile.TemporaryDirectory(prefix='make-0222-'")
pre = body[:head_end]
tail = body[tail_start:]
doc = (B / 'make-0223.doc.txt').read_text(encoding='utf-8')
edits = (B / 'make-0223.edits.txt').read_text(encoding='utf-8')
old = "NAME = '0222-sweet-usb-endpoint-halt-and-tx-watchdog.patch'"
assert old in pre
pre = pre.replace(old, "NAME = '0223-sweet-usb-halt-clear-stall-only.patch'")
old = "('0219-sweet-usb-reset-and-rndis-queue.patch', False))"
assert old in pre
pre = pre.replace(old, "('0219-sweet-usb-reset-and-rndis-queue.patch', False), ('0222-sweet-usb-endpoint-halt-and-tx-watchdog.patch', False))")
pre = pre.replace("make-0222-", "make-0223-")
tail = tail.replace("make-0222-", "make-0223-").replace("sweet_usb.new0222.c", "sweet_usb.new0223.c")
old = "'0219-sweet-usb-reset-and-rndis-queue.patch' in line and 'apply --reverse' in line]"
assert old in tail
tail = tail.replace(old, "'0222-sweet-usb-endpoint-halt-and-tx-watchdog.patch' in line and 'apply --reverse' in line]")
old = "# 0222: USB network keeps going: endpoint halt requests, failed TX starts, TX watchdog."
assert old in tail
tail = tail.replace(old, "# 0223: ENDPOINT_HALT clear is Clear Stall only (Linux 4.14 dwc3).")
(B / 'make-0223.py').write_text(doc + pre + edits + '\n' + tail, encoding='utf-8')
print('make-0223.py written')
