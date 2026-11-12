"""Writes make-0223.py from make-0223.py (same base handling, 0222 added to the chain, new edits)."""
from pathlib import Path

B = Path('D:/ios-sweet/build')
s = (B / 'make-0224.py').read_text(encoding='utf-8')
doc_end = s.index('"""', 3) + 3
body = s[doc_end:]
head_end = body.index("edit('''")
tail_start = body.rindex("with tempfile.TemporaryDirectory(prefix='make-0224-'")
pre = body[:head_end]
tail = body[tail_start:]
doc = (B / 'make-0225.doc.txt').read_text(encoding='utf-8')
edits = (B / 'make-0225.edits.txt').read_text(encoding='utf-8')
old = "NAME = '0224-sweet-usb-halt-acknowledged-only.patch'"
assert old in pre
pre = pre.replace(old, "NAME = '0225-sweet-usb-tx-watchdog-logs-only.patch'")
old = "('0223-sweet-usb-halt-clear-stall-only.patch', False))"
assert old in pre
pre = pre.replace(old, "('0223-sweet-usb-halt-clear-stall-only.patch', False), ('0224-sweet-usb-halt-acknowledged-only.patch', False))")
pre = pre.replace("make-0224-", "make-0225-")
tail = tail.replace("make-0224-", "make-0225-").replace("sweet_usb.new0224.c", "sweet_usb.new0225.c")
old = "'0223-sweet-usb-halt-clear-stall-only.patch' in line and 'apply --reverse' in line]"
assert old in tail
tail = tail.replace(old, "'0224-sweet-usb-halt-acknowledged-only.patch' in line and 'apply --reverse' in line]")
old = "# 0224: ENDPOINT_HALT requests acknowledged only (as up to 0219)."
assert old in tail
tail = tail.replace(old, "# 0225: the USB TX watchdog only logs.")
(B / 'make-0225.py').write_text(doc + pre + edits + '\n' + tail, encoding='utf-8')
print('make-0225.py written')
