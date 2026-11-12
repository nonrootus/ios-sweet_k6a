#!/usr/bin/env python3
"""Report staged system apps absent from /Applications on a mounted iOS root.

Read-only by default. --promote-offline moves bundles on a loop-mounted build
image into /Applications, preserving their metadata without copying contents.
Back up the image first. LaunchServices registration still requires a boot test.
"""
import argparse
import ctypes
import os
from pathlib import Path
import plistlib


def entries(root):
    source = root / 'private/var/staged_system_apps'
    target = root / 'Applications'
    if not source.is_dir() or source.is_symlink() or not target.is_dir() or target.is_symlink():
        raise ValueError('expected real staged_system_apps and Applications directories')
    for directory in (source, target):
        if not directory.resolve().is_relative_to(root.resolve()):
            raise ValueError('directory escapes mounted root')
    for app in sorted(source.iterdir()):
        if app.suffix != '.app' or app.is_symlink() or not app.is_dir():
            continue
        info_path = app / 'Info.plist'
        if info_path.is_symlink() or not info_path.is_file():
            raise ValueError(f'missing regular Info.plist in {app.name}')
        with info_path.open('rb') as f:
            info = plistlib.load(f)
        ident = info.get('CFBundleIdentifier')
        if not isinstance(ident, str) or not ident:
            raise ValueError(f'missing bundle identifier in {app.name}')
        dest = target / app.name
        yield app, dest, ident, os.path.lexists(dest)


def promote(plan):
    """Same-volume rename preserves resource forks, attributes and hard links."""
    libc = ctypes.CDLL(None, use_errno=True)
    rename = libc.renameat2
    rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int
    for src, dst, ident, exists in plan:
        if exists:
            continue
        if rename(-100, os.fsencode(src), -100, os.fsencode(dst), 1):
            error = ctypes.get_errno()
            raise OSError(error, os.strerror(error), str(dst))
        print('promoted', src.name, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mountpoint', type=Path)
    parser.add_argument('--promote-offline', action='store_true',
                        help='move bundles on a backed-up loop-mounted build image; never a phone device')
    args = parser.parse_args()
    root = args.mountpoint.resolve(strict=True)
    if root == Path('/') or not os.path.ismount(root):
        raise SystemExit('target must be an offline mounted image, not / or an ordinary directory')
    plan = list(entries(root))
    for src, dst, ident, exists in plan:
        print(('skip existing' if exists else 'staged only') + f' {src.name} ({ident})', flush=True)
    print(f'{sum(not x[3] for x in plan)} staged only, {sum(x[3] for x in plan)} already exist', flush=True)
    if args.promote_offline:
        dev = root.stat().st_dev
        backing = Path(f'/sys/dev/block/{os.major(dev)}:{os.minor(dev)}/loop/backing_file')
        if os.geteuid() != 0 or not backing.is_file():
            raise SystemExit('promotion requires root and an offline loop-mounted build image')
        if any(src.stat().st_dev != dev or dst.parent.stat().st_dev != dev for src, dst, _, _ in plan):
            raise SystemExit('all bundles must be on the image filesystem')
        promote(plan)
if __name__ == '__main__':
    main()
