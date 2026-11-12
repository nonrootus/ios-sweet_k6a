"""Writes make-0222.py from make-0219.py (same base handling, 0219 added to the chain, new edits)."""
from pathlib import Path

B = Path('D:/ios-sweet/build')
s = (B / 'make-0219.py').read_text(encoding='utf-8')
doc_end = s.index('"""', 3) + 3
body = s[doc_end:]
head_end = body.index("edit('''")
tail_start = body.rindex("with tempfile.TemporaryDirectory(prefix='make-0219-'")
pre = body[:head_end]
tail = body[tail_start:]
doc = (B / 'make-0222.doc.txt').read_text(encoding='utf-8')
edits = (B / 'make-0222.edits.txt').read_text(encoding='utf-8')
old = "NAME = '0219-sweet-usb-reset-and-rndis-queue.patch'"
assert old in pre
pre = pre.replace(old, "NAME = '0222-sweet-usb-endpoint-halt-and-tx-watchdog.patch'")
old = "('0218-sweet-usb-rndis-no-zlp-answers.patch', False))"
assert old in pre
pre = pre.replace(old, "('0218-sweet-usb-rndis-no-zlp-answers.patch', False), ('0219-sweet-usb-reset-and-rndis-queue.patch', False))")
pre = pre.replace("make-0219-", "make-0222-")
tail = tail.replace("make-0219-", "make-0222-").replace("sweet_usb.new0219.c", "sweet_usb.new0222.c")
old = "'0218-sweet-usb-rndis-no-zlp-answers.patch' in line and 'apply --reverse' in line]"
assert old in tail
tail = tail.replace(old, "'0219-sweet-usb-reset-and-rndis-queue.patch' in line and 'apply --reverse' in line]")
old = "# 0219: the USB device survives a bus reset; RNDIS notifications and answers queued."
assert old in tail
tail = tail.replace(old, "# 0222: USB network keeps going: endpoint halt requests, failed TX starts, TX watchdog.")
(B / 'make-0222.py').write_text(doc + pre + edits + '\n' + tail, encoding='utf-8')
print('make-0222.py written')
