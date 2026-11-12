"""Patch 0205: AppleCLCD also recognises a full-screen BGRA layer that the GPU already put on the panel.

With the sRGB device tree (image 0204) the display surfaces became BGRA, as intended, but
AppleCLCD::present only told the renderer which surfaces are on the display for b3a8 layers.
So the renderer's direct panel path never started: every frame was read back with the CPU
(0204: 'copying out' median 20 ms, frame median 21.8 ms) and the kernel copied it to the panel.
Base: CI build tree 40478936434 plus 0171, 0177, 0180, 0183, 0194 for SweetFramebuffer.cpp.
"""
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

REPO = Path('D:/ios-sweet/src/ios-sweet')
TREE = Path('D:/ios-sweet/build/xnu-buildtree-40478936434/xnu')
GIT = ['git', '-c', 'core.autocrlf=false', '-c', 'core.safecrlf=false']
NAME = '0205-sweet-framebuffer-bgra-direct-frame.patch'
FB = 'iokit/Kernel/arm/SweetFramebuffer.cpp'
CHAIN = ['0171-sweet-a618-iosurface-span.patch', '0177-sweet-b3a8-framebuffer.patch',
         '0180-sweet-usb-console-and-b3a8-evidence.patch', '0183-sweet-framebuffer-direct-frame.patch',
         '0194-sweet-amfi-iokit-service.patch']

with tempfile.TemporaryDirectory(prefix='make-0205-', dir='D:/ios-sweet/build') as scratch:
    work = Path(scratch)
    (work / FB).parent.mkdir(parents=True)
    shutil.copyfile(TREE / FB, work / FB)
    for name in CHAIN:
        patch = work / name
        patch.write_bytes(subprocess.check_output(GIT + ['show', 'HEAD:xnu/patches/' + name], cwd=REPO))
        subprocess.run(GIT + ['apply', '--include=' + FB, name], cwd=work, check=True)
    base = (work / FB).read_bytes().decode()

before = r'''		uint64_t last = (uint64_t)s->offset + (uint64_t)(sy + h - 1) * s->bytesPerRow +
'''
after = r'''		/* The sRGB device tree makes the display surfaces BGRA: same rule as for b3a8 above. */
		if (s->pixelFormat == SWEET_FB_FORMAT_BGRA && mask == 1 && layer == 0 && dx == 0 && dy == 0 &&
		    sx == 22 && sy == 18 && w == 1080 && h == 2400 && fWidth == 1080 && fHeight == 2400 &&
		    fRowBytes == 4320) {
			sweet_a618_note_display(id);
			if (sweet_a618_direct_take(id)) {
				static unsigned bgra_skipped;
				if (bgra_skipped++ < 8) {
					IOLog("SWEET FB: BGRA frame already on the panel swap=%u surface=%u\n", get32(rec, 0x50), id);
				}
				s->release();
				continue;
			}
		}
		uint64_t last = (uint64_t)s->offset + (uint64_t)(sy + h - 1) * s->bytesPerRow +
'''
assert base.count(before) == 1, base.count(before)
new = base.replace(before, after)

with tempfile.TemporaryDirectory(prefix='make-0205-', dir='D:/ios-sweet/build') as scratch:
    work = Path(scratch)
    for side, data in (('a', base), ('b', new)):
        path = work / side / FB
        path.parent.mkdir(parents=True)
        path.write_bytes(data.encode())
    done = subprocess.run(GIT + ['diff', '--no-index', '--no-color', '--no-prefix', '-U3', 'a', 'b'], cwd=work, capture_output=True)
    assert done.returncode == 1, done.stderr
    text = re.sub(r'^diff --git .*\n(index .*\n)?', '', done.stdout.decode(), flags=re.M)
    assert text.startswith('--- a/') and '\r' not in text
    output = REPO / 'xnu/patches' / NAME
    output.write_bytes(text.encode())
    check = work / 'check' / FB
    check.parent.mkdir(parents=True)
    check.write_bytes(base.encode())
    subprocess.run(GIT + ['apply', str(output)], cwd=work / 'check', check=True)
    assert check.read_bytes() == new.encode()
    # Which earlier patches can no longer be reversed on this file: the CI script must exclude it there.
    blocked = []
    for name in CHAIN:
        done = subprocess.run(GIT + ['apply', '--reverse', '--check', '--include=' + FB, str(REPO / 'xnu/patches' / name)],
                              cwd=work / 'check', capture_output=True)
        if done.returncode != 0:
            blocked.append(name)
    subprocess.run(GIT + ['apply', '--reverse', str(output)], cwd=work / 'check', check=True)
print(NAME, len(text.splitlines()), 'lines, forward and reverse verified; earlier patches now blocked:', blocked)

script = REPO / 'tools/check-sweet-patch-reversal.sh'
lines = script.read_bytes().decode().replace('\r\n', '\n').split('\n')
assert not any(NAME in line for line in lines)
for name in blocked:
    at = [i for i, line in enumerate(lines) if name in line and 'apply --reverse' in line]
    assert len(at) <= 1, (name, at)
    if at and '--exclude=' + FB not in lines[at[0]]:
        lines[at[0]] = lines[at[0]].replace(' --check ', ' --check --exclude=' + FB + ' ', 1)
last = max(i for i, line in enumerate(lines) if 'apply --reverse --check' in line or 'grep -F' in line)
lines.insert(last + 1, '# 0205: a full-screen BGRA layer the GPU already put on the panel is not copied again.')
lines.insert(last + 2, 'git -C dxb/xnu apply --reverse --check "$GITHUB_WORKSPACE/xnu/patches/' + NAME + '"')
script.write_bytes('\n'.join(lines).encode())
print('reversal script updated')
