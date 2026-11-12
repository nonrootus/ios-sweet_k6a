"""Writes make-0219.py from make-0218.py (same base handling, new edits)."""
from pathlib import Path

s = Path('D:/ios-sweet/build/make-0218.py').read_text(encoding='utf-8')
doc_end = s.index('"""', 3) + 3
body = s[doc_end:]
head_end = body.index("edit('''")
tail_start = body.rindex("with tempfile.TemporaryDirectory(prefix='make-0218-'")
pre = body[:head_end]
tail = body[tail_start:]
doc = Path('D:/ios-sweet/build/make-0219.doc.txt').read_text(encoding='utf-8')
edits = Path('D:/ios-sweet/build/make-0219.edits.txt').read_text(encoding='utf-8')
pre = pre.replace("NAME = '0218-sweet-usb-rndis-no-zlp-answers.patch'", "NAME = '0219-sweet-usb-reset-and-rndis-queue.patch'")
pre = pre.replace("('0216-sweet-usb-rndis-first.patch', False))",
                  "('0216-sweet-usb-rndis-first.patch', False), ('0218-sweet-usb-rndis-no-zlp-answers.patch', False))")
pre = pre.replace("make-0218-", "make-0219-")
assert "0218-sweet-usb-rndis-no-zlp-answers.patch', False))" in pre
tail = tail.replace("make-0218-", "make-0219-").replace("sweet_usb.new0218.c", "sweet_usb.new0219.c")
old = "'0216-sweet-usb-rndis-first.patch' in line and 'apply --reverse' in line]"
assert old in tail
tail = tail.replace(old, "'0218-sweet-usb-rndis-no-zlp-answers.patch' in line and 'apply --reverse' in line]")
tail = tail.replace("# 0218: RNDIS answers never a whole number of EP0 packets (no ZLP needed).",
                    "# 0219: the USB device survives a bus reset; RNDIS notifications and answers queued.")
Path('D:/ios-sweet/build/make-0219.py').write_text(doc + pre + edits + '\n' + tail, encoding='utf-8')
print('make-0219.py written')
