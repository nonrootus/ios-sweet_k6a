#!/usr/bin/env python3
"""Inspect candidate A618 firmware offline; does not load or access a GPU.

Usage: python3 a618-firmware-check.py GMU_BIN SQE_FW
The SQE test follows Linux a6xx_ucode_check_version for a630_sqe.fw only.
Passing these checks does not prove firmware is genuine or device-compatible.
"""
import hashlib
import json
import struct
import sys
from pathlib import Path


def inspect(gmu, sqe):
    gmu_size = len(gmu)
    if len(sqe) < 16:
        raise ValueError('SQE candidate is shorter than the 4-byte header plus three words')
    word0, _, word2 = struct.unpack_from('<III', sqe, 4)
    patched = (word0 & 0xf) == 0xa and (word2 & 0xf) >= 1
    version = word0 & 0xfff
    return {
        'gmu': {'size': gmu_size, 'sha256': hashlib.sha256(gmu).hexdigest(),
                'legacy_size_within_limit': 0 < gmu_size <= 0x8000},
        'sqe': {'size': len(sqe), 'sha256': hashlib.sha256(sqe).hexdigest(),
                'payload_word0': f'0x{word0:08x}', 'payload_word2': f'0x{word2:08x}',
                'linux_a630_version_test': bool(patched or version >= 0x190),
                'note': 'Only valid for a630_sqe.fw; identity and hardware compatibility not verified'},
    }


def main():
    if len(sys.argv) != 3: raise SystemExit(__doc__)
    try:
        result = inspect(Path(sys.argv[1]).read_bytes(), Path(sys.argv[2]).read_bytes())
    except (OSError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(result, indent=2))
    if not result['gmu']['legacy_size_within_limit'] or not result['sqe']['linux_a630_version_test']:
        raise SystemExit(1)

if __name__ == '__main__': main()
