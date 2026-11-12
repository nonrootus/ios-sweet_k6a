set -e
img=/mnt/d/ios-sweet/work/jb-root/jb-root.img
loop=$(losetup -r -f --show "$img"); mnt=$(mktemp -d)
mount -t hfsplus -o ro "$loop" "$mnt"
for f in usr/libexec/sweetnet usr/libexec/ellekit/loader usr/lib/TweakInject.dylib bin/sh prep_bootstrap.sh usr/libexec/sweet-jbsetup usr/libexec/sweet-respring private/etc/apt/sources.list.d/sweet.sources sweet/lib/libSweetRendererLoader.dylib usr/libexec/real/backboardd usr/bin/dpkg; do
  if [ -e "$mnt/$f" ] || [ -L "$mnt/$f" ]; then printf "ok   %s %s\n" "$f" "$(stat -c '%a %U %s' "$mnt/$f" 2>/dev/null)"; else echo "MISSING $f"; fi
done
ls "$mnt/private/var/sweet-jb/debs" | tr '\n' ' '; echo
python3 - "$mnt" <<'PY'
import plistlib,sys
d=plistlib.load(open(sys.argv[1]+'/System/Library/xpc/launchd.plist','rb'))
print('jobs', sorted(k.split('/')[-1] for k in d['LaunchDaemons'] if 'sweet' in k or 'openssh' in k))
for sec in d.values():
    if isinstance(sec,dict):
        for j in sec.values():
            if isinstance(j,dict) and j.get('Label')=='com.apple.SpringBoard': print('SB env', j.get('EnvironmentVariables'))
PY
umount "$mnt"; losetup -d "$loop"; rmdir "$mnt"
