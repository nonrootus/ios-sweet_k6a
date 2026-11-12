"""Verify the compact 0181 CI kernel and build a temporary GPU UI test image."""
from pathlib import Path
import hashlib
import json
import lzma
import struct
import subprocess
import sys

root = Path('D:/ios-sweet')
build = root / 'build'
repo = root / 'src/ios-sweet'
compact_run = int(sys.argv[1])
compact = root / 'artifacts' / f'xnu-0181-compact-{compact_run}'
out = build / 'a618-0181-device'
out.mkdir(exist_ok=True)
compressed = compact / 'kernel.development.sweet.xz'

def checked_hash(path, manifest):
    lines = [line.split() for line in (compact / manifest).read_text().splitlines()]
    expected = [entry[0] for entry in lines if entry[-1] == path.name]
    assert len(expected) == 1
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(chunk)
    assert h.hexdigest() == expected[0], path
    return expected[0]

compressed_hash = checked_hash(compressed, 'COMPRESSED-SHA256SUMS')
kernel = out / 'kernel.development.sweet'
with lzma.open(compressed, 'rb') as source, kernel.open('wb') as target:
    while chunk := source.read(8 * 1024 * 1024):
        target.write(chunk)
kernel_hash = checked_hash(kernel, 'SHA256SUMS')
data = kernel.read_bytes()
for marker in (b'SWEET CA: renderer armed', b'SWEET CA: hardware submit fence=',
               b'SweetAdrenoUserClient', b'SWEET A618 FILL: result rc=',
               b'sweetcagpu', b'SWEET CA: dyld policy for %s input=', b'SWEET SURF: b3a8 id %u plane', b'SWEET CA: BO recycle first=', b'SWEET FB: b3a8 visible pixels', b'Sweet iOS (USB console)', b'SWEET CA: renderer RAM disk mount rc='):
    assert marker in data, marker

prior = build / 'xnu-memory-probe-42474284974'
baseline = json.loads((prior / 'hfi-image-verification.json').read_text())
old_boot = json.loads((build / 'a618-zap-fdt-preflight/boot-attempt-20261108T120043Z.json').read_text())
old_flags = json.loads((build / 'xnu-memory-probe-42492574400/a618-0172-image.json').read_text())['flags']
assert old_flags[-2:] == ['sweetgpufill=3', 'sweetzaplayout=1']
assert old_flags.count('sweetiolog=-') == 1
flags = [flag for flag in old_flags[:-2] if flag != 'sweetiolog=-'] + [
    'sweetgpufill=1', 'sweetcagpu=1', 'sweetzaplayout=1']
assert flags.count('-noprogress') == 1
flags.remove('-noprogress')
assert flags[-1] == 'sweetzaplayout=1'
flags.insert(len(flags) - 1, 'sweetusb=3')
cmdline = ' '.join(flags)
# The shim appends " sweetzapfdt=0x05" at runtime after inspecting the live
# FDT. Its C size check includes a NUL byte: leave enough room for 19 bytes.
assert len(cmdline) == 580 and len(cmdline) + len(' sweetzapfdt=0xff') < 608

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

adt = prior / 'sweet-k6a-zap-reserve.adt'
firmware = root / 'research/sweet-k6a-gpu-firmware-20261027/gpu-firmware.bundle'
shim = build / 'a618-zap-fdt-preflight/shim/out/Image'
dtb = repo / 'dtb/boot_unpacked/dtb'
assert sha(adt) == baseline['adt_sha256']
assert sha(firmware) == baseline['firmware_bundle_sha256']
assert sha(shim) == old_boot['shim_sha256']
assert sha(dtb) == baseline['dtb_sha256']
sys.path.insert(0, str(repo / 'tools'))
import mkpayload
import os
# SWEET_SRGB=1: the display is sRGB in the device tree (like the K20 Pro port), so that iOS draws
# in plain BGRA surfaces instead of 10-bit w30r/b3a8 ones.
if os.environ.get('SWEET_SRGB') == '1':
    tree, _ = mkpayload.adt.parse(adt.read_bytes())
    product = next(c for c in tree.children if c.name == 'product')
    assert product.prop('artwork-display-gamut') == b'P3\0'
    product.props = [(n, f, b'sRGB\0' if n == 'artwork-display-gamut' else v) for n, f, v in product.props]
    adt = out / 'sweet-srgb.adt'
    adt.write_bytes(mkpayload.adt.serialize(tree))
    print('device tree: sRGB display gamut', flush=True)
