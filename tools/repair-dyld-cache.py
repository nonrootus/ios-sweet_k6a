#!/usr/bin/env python3
"""Restore selected dyld cache files in a mounted HFS root from SystemOS.

Usage: repair-dyld-cache.py SYSTEMOS_ROOT MOUNTED_ROOT
Writes through the existing hard link, preserving the inode and metadata.
"""
import hashlib
import os
import shutil
import sys
from pathlib import Path

if len(sys.argv) != 3:
    sys.exit(__doc__)
source = Path(sys.argv[1]) / 'System/Library/Caches/com.apple.dyld'
root = Path(sys.argv[2])
cryptex = root / 'private/preboot/Cryptexes/OS/System/Library/Caches/com.apple.dyld'
alias = root / 'System/Library/Caches/com.apple.dyld'
names = ('dyld_shared_cache_arm64.35', 'dyld_shared_cache_arm64.41.dylddata')

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

for name in names:
    src, dst, linked = source / name, cryptex / name, alias / name
    if not src.is_file() or not dst.is_file() or not linked.is_file():
        sys.exit(f'Missing required file: {name}')
    if not os.path.samefile(dst, linked):
        sys.exit(f'Expected hard links differ: {name}')
    expected = digest(src)
    print(f'{name}: source SHA256 {expected}', flush=True)
    with src.open('rb') as inp, dst.open('wb') as out:
        shutil.copyfileobj(inp, out, 1024 * 1024)
        out.flush()
        os.fsync(out.fileno())
    if digest(dst) != expected or digest(linked) != expected:
        sys.exit(f'Verification failed: {name}')
    print(f'{name}: restored and verified', flush=True)
