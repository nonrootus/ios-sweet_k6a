"""Android boot image header v2 writer, byte-for-byte as AOSP mkbootimg (no second stage, no recovery dtbo).

Used when WSL (where mkbootimg lives) is unavailable. Same arguments as the WSL call in prepare-image.py.
"""
import argparse
import hashlib
import struct


def parse_int(text):
    return int(text, 0)


def os_version(text):
    a, b, c = (list(map(int, text.split('.'))) + [0, 0])[:3]
    return (a << 14) | (b << 7) | c


def patch_level(text):
    y, m = map(int, text.split('-')[:2])
    return ((y - 2000) << 4) | m


def build(kernel, ramdisk, dtb, base, kernel_offset, ramdisk_offset, tags_offset, dtb_offset, pagesize,
          os_ver, os_patch, cmdline):
    sha = hashlib.sha1()
    for blob in (kernel, ramdisk):
        sha.update(blob)
        sha.update(struct.pack('I', len(blob)))
    sha.update(struct.pack('I', 0))                    # no second stage
    sha.update(struct.pack('I', 0))                    # no recovery dtbo
    sha.update(dtb)
    sha.update(struct.pack('I', len(dtb)))
    args = cmdline.encode()
    assert len(args) < 512 + 1024
    header = b''.join([
        b'ANDROID!',
        struct.pack('10I', len(kernel), base + kernel_offset, len(ramdisk), base + ramdisk_offset, 0,
                    0, base + tags_offset, pagesize, 2, (os_ver << 11) | os_patch),
        struct.pack('16s', b''),
        struct.pack('512s', args[:512]),
        struct.pack('32s', sha.digest()),
        struct.pack('1024s', args[512:]),
        struct.pack('<IQ', 0, 0),                      # recovery dtbo size and offset
        struct.pack('<I', 1660),                       # header size, v2
        struct.pack('<IQ', len(dtb), base + dtb_offset),
    ])
    assert len(header) == 1660, len(header)

    def padded(blob):
        return blob + b'\0' * ((pagesize - len(blob) % pagesize) % pagesize)
    return padded(header) + padded(kernel) + padded(ramdisk) + padded(dtb)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--header_version', type=int, required=True)
    p.add_argument('--kernel', required=True)
    p.add_argument('--ramdisk', required=True)
    p.add_argument('--dtb', required=True)
    for name in ('base', 'kernel_offset', 'ramdisk_offset', 'tags_offset', 'dtb_offset', 'pagesize'):
        p.add_argument('--' + name, type=parse_int, required=True)
    p.add_argument('--os_version', required=True)
    p.add_argument('--os_patch_level', required=True)
    p.add_argument('--cmdline', default='')
    p.add_argument('-o', '--output', required=True)
    a = p.parse_args()
    assert a.header_version == 2
    data = build(open(a.kernel, 'rb').read(), open(a.ramdisk, 'rb').read(), open(a.dtb, 'rb').read(), a.base,
                 a.kernel_offset, a.ramdisk_offset, a.tags_offset, a.dtb_offset, a.pagesize,
                 os_version(a.os_version), patch_level(a.os_patch_level), a.cmdline)
    open(a.output, 'wb').write(data)
