# ios-sweet_k6a

**iOS 16 on the Redmi Note 12 Pro 4G (`sweet_k6a`, Snapdragon 732G / SM7150, Adreno 618).**

A port of Apple's open-source XNU kernel (xnu-8796, the iOS 16 generation) to the Redmi Note 12 Pro
4G, running the **unmodified iOS 16.7.16 (20H392) userland of the iPhone X**. The UI is drawn by the
phone's own **Adreno 618 GPU**, through our kernel GPU driver and Mesa freedreno behind
CoreAnimation's OpenGL ES renderer. All eight CPU cores run, there is a rootful jailbreak with
tweaks, and internet over the USB cable.

> Experimental bring-up, not a daily-driver OS. iOS installs into the `userdata` partition, so
> **Android's user data is erased**. The kernel is started temporarily with `fastboot boot`: the
> bootloader, recovery, modem, persist and boot partitions are never flashed. No iOS firmware
> (IPSW) or other Apple files are in this repository; you supply your own.

## What it is

- **Kernel:** Apple's open-source XNU (xnu-8796.141.3) with our patches (`xnu/patches/`, up to
  0225), built on GitHub Actions (`.github/workflows/xnu.yml`, macOS runner, darwin-xnu-build).
- **Userland:** the real iPhone X system: iOS 16.7.16 (20H392), launchd, the system daemons,
  backboardd, SpringBoard and the stock apps.
- **Boot:** stock Xiaomi bootloader → `fastboot boot` of our image (shim + XNU + device tree) → XNU.
  The iOS root is an HFS+ volume in `userdata`.
- **Identity:** the phone presents itself to iOS as an iPhone X (`iPhone10,3`), the screen as a
  1125×2436 panel.

