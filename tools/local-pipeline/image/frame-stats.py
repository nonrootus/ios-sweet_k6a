"""Frame-time statistics of a USB console log: frame-stats.py LOG [LOG...]"""
import re
import sys
rx = re.compile(rb'redwood-gl: frame (\d+): (\d+) GL calls, (\d+) draws, (\d+) triangles, (\d+) clears; (\d+) textures refilled from IOSurfaces \((\d+) KB\); (\d+) picture\w* copied out, (\d+) drawn in place; (\d+) us \((\d+) handing on, (\d+) waiting, (\d+) copying out\), (\d+) before')
for path in sys.argv[1:]:
    data = open(path, 'rb').read()
    rows = [list(map(int, m.groups())) for m in rx.finditer(data)]
    print(path.split('/')[-1], len(rows), 'samples, last frame', rows[-1][0] if rows else None)
    if not rows:
        continue
    for name, i in (('draws', 2), ('frame_us', 9), ('handing_us', 10), ('copy_us', 12)):
        v = sorted(r[i] for r in rows)
        print(' ', name, 'median', v[len(v) // 2], 'p90', v[int(len(v) * .9)], 'max', v[-1])
    busy = [r for r in rows if r[2] >= 60]
    if busy:
        v = sorted(r[9] for r in busy)
        print('  frames with 60+ draws:', len(busy), 'median', v[len(v) // 2], 'p90', v[int(len(v) * .9)])
    idle = [r for r in rows if r[2] < 40]
    if idle:
        v = sorted(r[9] for r in idle)
        print('  frames under 40 draws:', len(idle), 'median', v[len(v) // 2], 'p90', v[int(len(v) * .9)])
    over = sum(1 for r in rows if r[9] > 16667)
    print('  over 16.7 ms:', over, 'of', len(rows), 'submit-wait lines:', len(re.findall(rb'GPU wait mean', data)))
    for m in re.findall(rb'SWEET CA: GPU wait mean[^\n|]{0,70}', data)[-4:]:
        print('  ', m.decode('latin-1'))
    f = re.findall(rb'SWEET DIRECT: fields (\d+) us: submit (\d+) in (\d+) us', data)
    if f:
        v = sorted(int(c) / int(b) for a, b, c in f if int(b))
        print('  field submit us: median', v[len(v) // 2], 'min', v[0], 'max', v[-1], 'n', len(v))
    print('  crashes SB', len(re.findall(rb'CRASH SpringBoard\[', data)), 'backboardd', len(re.findall(rb'CRASH backboardd\[', data)),
          'disabled', len(re.findall(rb'submit disabled', data)), 'panic', len(re.findall(rb'panic\(cpu', data)),
          'touches', len(re.findall(rb'SWEET HID: touch', data)))
    p = re.findall(rb'redwood-gl: profile: ([^\n|]{0,240})', data)
    if p:
        print('  ', p[-1].decode('latin-1'))
