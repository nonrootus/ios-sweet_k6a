"""Repack an .ipa (zip) as a tar of its Payload/*.app with the zip's Unix modes and symlinks.

  python -I ipa2tar.py APP.ipa OUT.tar
Nothing is extracted to disk and nothing from the archive is run.
"""
import io
import stat
import sys
import tarfile
import time
import zipfile

src, dst = sys.argv[1], sys.argv[2]
apps = set()
with zipfile.ZipFile(src) as z, tarfile.open(dst, 'w', format=tarfile.PAX_FORMAT) as t:
    for info in z.infolist():
        name = info.filename
        if not name.startswith('Payload/') or name == 'Payload/':
            continue
        rel = name[len('Payload/'):]
        if '..' in rel.split('/') or rel.startswith('/'):
            raise SystemExit('unsafe path ' + name)
        apps.add(rel.split('/', 1)[0])
        mode = (info.external_attr >> 16) & 0xffff
        ti = tarfile.TarInfo(rel.rstrip('/'))
        ti.mtime = time.mktime(info.date_time + (0, 0, -1))
        ti.uid = ti.gid = 0
        if name.endswith('/'):
            ti.type = tarfile.DIRTYPE
            ti.mode = stat.S_IMODE(mode) or 0o755
            t.addfile(ti)
        elif stat.S_ISLNK(mode):
            ti.type = tarfile.SYMTYPE
            ti.linkname = z.read(info).decode()
            ti.mode = 0o755
            t.addfile(ti)
        else:
            data = z.read(info)
            ti.size = len(data)
            ti.mode = stat.S_IMODE(mode) or 0o644
            t.addfile(ti, io.BytesIO(data))
print('apps:', sorted(apps))
