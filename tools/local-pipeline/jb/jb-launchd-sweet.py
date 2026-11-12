#!/usr/bin/env python3
"""Add the jailbreak jobs to the sweet_k6a iOS root's launchd.plist (adapted from the Galaxy S9
fork's tools/jb-launchd.py, syncmodz/ios-s9, MIT).

  jb-launchd-sweet.py MOUNTED_ROOT

This iOS boots with launchd_unsecure_cache=1: launchd reads its jobs only from
/System/Library/xpc/launchd.plist, so the jobs a jailbreak would load go into that file:
  com.sweet.jbsetup   first boot: Procursus bootstrap prep, dpkg -i the bundled debs, uicache,
                      respring; exits at once on later boots
  com.sweet.sweetnet  publishes ue0 (USB network, sweetusb=4) to configd
  com.sweet.ellekit   ElleKit's loader (tweak injection through launchd)
  com.sweet.respring  one respring per boot once ElleKit's loader is done
  com.openssh.sshd    the openssh-server package's own job (ports 22 and 2222)
and SpringBoard gets DYLD_INSERT_LIBRARIES=/usr/lib/TweakInject.dylib (ElleKit's injector; the
kernel's AMFI dyld policy allows it, kernel 0213, and a missing library is not fatal). Idempotent.
"""
import os
import plistlib
import sys

JOBS = {
    '/System/Library/LaunchDaemons/com.sweet.jbsetup.plist': {
        'Label': 'com.sweet.jbsetup',
        'ProgramArguments': ['/bin/sh', '/usr/libexec/sweet-jbsetup'],
        'RunAtLoad': True,
        'UserName': 'root',
        'POSIXSpawnType': 'Interactive',
    },
    '/System/Library/LaunchDaemons/com.sweet.sweetnet.plist': {
        'Label': 'com.sweet.sweetnet',
        'ProgramArguments': ['/usr/libexec/sweetnet'],
        'RunAtLoad': True,
        'KeepAlive': True,
        'ThrottleInterval': 10,
        'UserName': 'root',
        'StandardOutPath': '/private/var/sweet-jb/sweetnet.log',
        'StandardErrorPath': '/private/var/sweet-jb/sweetnet.log',
    },
    '/System/Library/LaunchDaemons/com.sweet.ellekit.plist': {
        'Label': 'com.sweet.ellekit',
        'ProgramArguments': ['/usr/libexec/ellekit/loader'],
        'RunAtLoad': True,
        'LaunchOnlyOnce': True,
        'UserName': 'root',
        'StandardOutPath': '/private/var/sweet-jb/ellekit.log',
        'StandardErrorPath': '/private/var/sweet-jb/ellekit.log',
    },
    '/System/Library/LaunchDaemons/com.sweet.respring.plist': {
        'Label': 'com.sweet.respring',
        'ProgramArguments': ['/bin/sh', '/usr/libexec/sweet-respring'],
        'RunAtLoad': True,
        'LaunchOnlyOnce': True,
        'UserName': 'root',
        'StandardOutPath': '/private/var/sweet-jb/respring.log',
        'StandardErrorPath': '/private/var/sweet-jb/respring.log',
    },
    '/System/Library/LaunchDaemons/com.openssh.sshd.plist': {
        'Label': 'com.openssh.sshd',
        'Program': '/bin/sh',
        'ProgramArguments': ['/bin/sh', '/usr/libexec/sshd-keygen-wrapper', '-i'],
        'SessionCreate': True,
        'Sockets': {
            'SSHListener': {'SockServiceName': 'ssh'},
            'SSHListener2': {'SockServiceName': '2222'},
        },
        'inetdCompatibility': {'Wait': False},
        'StandardErrorPath': '/dev/null',
        'POSIXSpawnType': 'Interactive',
        'UserName': 'root',
    },
}
INJECT = '/usr/lib/TweakInject.dylib'


def main():
    path = os.path.join(sys.argv[1], 'System/Library/xpc/launchd.plist')
    st = os.stat(path)
    with open(path, 'rb') as f:
        plist = plistlib.load(f)
    daemons = plist['LaunchDaemons']
    for key, job in JOBS.items():
        daemons[key] = job
        print('job', job['Label'])
    found = 0
    for section in plist.values():
        if not isinstance(section, dict):
            continue
        for job in section.values():
            if isinstance(job, dict) and job.get('Label') == 'com.apple.SpringBoard':
                env = job.setdefault('EnvironmentVariables', {})
                env['DYLD_INSERT_LIBRARIES'] = INJECT
                found += 1
    if found != 1:
        sys.exit(f'SpringBoard job found {found} times, expected 1')
    print('SpringBoard: DYLD_INSERT_LIBRARIES =', INJECT)
    with open(path, 'wb') as f:
        plistlib.dump(plist, f, fmt=plistlib.FMT_BINARY)
    os.chown(path, st.st_uid, st.st_gid)
    os.chmod(path, st.st_mode & 0o7777)


if __name__ == '__main__':
    main()
