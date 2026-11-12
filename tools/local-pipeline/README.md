# Local pipeline (as used)

These are the scripts that built the boot images and the jailbroken iOS root for `sweet_k6a` and put
apps on the phone, copied as they were used on the Windows build machine. They expect the layout
`D:\ios-sweet\{src,build,artifacts,work,jb,keys}` and Git Bash, PowerShell 5.1, Python 3 and WSL
(Ubuntu 24.04, for HFS+ images). Treat them as a working reference, not a polished installer.

## image/ — boot images

- `finish-image2.sh VERSION KERNEL_HEAD KERNEL_RUN RENDERER_RUN RENDERER_HEAD MARKER` waits for the
  kernel CI run, fetches the compact kernel artifact, builds the image (`prepare-kernel-renderer.py`
  → `prepare-a618-0181-image.py`), checks that the kernel carries MARKER and boots it from recovery
  (`boot-when-recovery.ps1` → `boot.py` made from `boot-a618-0181.py`).
  Environment: `SWEET_SRGB=1` (sRGB device tree → BGRA surfaces), `SWEET_USBNET=1` (`sweetusb=4`:
  USB console + RNDIS network), `SWEET_WFI=1` (CPU idle), `SWEET_GPU_LEVEL`, `SWEET_CPUS`.
- `read-sweet-usb-0181.ps1` reads the kernel console from the USB serial port into a log.
- `dispatch-a618-kernel-windows.py BRANCH SHA` starts the kernel build on GitHub Actions;
  `gh_token.py` takes the GitHub token from Git Credential Manager.
- `frame-stats.py LOG` summarises the renderer's frame timings from a console log.

## jb/ — jailbroken root

- `mk-jb-root.sh SWEETNET` (WSL, root): from a working iOS root image adds the palera1n Procursus
  rootful bootstrap, ElleKit, Sileo, NewTerm, OpenSSH (installed by dpkg on first boot),
  `sweetnet`, the launchd jobs (`jb-launchd-sweet.py`) and Sileo sources. After the Galaxy S9 port
  (syncmodz/ios-s9, MIT).
- `flash-jb-root.ps1 -BootVersion V` flashes the sparse image into `userdata` (checks the product,
  the partition size and the image hash first) and boots image V. **Erases userdata.**
- `mk-krw-stub-deb.py OUT.deb`: an empty package that Provides `libkrw0-plugin`, so apt accepts the
  bootstrap's libkrw0 (no kernel read/write behind it).

## helpers/

- `ipa2tar.py APP.ipa OUT.tar` repacks an .ipa's `Payload/*.app` as a tar keeping Unix modes (the
  phone has tar but no unzip or gzip). Install: copy the tar, `tar -xf X.tar -C /Applications`,
  `chown -R root:wheel`, `uicache -p /Applications/X.app`.
- `copy-in-pieces.ps1 -File F` copies a big file over USB SSH in 5 MB pieces, retrying each piece
  until the link is back, and checks the SHA-256 on the phone.
- `fdt-grep.py FILE.dtb REGEX...` greps a flattened device tree without dtc.

## patch-generators/

`make-NNNN.py` wrote `xnu/patches/NNNN-*.patch` from the previous patches and a list of edits, then
checked that the patch applies forward and backward and registered it in the CI checks
(`tools/check-sweet-patch-reversal.sh`, `tools/verify-gmu-service-patch.py`). Each one's docstring
says why the patch exists. Their base is a local CI build tree, which is not part of this repository.
