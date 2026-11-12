#!/usr/bin/env python3
"""Pack phone GPU firmware into an offline-verifiable RAM-disk payload.

  pack-gpu-fw.py pack FIRMWARE_DIR NEW_OUTPUT
  pack-gpu-fw.py verify BUNDLE FIRMWARE_DIR

This format is not yet consumed by XNU and does not authenticate signatures.
Do not commit device firmware or bundles.
"""
import hashlib
import os
import struct
import sys
from pathlib import Path

NAMES = ('a618_gmu.bin', 'a630_sqe.fw', 'a615_zap.mdt', 'a615_zap.b02')
MAGIC = b'SWEETGPU'
PAGE = 4096
HEADER = struct.Struct('<8sIIQ')
ENTRY = struct.Struct('<32sQQ32s')
MAX_FILE = 1024 * 1024


def align(n):
    return (n + PAGE - 1) & ~(PAGE - 1)


def pack(folder, output):
    files = []
    for name in NAMES:
        data = (folder / name).read_bytes()
        if not 0 < len(data) <= MAX_FILE:
            raise ValueError(f'invalid size for {name}')
        files.append((name, data))
    records = []; pos = PAGE
    for name, data in files:
        records.append((name.encode(), pos, len(data), hashlib.sha256(data).digest()))
        pos = align(pos + len(data))
    if HEADER.size + len(records) * ENTRY.size > PAGE:
        raise ValueError('header too large')
    # Exclusive create ensures that a failed or repeated run cannot overwrite an existing file.
    with output.open('xb') as f:
        f.write(HEADER.pack(MAGIC, 1, len(records), pos))
        for rec in records: f.write(ENTRY.pack(*rec))
        f.write(bytes(PAGE - f.tell()))
        for (_, data), (_, off, _, _) in zip(files, records):
            if f.tell() != off: raise ValueError('internal offset error')
            f.write(data); f.write(bytes(align(f.tell()) - f.tell()))
        f.flush(); os.fsync(f.fileno())
    print(f'packed {len(files)} files, {pos} bytes')


def verify(bundle, folder):
    with bundle.open('rb') as f:
        raw = f.read(HEADER.size)
        if len(raw) != HEADER.size: raise ValueError('short header')
        magic, version, count, total = HEADER.unpack(raw)
        if magic != MAGIC or version != 1 or count != len(NAMES) or total != bundle.stat().st_size:
            raise ValueError('invalid header')
        records = []
        for expected in NAMES:
            raw = f.read(ENTRY.size)
            if len(raw) != ENTRY.size: raise ValueError('short entry')
            name, off, size, digest = ENTRY.unpack(raw)
            if name.rstrip(b'\0') != expected.encode() or not 0 < size <= MAX_FILE:
                raise ValueError('invalid name or size')
            records.append((expected, off, size, digest))
        end = PAGE
        for name, off, size, digest in records:
            if off != end or off + size > total: raise ValueError('invalid extent')
            f.seek(off); data = f.read(size)
            if len(data) != size or hashlib.sha256(data).digest() != digest or data != (folder / name).read_bytes():
                raise ValueError(f'content mismatch: {name}')
            end = align(off + size)
        if end != total: raise ValueError('unexpected trailing extent')
    print(f'verified {count} files, {total} bytes; SHA-256 checksums match source files')


def main():
    if len(sys.argv) != 4: raise SystemExit(__doc__)
    try:
        if sys.argv[1] == 'pack': pack(Path(sys.argv[2]), Path(sys.argv[3]))
        elif sys.argv[1] == 'verify': verify(Path(sys.argv[2]), Path(sys.argv[3]))
        else: raise ValueError('expected pack or verify')
    except (OSError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc

if __name__ == '__main__': main()
