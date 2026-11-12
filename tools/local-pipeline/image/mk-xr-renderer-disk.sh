#!/usr/bin/env bash
set -euo pipefail

base=/mnt/d/ios-sweet
source="$base/artifacts/sweet-renderer-42616583415/sweet/lib/libSweetEAGL.dylib"
sha=d8fb5f46649d3cbba7fc05a261ccec29746eed6f2f058a30f604d54f55ac5e51
out="$base/build/a618-0181-device"
mkdir -p "$out"
test ! -e "$out/renderer.hfs"
test "$(sha256sum "$source" | cut -d' ' -f1)" = "$sha"
work=$(mktemp -d "$out/mk-hfs.XXXXXXXX")
mkdir "$work/root"
loop=
cleanup() {
    if mountpoint -q "$work/root"; then umount "$work/root"; fi
    if [ -n "$loop" ]; then losetup -d "$loop"; fi
}
trap cleanup EXIT

truncate -s 4M "$work/renderer.hfs"
mkfs.hfsplus -s -v SweetRenderer "$work/renderer.hfs"
loop=$(losetup --find --show "$work/renderer.hfs")
mount -t hfsplus -o rw "$loop" "$work/root"
install -m 0644 -o 0 -g 0 "$source" "$work/root/libSweetEAGL.dylib"
umount "$work/root"
losetup -d "$loop"
loop=
fsck.hfsplus -fn "$work/renderer.hfs"

loop=$(losetup --read-only --find --show "$work/renderer.hfs")
mount -t hfsplus -o ro "$loop" "$work/root"
test "$(find "$work/root" -mindepth 1 -maxdepth 1 -printf '%f\n')" = libSweetEAGL.dylib
test "$(sha256sum "$work/root/libSweetEAGL.dylib" | cut -d' ' -f1)" = "$sha"
test "$(stat -c '%a:%u:%g' "$work/root/libSweetEAGL.dylib")" = 644:0:0
umount "$work/root"
losetup -d "$loop"
loop=
mv "$work/renderer.hfs" "$out/renderer.hfs"
sha256sum "$out/renderer.hfs"
