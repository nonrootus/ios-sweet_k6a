"""Build the sweet_k6a libkrw0 plugin stub: a .deb with no files that Provides libkrw0-plugin.

libkrw0 (from the palera1n Procursus rootful bootstrap) Depends on the virtual package
libkrw0-plugin, which each jailbreak's own package provides on real iPhones. This port has none, so
apt refuses every install ("Unmet dependencies"). The stub satisfies the dependency only: nothing
gets kernel read/write through libkrw on this phone.
  python -I mk-krw-stub-deb.py OUT.deb
"""
import io
import sys
import tarfile
import time

CONTROL = b"""Package: sweet-libkrw0-plugin-stub
Name: libkrw0 plugin stub (sweet_k6a)
Version: 1.0
Architecture: iphoneos-arm
Provides: libkrw0-plugin
Maintainer: ios-sweet
Section: System
Priority: optional
Description: Satisfies libkrw0's plugin dependency on the sweet_k6a iOS port.
 It installs no files and gives no kernel read/write access.
"""


def targz(members):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode='w:gz', format=tarfile.GNU_FORMAT) as t:
        for name, data in members:
            ti = tarfile.TarInfo(name)
            ti.mtime = int(time.time())
            ti.uid = ti.gid = 0
            ti.uname = ti.gname = 'root'
            if data is None:
                ti.type = tarfile.DIRTYPE
                ti.mode = 0o755
                t.addfile(ti)
            else:
                ti.mode = 0o644
                ti.size = len(data)
                t.addfile(ti, io.BytesIO(data))
    return buf.getvalue()


def ar_member(name, data):
    head = b'%-16s%-12d%-6d%-6d%-8s%-10d`\n' % (name.encode(), int(time.time()), 0, 0, b'100644', len(data))
    assert len(head) == 60
    return head + data + (b'\n' if len(data) % 2 else b'')


out = sys.argv[1]
deb = b'!<arch>\n'
deb += ar_member('debian-binary', b'2.0\n')
deb += ar_member('control.tar.gz', targz([('./', None), ('./control', CONTROL)]))
deb += ar_member('data.tar.gz', targz([('./', None)]))
open(out, 'wb').write(deb)
print(out, len(deb), 'bytes')
