#!/bin/bash
# Jailbroken iOS root for sweet_k6a, from the root on the phone now (gpu0177), after the Galaxy S9
# fork's tools/prep-ios6.sh (syncmodz/ios-s9, MIT): Procursus rootful bootstrap 1800, ElleKit, the
# bundled debs installed by dpkg at first boot, sweetnet (ue0 to configd), launchd jobs, Sileo repos.
#   (WSL, root) bash mk-jb-root.sh SWEETNET_BINARY
# Output: /mnt/d/ios-sweet/work/jb-root/ios16-root-sweet-k6a-20H392-jb1.simg (+ .sha256). Nothing is
# flashed here.
set -euo pipefail
sweetnet=$1
src=/mnt/d/ios-sweet/artifacts/gpu0177/ios16-root-sweet-k6a-20H392-gpu0177.simg
jb=/mnt/d/ios-sweet/jb/downloads
work=/mnt/d/ios-sweet/work/jb-root
raw=$work/jb-root.img
out=$work/ios16-root-sweet-k6a-20H392-jb1.simg
mkdir -p "$work"
(cd "$jb" && sha256sum -c --quiet SHA256SUMS)
file "$sweetnet" | grep -q "Mach-O 64-bit arm64 executable"

echo "== expand $src"
[ -f "$raw" ] || simg2img "$src" "$raw"
loop=$(losetup -f --show "$raw")
mnt=$(mktemp -d)
cleanup() {
	mountpoint -q "$mnt" && umount "$mnt"
	losetup -d "$loop" 2>/dev/null || true
	rmdir "$mnt" 2>/dev/null || true
}
trap cleanup EXIT
fsck.hfsplus -fy "$loop" >/dev/null || echo "fsck: exit $? (repaired or warnings)"
mount -t hfsplus -o rw,force "$loop" "$mnt"
test -f "$mnt/System/Library/xpc/launchd.plist"
test -f "$mnt/sweet/lib/libSweetRendererLoader.dylib"

echo "== Procursus rootful bootstrap and ElleKit"
zstd -dc "$jb/bootstrap-rootful-1800.tar.zst" | tar -xp --numeric-owner --keep-directory-symlink -C "$mnt"
ar p "$jb/debs/0-ellekit.deb" data.tar.xz | tar -xJp --numeric-owner --keep-directory-symlink -C "$mnt"
test -x "$mnt/usr/libexec/ellekit/loader"

install -d -m 755 "$mnt/private/var/sweet-jb/debs"
install -m 644 "$jb"/debs/*.deb "$mnt/private/var/sweet-jb/debs/"
install -m 755 "$sweetnet" "$mnt/usr/libexec/sweetnet"

cat > "$mnt/usr/libexec/sweet-jbsetup" <<'EOF'
#!/bin/sh
# sweet_k6a iOS: first-boot jailbreak setup (launchd job com.sweet.jbsetup, root).
exec >>/private/var/sweet-jb/jbsetup.log 2>&1
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
[ -f /private/var/sweet-jb/jbsetup.done ] && exit 0
echo "=== $(date) jbsetup start"
sleep 60        # let SpringBoard, lsd and installd come up for uicache
if [ -f /prep_bootstrap.sh ]; then
	NO_PASSWORD_PROMPT=1 /bin/sh /prep_bootstrap.sh
	printf 'alpine\n' | /usr/sbin/pw usermod 501 -h 0
	printf 'alpine\n' | /usr/sbin/pw usermod 0 -h 0
fi
dpkg -i /private/var/sweet-jb/debs/*.deb || dpkg -i --force-depends /private/var/sweet-jb/debs/*.deb
dpkg --configure -a
uicache -a
touch /private/var/sweet-jb/jbsetup.done
echo "=== $(date) jbsetup done, respring"
sbreload || killall -9 SpringBoard
EOF
chmod 755 "$mnt/usr/libexec/sweet-jbsetup"

cat > "$mnt/usr/libexec/sweet-respring" <<'EOF'
#!/bin/sh
# sweet_k6a iOS: one respring per boot (launchd job com.sweet.respring). SpringBoard starts before
# ElleKit's loader has set up injection, so the first SpringBoard of a boot has no tweaks.
running() { ps -axo comm | grep -q "$1"; }
i=0
while [ $i -lt 900 ]; do
	if running '/SpringBoard$' && ! running 'ellekit/loader$'; then
		break
	fi
	sleep 2
	i=$((i + 2))
done
sleep 20
[ -f /private/var/sweet-jb/jbsetup.done ] || exit 0
echo "$(date) respring after ${i}s"
killall -9 SpringBoard
EOF
chmod 755 "$mnt/usr/libexec/sweet-respring"

install -d -m 755 "$mnt/private/etc/apt/sources.list.d"
install -m 644 /mnt/d/ios-sweet/jb/repos.sources "$mnt/private/etc/apt/sources.list.d/sweet.sources"

python3 -I /mnt/d/ios-sweet/build/jb-launchd-sweet.py "$mnt"
# No Bluetooth hardware: on the S9 mediaserverd's BTAudioHALPlugin looked bluetoothd up over XPC
# forever (launchd ~70 % + mediaserverd ~50 % of a core at idle). Moved aside, not deleted.
if [ -d "$mnt/System/Library/Audio/Plug-Ins/HAL/BTAudioHALPlugin.driver" ]; then
	mkdir -p "$mnt/Library/Audio/Plug-Ins/HAL.disabled"
	mv "$mnt/System/Library/Audio/Plug-Ins/HAL/BTAudioHALPlugin.driver" "$mnt/Library/Audio/Plug-Ins/HAL.disabled/"
fi
sync
umount "$mnt"
fsck.hfsplus -fy "$loop" >/dev/null || echo "fsck: exit $? (repaired or warnings)"
fsck.hfsplus -fn "$loop" && echo "fsck clean"
losetup -d "$loop"
trap - EXIT
rmdir "$mnt"
echo "== sparse image"
rm -f "$out"
img2simg "$raw" "$out"
sha256sum "$out" > "$out.sha256"
ls -la "$out"
cat "$out.sha256"
