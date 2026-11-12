"""Packages a kernel and renderer built from one commit into a temporary boot image.

Usage: prepare-kernel-renderer.py VERSION HEAD KERNEL_RUN RENDERER_RUN COMPACT_RUN COMPACT_ARTIFACT_ID [KERNEL_VERSION KERNEL_HEAD]
Every input is verified by the templates it reuses; nothing here writes to the phone.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import sys

version, head, kernel_run, renderer_run, compact_run, artifact_id = sys.argv[1:7]
kernel_version, kernel_head = sys.argv[7:9] if len(sys.argv) > 7 else (version, head)
assert re.fullmatch('0[0-9]{3}[a-z]?', version) and re.fullmatch('[a-f0-9]{40}', head)
for number in (kernel_run, renderer_run, compact_run, artifact_id):
    assert number.isdecimal()

base = Path('D:/ios-sweet')
build = base / 'build'
out = build / f'a618-{version}-device'
out.mkdir(exist_ok=True)
artifact = base / 'artifacts' / f'sweet-renderer-{renderer_run}'
relpath = 'sweet/lib/libSweetEAGL.dylib'
OLD_HEAD = 'ed68c3ca11794cda5978d79a436b6b009c3d65c4'
OLD_DISK = '16ab131ea40c67ba805c7cc9a63b55feea4c39d6b7fd5e268b0033f3b92a22dd'


def script(original, output, replacements):
    source = (build / original).read_text(encoding='utf-8')
    for before, after in replacements:
        assert before in source, before
        source = source.replace(before, after)
    target = out / output
    if target.suffix == '.py':
        compile(source, str(target), 'exec')
    target.write_text(source, encoding='utf-8', newline='\n')
    return target


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


if not (artifact / 'ci-evidence.json').is_file():
    download = script('fetch-xr-renderer.py', 'fetch-renderer.py', [
        ('78c3db86ec79e71152142d6b4dd147888c529662', head),
    ])
    subprocess.run([sys.executable, str(download), renderer_run], check=True)
evidence = json.loads((artifact / 'ci-evidence.json').read_text())
assert evidence['head_sha'] == head and evidence['id'] == int(renderer_run) and evidence['conclusion'] == 'success'
dylib = artifact / relpath
digest = sha(dylib)
assert [digest, relpath] in [line.split() for line in (artifact / 'SHA256SUMS').read_text().splitlines()]
data = dylib.read_bytes()
full_renderer = os.environ.get('SWEET_FULL_RENDERER') == '1'
disk_mib = 20 if full_renderer else 4
if full_renderer:
    mesa_relpath = 'sweet/lib/libOSMesa.8.dylib'
    mesa = artifact / mesa_relpath
    mesa_data = mesa.read_bytes()
    mesa_hash = hashlib.sha256(mesa_data).hexdigest()
    assert [mesa_hash, mesa_relpath] in [line.split() for line in (artifact / 'SHA256SUMS').read_text().splitlines()]
    assert b'SWEET BO: pressure retry size=%u recovered=%d' in mesa_data
for marker in (b'SWEET CA: filter uniform hook installed', b'SWEET RB: gpu call timing installed',
               b'SWEET DIRECT: frame %u of surface', b'SWEET ICON: surface='):
    assert marker in data, marker

disk = out / 'renderer.hfs'
if full_renderer:
    disk_manifest = out / 'renderer-overlay.json'
    if not disk.exists():
        def wsl_path(path):
            return '/mnt/d/' + path.as_posix().removeprefix('D:/')
        subprocess.run(['wsl', '-d', 'Ubuntu-24.04', '-u', 'root', '--', 'bash',
                        wsl_path(build / 'mk-full-renderer-disk.sh'),
                        wsl_path(dylib.parent), wsl_path(out), digest, mesa_hash], check=True)
        disk_manifest.write_text(json.dumps({'eagl': digest, 'mesa': mesa_hash, 'disk': sha(disk)}),
                                 encoding='utf-8')
    assert json.loads(disk_manifest.read_text(encoding='utf-8')) == {
        'eagl': digest, 'mesa': mesa_hash, 'disk': sha(disk)}
elif not disk.exists():
    disk_build = script('mk-xr-renderer-disk.sh', 'mk-renderer-disk.sh', [
        ('42616583415', renderer_run), ('a618-0181-device', f'a618-{version}-device'),
        ('d8fb5f46649d3cbba7fc05a261ccec29746eed6f2f058a30f604d54f55ac5e51', digest),
    ])
    ws = '/mnt/d/' + disk_build.as_posix().removeprefix('D:/')
    subprocess.run(['wsl', '-d', 'Ubuntu-24.04', '-u', 'root', '--', 'bash', ws], check=True)
assert disk.stat().st_size == disk_mib * 1024**2
if not full_renderer:
    assert data in disk.read_bytes()
new_disk = sha(disk)

compact_dir = base / 'artifacts' / f'xnu-{kernel_version}-compact-{compact_run}'
if not (compact_dir / 'kernel.development.sweet.xz').is_file():
    fetch = script('fetch-compact-0181.py', 'fetch-compact.py', [
        (OLD_HEAD, kernel_head), ('xnu-0181-compact-', f'xnu-{kernel_version}-compact-'),
        # The compact job runs at the branch head, which may be a later renderer-only commit;
        # the kernel inside is still pinned by source_run and its markers.
        (f"assert state['head_sha']=='{kernel_head}'", f"assert state['head_sha'] in ('{kernel_head}', '{head}')"),
        ('READY compact 0181', f'READY compact {kernel_version}'),
    ])
    subprocess.run([sys.executable, str(fetch), compact_run, artifact_id], check=True)

# SWEET_GPU_LEVEL=N (0190 and later kernels): boot with sweetgmudcvs=N, GPU level N of 1..7.
# Same length as sweetgmudcvs=1, so the 580-byte command line keeps its size.
level = os.environ.get('SWEET_GPU_LEVEL', '')
level_edits = []
if level:
    assert len(level) == 1 and level in '1234567', level
    level_edits = [
        ("flags.insert(len(flags) - 1, 'sweetusb=3')\n",
         "flags.insert(len(flags) - 1, 'sweetusb=3')\n"
         "assert flags.count('sweetgmudcvs=1') == 1\n"
         f"flags[flags.index('sweetgmudcvs=1')] = 'sweetgmudcvs={level}'\n"),
        ("(b'SWEET CA: panel memory at GPU VA',", "(b'SWEET GMU DCVS: requested index=', b'SWEET CA: panel memory at GPU VA',"),
    ]
    print('GPU level', level, flush=True)
# SWEET_CPUS=N: boot with cpus=N (1..8; 6 = the six A55 cores, 8 adds the two A76). Same length.
cpus = os.environ.get('SWEET_CPUS', '')
if cpus:
    assert len(cpus) == 1 and cpus in '12345678', cpus
    level_edits.append(
        ("flags.insert(len(flags) - 1, 'sweetusb=3')\n",
         "flags.insert(len(flags) - 1, 'sweetusb=3')\n"
         "assert flags.count('cpus=6') == 1\n"
         f"flags[flags.index('cpus=6')] = 'cpus={cpus}'\n"))
    print('CPUs', cpus, flush=True)
# SWEET_WFI=1 (0209 and later kernels): boot with wfi=1, so idle cores wait in WFI once the GPU is up
# instead of spinning. Same length as wfi=0.
wfi = os.environ.get('SWEET_WFI', '')
if wfi:
    assert wfi == '1', wfi
    level_edits.append(
        ("flags.insert(len(flags) - 1, 'sweetusb=3')\n",
         "flags.insert(len(flags) - 1, 'sweetusb=3')\n"
         "assert flags.count('wfi=0') == 1\n"
         "flags[flags.index('wfi=0')] = 'wfi=1'\n"))
    print('WFI on', flush=True)
# SWEET_USBNET=1 (0211 and later kernels): sweetusb=4, the USB console plus an RNDIS network
# function that Windows drives itself (ue0 192.168.137.2 beside Internet Connection Sharing).
usbnet = os.environ.get('SWEET_USBNET', '')
if usbnet:
    assert usbnet == '1', usbnet
    level_edits.append(
        ("flags.insert(len(flags) - 1, 'sweetusb=3')\n",
         "flags.insert(len(flags) - 1, 'sweetusb=3')\n"
         "assert flags.count('sweetusb=3') == 1\n"
         "flags[flags.index('sweetusb=3')] = 'sweetusb=4'\n"))
    print('USB console + RNDIS network', flush=True)

image_build = script('prepare-a618-0181-image.py', 'prepare-image.py', [
    ('xnu-0181-compact-', f'xnu-{kernel_version}-compact-'),
    ('a618-0181-device', f'a618-{version}-device'),
    ('a618-0181-image.json', f'a618-{version}-image.json'),
    ('temporary 0181 GPU', f'temporary {version} GPU'),
    (OLD_DISK, new_disk),
    ('source_run=42620402082', f'source_run={kernel_run}'),
    (OLD_HEAD, kernel_head),
    ("for marker in (b'SWEET CA: renderer armed',",
     "for marker in (b'SWEET CA: panel memory at GPU VA', b'SWEET FB: frame already on the panel', b'SWEET CA: renderer armed',"),
] + level_edits + ([('4 * 1024**2', f'{disk_mib} * 1024**2')] if full_renderer else []))
subprocess.run([sys.executable, str(image_build), compact_run], check=True)

script('boot-a618-0181.py', 'boot.py', [
    ("assert version == '0181'", f"assert version == '{version}'"),
    (OLD_DISK, new_disk), (OLD_HEAD, kernel_head),
])
script('read-sweet-usb-0181.ps1', 'read-usb.ps1', [
    ('a618-0181-device', f'a618-{version}-device'),
    ('SWEET CA: renderer RAM disk|',
     'SWEET CA: (renderer RAM disk|panel memory|filter uniform)|SWEET RB|SWEET DIRECT|SWEET DMG|SWEET ICON|SWEET FB: frame already|CoreAnimation gives|colour matrix|'),
])
wait = (build / 'wait-0181d-log.ps1').read_text(encoding='utf-8').replace('0181d', version)
(build / f'wait-{version}-log.ps1').write_text(wait, encoding='utf-8', newline='\n')
print(f'Verified {version} renderer {digest}, disk {new_disk}', flush=True)
