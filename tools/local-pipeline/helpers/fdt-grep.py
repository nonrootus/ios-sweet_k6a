"""Print device tree nodes/properties whose path or name matches a regex (no dtc needed).

  python -I fdt-grep.py FILE.dtb REGEX [REGEX...]
Strings are shown as text, everything else as 32-bit big-endian cells.
"""
import re
import struct
import sys


def main():
    data = open(sys.argv[1], 'rb').read()
    pats = [re.compile(p) for p in sys.argv[2:]]
    magic, total, off_struct, off_strings = struct.unpack('>IIII', data[:16])
    assert magic == 0xd00dfeed
    strings = data[off_strings:]
    pos = off_struct
    path = []
    while True:
        tok, = struct.unpack('>I', data[pos:pos + 4])
        pos += 4
        if tok == 1:
            end = data.index(b'\0', pos)
            path.append(data[pos:end].decode(errors='replace'))
            pos = (end + 4) & ~3
        elif tok == 2:
            path.pop()
        elif tok == 3:
            size, nameoff = struct.unpack('>II', data[pos:pos + 8])
            pos += 8
            value = data[pos:pos + size]
            pos = (pos + size + 3) & ~3
            name = strings[nameoff:strings.index(b'\0', nameoff)].decode()
            full = '/'.join(path) + ':' + name
            if any(p.search(full) for p in pats):
                if value and value[-1:] == b'\0' and all(32 <= c < 127 or c == 0 for c in value[:-1]) and value[0] != 0:
                    shown = repr(value[:-1].decode().replace('\0', ' | '))
                elif size % 4 == 0:
                    cells = struct.unpack('>%dI' % (size // 4), value)
                    shown = ' '.join('%#x' % c for c in cells[:24]) + (' ...' if len(cells) > 24 else '')
                else:
                    shown = value[:48].hex()
                print(full, '=', shown)
        elif tok == 4:
            continue
        elif tok == 9:
            break
        else:
            raise ValueError(tok)


main()
