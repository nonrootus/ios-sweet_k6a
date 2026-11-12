#!/usr/bin/env python3
"""Inspect saved Android FDT descriptions for sweet wireless and cameras.

Usage: python device-peripherals.py captured.dtb
Results describe device-tree nodes; they do not identify active firmware,
attached sensor modules, register ownership or a working iOS driver.
"""
import importlib.util
import json
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location('sweet_gpu_fdt', Path(__file__).with_name('gpu-dt-info.py'))
fdt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fdt)


def inspect(data):
    nodes = fdt.parse_fdt(data)
    result = {'bluetooth': [], 'wireless': [], 'camera_sensors': [], 'camera_controllers': []}
    for path, props in nodes.items():
        comp = fdt.names(props['compatible']) if 'compatible' in props else []
        item = {'path': path, 'compatible': comp}
        if 'status' in props:
            item['status'] = fdt.names(props['status'])
        if 'reg' in props:
            item['reg_cells'] = [f'0x{x:x}' for x in fdt.cells(props['reg'])]
        if 'cell-index' in props:
            item['cell_index'] = fdt.cells(props['cell-index'])
        if 'qca,wcn3990' in comp:
            result['bluetooth'].append(item)
        if 'qcom,icnss' in comp:
            result['wireless'].append(item)
        if 'qcom,cam-sensor' in comp:
            result['camera_sensors'].append(item)
        if 'qcom,camcc-sdmmagpie' in comp or 'qcom,cam-isp' in comp:
            result['camera_controllers'].append(item)
    return result


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    print(json.dumps(inspect(Path(sys.argv[1]).read_bytes()), indent=2))


if __name__ == '__main__':
    main()