renderer_disk = out / 'renderer.hfs'
renderer_hash = sha(renderer_disk)
assert renderer_hash == '16ab131ea40c67ba805c7cc9a63b55feea4c39d6b7fd5e268b0033f3b92a22dd'
payload, info = mkpayload.build(kernel, adt, cmdline, firmware, renderer_disk)
payload_adt_off, payload_adt_size = struct.unpack_from('<2Q', payload, 0x20)
payload_adt, _ = mkpayload.adt.parse(payload[payload_adt_off:payload_adt_off + payload_adt_size])
chosen = next(c for c in payload_adt.children if c.name == 'chosen')
mmap = next(c for c in chosen.children if c.name == 'memory-map')
fw_pa, fw_size = struct.unpack('<2Q', mmap.prop('RAMDisk'))
disk_pa, disk_size = struct.unpack('<2Q', mmap.prop('SweetRendererDisk'))
assert fw_size == firmware.stat().st_size and disk_pa == fw_pa + fw_size
assert disk_size == renderer_disk.stat().st_size == 4 * 1024**2
nsegs, = struct.unpack_from('<I', payload, 12)
rd_va, rd_len, rd_offset, rd_file_size = struct.unpack_from('<4Q', payload, 0x2a8 + 32 * (nsegs - 1))
assert rd_va - int(info['virt_base'], 16) + mkpayload.adt_dram(adt.read_bytes())[0] == fw_pa
assert rd_len == rd_file_size == fw_size + disk_size
assert int(info['kernel_end'], 16) == rd_va + rd_len
assert payload[rd_offset:rd_offset + fw_size] == firmware.read_bytes()
assert payload[rd_offset + fw_size:rd_offset + rd_file_size] == renderer_disk.read_bytes()
assert info['fixups'] == 0
assert payload[0x48:0x2a8] == cmdline.encode().ljust(608, b'\0')
parts = mkpayload.parse_macho(data)
segments = [entry for entry in parts['segs'] if entry['vmsize']]
assert len(segments) == 10
for index, segment in enumerate(segments):
    va, vs, offset, size = struct.unpack_from('<4Q', payload, 0x2a8 + 32 * index)
    assert (va, vs, size) == (segment['vmaddr'], segment['vmsize'], segment['filesize'])
    assert payload[offset:offset + size] == data[segment['fileoff']:segment['fileoff'] + size]
payload_file = out / 'payload.bin'
payload_file.write_bytes(payload)
image = out / 'shim-boot-sweet-a618-gpu.img'
ws = lambda path: str(path)  # mkbootimg_v2.py runs on Windows (byte-identical to the WSL mkbootimg)
subprocess.run([sys.executable, 'D:/ios-sweet/build/mkbootimg_v2.py', '--header_version', '2',
    '--kernel', ws(shim), '--ramdisk', ws(payload_file), '--dtb', ws(dtb),
    '--base', '0', '--kernel_offset', '0x8000', '--ramdisk_offset', '0x1000000',
    '--tags_offset', '0x100', '--dtb_offset', '0x1f00000', '--pagesize', '4096',
    '--os_version', '17.0.0', '--os_patch_level', '2035-06', '--cmdline', 'console=null',
    '-o', ws(image)], check=True)
raw = image.read_bytes()
assert raw[:8] == b'ANDROID!'
ks, ka, rs, ra, ss, sa, ta, page, hver, osv = struct.unpack_from('<10I', raw, 8)
assert (ka, ra, ss, ta, page, hver) == (0x8000, 0x1000000, 0, 0x100, 4096, 2)
aligned = lambda n: (n + page - 1) & -page
ramdisk_at = page + aligned(ks)
dtb_at = ramdisk_at + aligned(rs)
assert (ks, rs) == (shim.stat().st_size, len(payload))
assert raw[page:page + ks] == shim.read_bytes()
assert raw[ramdisk_at:ramdisk_at + rs] == payload
assert raw[dtb_at:dtb_at + dtb.stat().st_size] == dtb.read_bytes()
result = dict(source_run=42620402082, compact_run=compact_run,
    kernel_source='ed68c3ca11794cda5978d79a436b6b009c3d65c4',
    kernel_sha256=kernel_hash, compressed_sha256=compressed_hash,
    payload_sha256=hashlib.sha256(payload).hexdigest(),
    image_sha256=hashlib.sha256(raw).hexdigest(), image_bytes=len(raw),
    flags=flags, segments_verified=len(segments), renderer_disk_sha256=renderer_hash)
(out / 'a618-0181-image.json').write_text(json.dumps(result, indent=2) + '\n')
print('READY verified temporary 0181 GPU UI boot image', result['image_sha256'], flush=True)
