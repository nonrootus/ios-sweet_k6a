#!/bin/bash
# finish-image2.sh VERSION KERNEL_HEAD KERNEL_RUN RENDERER_RUN RENDERER_HEAD MARKER
# Builds the image with its own renderer disk (needs WSL) and boots it from recovery if the
# kernel carries MARKER. SWEET_SRGB in the environment selects the sRGB device tree.
version=$1; head=$2; run=$3; renderer_run=$4; renderer_head=$5; marker=$6
cd /d/ios-sweet/build
mkdir -p a618-$version-device
export SWEET_GPU_LEVEL=7 SWEET_CPUS=8 SWEET_FULL_RENDERER=1 PYTHONUNBUFFERED=1
python finish-kernel-image.py $version $head $run $renderer_run $renderer_head || { echo "IMAGE FAILED"; exit 1; }
n=$(grep -a -c "$marker" a618-$version-device/kernel.development.sweet)
echo "marker count $n"
[ "$n" -ge 1 ] || { echo "KERNEL HAS NO MARKER, not booting"; exit 2; }
powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'D:\ios-sweet\build\boot-when-recovery.ps1' -Version $version -WaitMinutes 120
echo "boot script exit $?"
