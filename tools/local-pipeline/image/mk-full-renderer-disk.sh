#!/usr/bin/env bash
set -euo pipefail

source="$1"
out="$2"
eagl_hash="$3"
mesa_hash="$4"
test ! -e "$out/renderer.hfs"
printf '%s  %s\n' "$eagl_hash" "$source/libSweetEAGL.dylib" "$mesa_hash" "$source/libOSMesa.8.dylib" | sha256sum -c -

work=$(mktemp -d "$out/mk-full-hfs.XXXXXXXX")
mkdir "$work/root"
loop=
cleanup() {
    if mountpoint -q "$work/root"; then umount "$work/root"; fi
    if [ -n "$loop" ]; then losetup -d "$loop"; fi
}
trap cleanup EXIT

truncate -s 20M "$work/renderer.hfs"
mkfs.hfsplus -s -v SweetRenderer "$work/renderer.hfs"
loop=$(losetup --find --show "$work/renderer.hfs")
mount -t hfsplus -o rw "$loop" "$work/root"
for library in libSweetEAGL.dylib libOSMesa.8.dylib; do
    install -m 0644 -o 0 -g 0 "$source/$library" "$work/root/$library"
done
umount "$work/root"
losetup -d "$loop"
loop=
fsck.hfsplus -fn "$work/renderer.hfs"

loop=$(losetup --read-only --find --show "$work/renderer.hfs")
mount -t hfsplus -o ro "$loop" "$work/root"
test "$(find "$work/root" -mindepth 1 -maxdepth 1 -printf '%f\n' | sort)" = "$(printf '%s\n' libOSMesa.8.dylib libSweetEAGL.dylib)"
printf '%s  %s\n' "$eagl_hash" "$work/root/libSweetEAGL.dylib" "$mesa_hash" "$work/root/libOSMesa.8.dylib" | sha256sum -c -
for library in libSweetEAGL.dylib libOSMesa.8.dylib; do
    test "$(stat -c '%a:%u:%g' "$work/root/$library")" = 644:0:0
done
umount "$work/root"
losetup -d "$loop"
loop=
mv "$work/renderer.hfs" "$out/renderer.hfs"
rmdir "$work/root" "$work"
sha256sum "$out/renderer.hfs"