This continues [dipa-studio/ios-sweet](https://github.com/dipa-studio/ios-sweet), the same port for
the Redmi Note 10 Pro (`sweet`). The `sweet_k6a` and GPU work is done here. Upstream's previous
README is kept as [`docs/UPSTREAM-README.md`](docs/UPSTREAM-README.md).

## What works

| Area | State |
| --- | --- |
| Boot | Temporary `fastboot boot`; iOS reaches the home screen |
| CPU | All 8 cores (6× Cortex-A55 + 2× Cortex-A76), own frequency governor: A55 up to 1804 MHz, A76 up to 2304 MHz |
| GPU | **The Adreno 618 draws the whole UI.** Own kernel driver (GMU, HFI, SMMU, CP command ring) with Mesa freedreno (OSMesa) behind CoreAnimation's OpenGL ES renderer |
| Smoothness | Asynchronous GPU submission with fences (0215): median frame 4–8 ms, heavy animations 14–16 ms. Render threads pinned to the fast A76 cores (0203, 0217). Zero-copy IOSurfaces (0206–0208); BGRA surfaces through an sRGB device tree |
| UI | Lock screen, home screen, Control Center, Notification Center, Settings, stock apps |
| Touch and buttons | Touchscreen, power and volume keys (from upstream) |
| Jailbreak | Rootful: Procursus bootstrap (palera1n's), Sileo, NewTerm, OpenSSH, tweaks through ElleKit (`DYLD_INSERT_LIBRARIES` allowed by the in-kernel AMFI policy, 0213). apt works (a `libkrw0-plugin` stub) |
| USB | Kernel console (CDC ACM) and an RNDIS network at the same time (`sweetusb=4`, 0211, 0216–0219). Windows sees the phone as a network adapter with its built-in driver |
| Internet | Over the cable: Windows Internet Connection Sharing → phone at 192.168.137.2. Safari, Sileo, SSH (`root@192.168.137.2`) |
| Apps | Decrypted .ipa files install into `/Applications` over SSH + `uicache` and run |

## What does not work

- **Wi-Fi, Bluetooth, cellular, audio, camera, flashlight, haptics:** no drivers yet. For Wi-Fi the
  Redmi K20 Pro port has a working chain (WCN3990 through ICNSS + the modem + ath10k); this phone has
  the same hardware, but the port has not been done.
- **Brightness:** an attempt (0220: DCS 0x51 over DSI + `AppleARMBacklight`) broke the picture and
  crashed the phone, so it was removed. The analysis is in `NOTES.md`.
- **Metal:** none. Most current games (Unity, Unreal) render with Metal and will not start; OpenGL ES
  games have a chance.
- **The USB network is unstable.** After a few minutes (sooner under load, and when Windows sharing
  is already on before the phone boots) Windows loses an answer on the RNDIS control channel, resets
  the pipes and the link stays down until the cable is replugged. Patches 0222–0225 did not find the
  cause (they are harmless and kept). Copy big files in pieces
  (`tools/local-pipeline/helpers/copy-in-pieces.ps1`).
- **CPU idle (WFI) is off** (`wfi=0`), so the phone gets warm even when idle. The idle path (0209,
  0210, 0212, 0214) is written but not fully tested: 0212 gave a black screen, 0214 should fix that.
- **Jailbreaks for real iPhones** (Dopamine, Serotonin) do not work: they exploit Apple's kernel, and
  this one is different. Dopamine crashes (an arm64e-only library), Serotonin panics the kernel.
- iOS sometimes restarts itself (Apple logo without a kernel reboot) when the system watchdog finds a
  hung process.
- Apple's security model is mostly switched off (AMFI, sandbox and so on). Keep nothing important
  on it.

## Repository layout

| Path | Contents |
| --- | --- |
| `xnu/patches/` | XNU patches in order (0001–0225), each with a description at the top; the generators of the recent ones are in `tools/local-pipeline/patch-generators/` |
| `xnu/gpu/`, `xnu/cpufreq/`, `xnu/amfi/` | Sources of the GPU driver, the frequency governor and the AMFI service (mirrors of the files the patches add) |
| `shim/` | Boot shim: starts on the core the bootloader hands over, wakes the right cores and passes control to XNU |
| `tools/` | Kernel and image tooling, device tree generation (`mkadt.py`), iOS root builder (`mkiosroot.sh`), renderer build (`build-sweet-renderer.sh`), log parsers |
| `userland/gpu/` | EAGL/Mesa patches and our libraries for CoreAnimation rendering on the GPU |
| `userland/jb/` | `sweetnet`: publishes the USB network (`ue0`) to configd so apps see the internet |
| `tools/local-pipeline/` | The scripts that built the images and the jailbroken root and installed apps, as used (paths under `D:\ios-sweet\...`; see the README there) |
| `NOTES.md` | The full working log: every build, boot, measurement and mistake |
| `docs/` | Documents on the GPU, panel output and QEMU testing |

## Building (short version)

1. **Kernel:** GitHub Actions `xnu` (workflow_dispatch) applies `xnu/patches/` to xnu-8796.141.3 and
   builds `kernel.development.sweet`; a separate job builds the renderer (Mesa + EAGL).
2. **iOS root:** an iPhone X 20H392 IPSW (your own) → `tools/mkiosroot.sh` → an HFS+ image for
   `userdata`. The jailbroken root on top of it: `tools/local-pipeline/jb/mk-jb-root.sh`.
3. **Boot image:** shim + kernel + device tree + renderer RAM disk (`tools/local-pipeline/`), then
   `fastboot boot`.
4. **Internet:** an image with `sweetusb=4`; on Windows, share the internet connection to the
   "Remote NDIS" adapter.

Details, build numbers and every pitfall are in `NOTES.md`.

## Credits and licenses

- [dipa-studio/ios-sweet](https://github.com/dipa-studio/ios-sweet) and its authors (dipa-studio,
  damjankakak3, legendxdevil and others): the base of this port. MIT license (`LICENSE`).
- Apple: XNU (APSL 2.0). The XNU patches are derivatives of XNU and fall under APSL 2.0.
- [Mesa](https://mesa3d.org/) / freedreno (MIT).
- [MakrSas/ios-topaz](https://github.com/MakrSas/ios-topaz): the EAGL renderer for CoreAnimation;
  its `eagl.c` is downloaded when the renderer is built and is not part of this repository.
- HackiOS (oosexgang; APSL 2.0 / MIT) and
  [HeliumStudio-Dev/hackios-xnu-kernel](https://github.com/HeliumStudio-Dev/hackios-xnu-kernel)
  (the Redmi K20 Pro port): reference for Qualcomm hardware.
- [syncmodz/ios-s9](https://github.com/syncmodz/ios-s9) (MIT): the way the jailbroken root is built
  and `s9net`, which `sweetnet` is adapted from.
- palera1n / Procursus, Sileo, ElleKit, blacktop/darwin-xnu-build.

iOS, the IPSW, Apple's trademarks and the phone's firmware are not part of this repository.
