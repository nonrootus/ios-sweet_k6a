# iOS 16 on sweet / sweet_k6a - working notes

## Current sweet_k6a handoff - 2026-11-09 (read first)

### 2026-11-11: 0218n hung USB after 4 min of RNDIS; 0219; brightness/torch/Wi-Fi sources

- 0218n (kernel CI 43028250140, booted 13:32 UTC, `build/a618-0218n-device/live-20261111T133233Z.log`):
  Windows' RNDIS adapter came up ("Ethernet 4", 480 Mbps, packet filter 0xb; 868 frames in, 36 out,
  sweetnet started; first `GPU thread 1 of backboardd bound to A76 core 7`). At 13:37 UTC the phone
  stopped answering on USB (Windows: "device descriptor request failed", VID_0000&PID_0002); no
  panic in the log, whose last control requests were two 76-byte RNDIS SETs without a
  GET_ENCAPSULATED_RESPONSE between them (475 such SETs in 4 minutes). Whether the UI froze too is
  not known. Rebooted to 0218n from fastboot with `a618-0218n-device/boot.py 0218n` (boot.py also
  works from fastboot; boot-when-recovery only waits for recovery).
- **0219** (`build/make-0219.py` via `gen-make-0219.py`, local 3e2990c, published 1c429d3, kernel CI
  43032319438): bus reset ends every active transfer (resource index kept per endpoint), clears
  configured/RNDIS state and arms SETUP again; one RESPONSE_AVAILABLE at a time with the rest queued
  on its completion; up to four unread answers; an abandoned control data stage stalls and restarts
  EP0; the first 16 RNDIS SETs log their OID. Image 0219n (SWEET_SRGB=1, SWEET_USBNET=1) booted
  14:02:51 UTC, but `a618-0219n-device/live-20261111T140251Z.log` stayed EMPTY (no console at all)
  and at 15:51 UTC the phone was not on USB (another phone, a POCO X8 Pro Max with ADB, was
  plugged in instead: never touch it). 0219n is unverified.
- ICS: the owner opened the Sharing tab of "vEthernet (Беспроводная се)" (its list lacked that
  name) instead of "Беспроводная сеть", and the phone's adapter was already gone by then.
- Feature sources (outside git): `research/topaz/e4772911` (MakrSas/ios-topaz, no licence file:
  reference only; brightness 0104/0105/0110, WLAN 0123-0130, audio 0144-0146) and
  `research/hackios-raphael/57722468` (HeliumStudio-Dev/hackios-xnu-kernel branch raphael-bringup,
  Redmi K20 Pro: kernel APSL 2.0, rest MIT; torch, sound, Wi-Fi via ICNSS + MPSS + ath10k SNOC,
  haptic, camera, modem). Brightness plan: DSI0 0xae94000 (dsi-ctrl-hw-v2.3), panel
  `k6 38 0c 0a fhd dsc video` (video mode, DCS backlight 8..0x7ff, 120 Hz timing), DCS 0x51 through
  the command DMA as topaz, waiting for the video engine; AppleARMBacklight for CoreBrightness.
  `build/fdt-grep.py` reads the stock DT without dtc. Owner also wants glthread, torch, sound,
  Wi-Fi without the PC.
- **0220** (`build/make-0220.py`, local 02b3e5f, published f372f74, kernel CI 43053484110; kernel has
  0217-0220): brightness. AppleARMBacklight (backlight-control, brightness-nits, max-nits 420) for
  CoreBrightness; IOMFBBrightnessLevel (nits 16.16) -> level 8..0x7ff -> DCS 0x51 MSB first (panel
  flag qcom,mdss-dsi-bl-dcs-type-ss-ea) as one long write through DSI0's command DMA (0xae94000,
  buffer below 4 GiB, HS, SW trigger, CMD_DMA_DONE polled 50 ms), waiting up to 20 ms for the video
  engine to go idle first; three failures turn it off. Display off sends level 0, on restores.
  Logs `AppleARMBacklight published; DSI0 ctrl .. status ..`, `panel level 0x..: done|NO DONE`.
  Local strict compile: 0 errors, two new warning kinds (cast-align, reserved identifier from the
  metaclass macro) of kinds already present. Untested on the phone; a DSI command in video mode
  could glitch the panel; the MDSS SMMU must let the DMA read the buffer (topaz's worked).
  Image 0220n (SWEET_SRGB=1, SWEET_USBNET=1) queued by finish-image2 (`a618-0220n-device/finish.log`).
- **Copying apps over scp kills the USB link (0219n); 0222.** SSH key login for the agent:
  `D:\ios-sweet\keys\sweet_ed25519` (owner added it to /var/root/.ssh/authorized_keys; never type
  the password for the owner). Apps go in as `build`-side tar (zip modes kept, scratchpad
  `ipa2tar.py`) -> scp -> `tar -xf -C /Applications`, chown root:wheel, `uicache -p`. Phone has no
  unzip/ldid, and apt is broken (libkrw0 needs libkrw0-plugin; two repos lack keys): do not
  "fix" it blindly. Dopamine installed but crashes ("Library not loaded: @rpath/Titan.framework",
  likely arm64e-only); the owner gave up on it. Serotonin (Def1nit3lyN0tAJa1lbr3akTool.ipa) did not
  get through: the 180 MB tar and then a 67 MB tar.gz both broke the link (sshd reset, then no
  route until the cable was replugged). Console before: ue0 TX counter stuck while RX counted,
  then CLEAR_FEATURE(ENDPOINT_HALT) for 0x83/0x03/0x84 from Windows. **0222** (`build/make-0222.py`
  via `gen-make-0222.py`, local 520e74d, published cb9d00c, kernel CI 43065849147): failed TX start
  no longer leaves the endpoint busy; ENDPOINT_HALT clear = End Transfer + Clear Stall + restart
  that endpoint's work, set = Set Stall; a TX transfer older than 2 s is ended (log `ue0 TX stuck`).
  Image 0222n (SWEET_SRGB=1, SWEET_USBNET=1) queued by finish-image2. Note: read-usb.ps1 stops
  for good when the cable is pulled; restart it after a replug.
- 0222n (booted 17:30:29 UTC, `a618-0222n-device/live-20261111T173029Z.log`): Windows cleared the
  halts of 0x83/0x03/0x84 at RNDIS start (it does that on every RNDIS start; 0219n shows it too),
  0222 ended + Clear-Stalled + restarted each, and the USB console went silent right after the
  third; SSH still accepted a connect, scp of the 67 MB tar.gz died after 57 s. **0223**
  (`build/make-0223.py`, local c0a8c0a, published 37df94c, kernel CI 43069750815): halt clear =
  Clear Stall only (Linux 4.14 dwc3; modern Linux waits for the End Transfer event first), set =
  Set Stall; failed-TX-start fix and TX watchdog kept. Image 0223n queued by finish-image2.
- 0223n (kernel CI 43069750815, booted 17:52:55 UTC, `a618-0223n-device/live-20261111T175255Z.log`):
  same as 0222n: console silent right after "clear halt of endpoint 0x84" at the RNDIS start, SSH
  gone. So any DWC3 command on those endpoints at that moment wedges it. **0224** (`make-0224.py`
  via `gen-make-0224.py`, local 5a3e375, worktree 529b7de): halt requests acknowledged only again
  (as up to 0219), failed-TX-start fix and 2 s TX watchdog kept. Pushed later (529b7de, kernel CI
  43073834597; 0224n chain + `install-serotonin-0224n.ps1` queued). First try failed: at ~18:00 UTC the PC
  could not open any outside connection (git: "getaddrinfo() thread failed to start", Python
  WinError 10013, TCP to 1.1.1.1:443 fails while DNS answers; same with the sandbox off).
  Push 529b7de, then dispatch and run `finish-image2.sh 0224n ... "ue0 TX stuck for 2 s"`
  (SWEET_SRGB=1 SWEET_USBNET=1), then `build/install-serotonin-0223n.ps1` adapted to 0224n.
- 0224n (booted 18:25:57 UTC, `a618-0224n-device/live-20261111T182557Z.log`) died the same way
  right after the halt clears although they were only acknowledged, so the halt handling was
  never the cause. Common to 0222/0223/0224: 0222's TX watchdog (End Transfer, then the next Start
  Transfer 100 us later, with Windows not reading during its pipe resets; DWC3 needs the End
  Transfer event first). **0225** (`make-0225.py` via `gen-make-0225.py`, local 9e3e826, published
  72cd2fc, kernel CI 43078579191): the watchdog only logs (`ue0 TX pending for 2 s`); the
  failed-TX-start fix stays. Chain: finish-image2 0225n, then `build/install-after-0225n.ps1`
  (Serotonin + `jb/sweet-libkrw0-plugin-stub_1.0_iphoneos-arm.deb`, made by
  `build/mk-krw-stub-deb.py`: empty package, Provides libkrw0-plugin).
- 0225n (booted 18:45:05 UTC, `a618-0225n-device/live-20261111T184505Z.log`): same end. SSH
  answered after the halt clears, scp ran ~52 s and ended "Connection reset by peer". No failed
  endpoint command and no "TX start failed" in any log (0219n..0225n), so the 0222..0225 paths never
  ran: the real pattern, in 0218n, 0219n and 0225n alike, is two RNDIS SET (76 bytes, multicast list
  OID 0x01010103; Windows sends hundreds) with NO GET_ENCAPSULATED_RESPONSE between them, i.e.
  Windows never got RESPONSE_AVAILABLE or the answer for the first; it then clears the halts of
  0x83/0x03/0x84. On 0219n Windows followed with a port reset + re-enumeration and 0219's bus-reset
  recovery brought the link back; on 0222n..0225n nothing more reached the console. Windows
  configures a Hyper-V VMS_MP port each time the RNDIS adapter appears (Kernel-PnP 400/410), which
  may be why the multicast list changes so often. Next: log every RNDIS command id/type, each
  answer queued/read and each notification started/completed (rate-limited) to find where it is
  lost; 0222..0225's watchdog/halt changes are harmless but did not help.
- **Owner, ~19:00 UTC, fed up: back to 0219n, no more kernel builds for the USB link for now.**
  `build/back-to-0219n-and-install.ps1` boots 0219n when the phone is in recovery/fastboot, then
  `build/copy-in-pieces.ps1` (5 MB pieces, each retried until the link is back, sha256 checked on
  the phone) copies serotonin.tar.gz, installs it into /Applications and dpkg -i's the libkrw0
  stub. 0222..0225 stay in the series (harmless) but the phone runs 0219n.
- **0219n again (booted 18:52 UTC, `a618-0219n-device/live-20261111T185217Z.log`): the console died
  at the same spot (right after the halt clears at RNDIS start, 18:53:04 UTC)**, so 0222..0225 were
  not regressions. Difference from the first 0219n session (which ran for hours): ICS was switched
  on only after that boot; on every later boot ICS was already on when the adapter appeared.
  The network itself outlived the console for ~4 min: `copy-in-pieces.ps1` (fixed: pieces go to
  /var/mobile/Documents/NAME.pNNN, no remote folder) got 3 of 13 pieces through, then the link
  dropped at 18:57 and did not come back without a replug.
- **Serotonin installed (2026-11-11 19:08 UTC)** in /Applications/Def1nit3lyN0tAJa1lbr3akTool.app,
  uicache 0. Getting it there: the phone has GNU tar 1.35 but NO gzip (a .tar.gz fails with "gzip:
  Cannot exec"); the 169 MB prefix of serotonin.tar left by the first failed scp matched the local
  file (sha256 of the prefix), so only the 13 MB tail went over (copy-in-pieces), appended, whole
  tar sha256 d608f8ec... checked, `tar -xf`. During the copy iOS restarted itself (Apple logo; a
  spindump ran just before, so a watchdog-detected hang, kernel kept running) and the link needed
  one replug. **libkrw0 stub installed** (dpkg 0), `apt-get check` clean now.
- apt on the phone: libkrw0 (from the palera1n Procursus bootstrap) depends on the virtual
  libkrw0-plugin, which palera1n's own packages provide on real iPhones; we never had one, so apt
  refuses to install anything. Option offered to the owner: a stub package that Provides
  libkrw0-plugin (no kernel r/w), or later a real plugin backed by this kernel.
- **USB internet WORKS (0219n, booted 16:27 UTC, `a618-0219n-device`).** Windows: "Ethernet 4"
  (Remote NDIS #4, 480 Mbps); the owner turned on ICS from "Беспроводная сеть"; owner: "работает
  все". sshd answers on 192.168.137.2 ports 22 and 2222 (root password alpine from jbsetup). Owner
  dropped Wi-Fi and sound for now ("будем по кабелю работать"). IPA install advice given: AppSync
  Unified (repo https://cydia.akemi.ai/) + Filza, or unpack into /Applications + uicache over SSH;
  App Store IPAs must be decrypted.
- **0220n failed and brightness is dropped (owner, ~16:30 UTC).** 0220n (kernel CI 43053484110,
  booted 16:13:55 UTC from recovery with `a618-0220n-device/boot.py`, log
  `live-20261111T161355Z.log`): AppleARMBacklight published (DSI0 ctrl 0x1f7 status 0x2008),
  backboardd matched it, "display on", three frames, then the panel showed grey with blue stripes
  and the phone died; no "panel level" line reached the PC (the USB log loses its tail when the
  phone dies). Most likely the first DCS command: its buffer came from IOBufferMemoryDescriptor in
  XNU RAM (>= 0xb0000000) while the DSI command DMA reads through the display's apps-SMMU stream
  (mdss_mdp iommus <0x800 0x440>), which ABL set up for cont_splash_region (0x9c000000, 0x1700000,
  outside XNU RAM) only; or the command landed mid-frame (video mode + DSC). Not proven.
  `build/make-0221.py` (dry run: buffer in the splash tail 0x9d6fc000, logs apps SMMU SMR/S2CR/bank
  for 0x800/0x801, DSI0 registers, video-engine idle sampling) was written but never built.
  0220 is reverted (local 66c88c9, published 0e2e1fb). 0219's USB recovery WORKED in the 0220n log:
  `bus reset: transfers ended, SETUP armed again`, RNDIS re-initialised (multicast-list SETs are
  OID 0x01010103). Best image now: **0219n** (kernel 0217+0218+0219, CI 43032319438, built in
  `a618-0219n-device`); the phone runs 0218n (booted again after 0220n).
- Hardware for the next features (stock DT): Wi-Fi = qcom,icnss@18800000 (WCN3990, MSA fixed region,
  firmware in the modem) like the K20 Pro port (ath10k SNOC, MPSS PAS); audio = ADSP (APR) +
  bolero (va/tx/rx/wsa macros) + WCD937x on SoundWire (+ wsa881x nodes, fsa4480), sound card
  sm6150; the K20 uses WCD9340 on SLIMbus, HackiOS redwood is closer for audio. Partition backups
  have modemst1/2, fsg, fsc (the NV snapshot raphael's Wi-Fi needs); the modem partition (MPSS,
  wlanmdsp, BDF, ADSP firmware) still has to be read from the phone (read-only).
- **Owner decision (2026-11-11 ~16:15 UTC): smoothness work is shelved** ("у него железом мощнее...
  забей на плавность": the K20 Pro port runs on an Adreno 640 and four big cores). glthread is
  dropped. Order now: brightness + USB internet (0220n), flashlight, Wi-Fi without the PC, sound.

### 2026-11-11: 0216n result, 0217 (both A76), 0218 (RNDIS answer length)

- 0216n (kernel CI 43025343528, compact 43027427928, booted 13:16:48 UTC, `build/a618-0216n-device/
  live-20261111T131544Z.log`; first boot try failed because `boot.py` asserted sweetusb=3, fixed in
  `build/boot-a618-0181.py`): Windows now sends RNDIS INITIALIZE (24 bytes) and a 28-byte QUERY, reads
  both answers (GET_ENCAPSULATED_RESPONSE wLength 4096), then stops; MI_00 still Code 10. Console on
  MI_02 (COM16) works. Cause (inferred from the lengths, OID not logged): the OID_GEN_SUPPORTED_LIST
  answer was 24 + 26 * 4 = 128 bytes, two whole EP0 packets shorter than wLength, and EP0 never sends
  a zero-length packet. **0218** (`build/make-0218.py`, local 27d8697): OID_GEN_VENDOR_DRIVER_VERSION
  added (27 OIDs, 132 bytes, as Linux's list has it) and any other such answer padded by one byte.
- **0217** (`build/make-0217.py`, local 3fcbdf6): the GPU submitting threads alternate between A76
  cores 7 and 6 (0215n had all four of backboardd's bound to core 7); log `GPU thread N of PROC bound
  to A76 core C`. Owner asked for "both fast cores".
- Published 9405446 (0216 + 0217 + 0218), kernel CI 43028250140 (the 0217-only run 43027626879 was
  cancelled). Image 0218n (SWEET_SRGB=1, SWEET_USBNET=1, wfi=0) by finish-image2, marker
  `bound to A76 core %u`, boots at the next recovery (`build/a618-0218n-device/finish.log`).
- PC internet is on the "Беспроводная сеть" adapter; ICS must be turned on there by the owner
  (Sharing tab, share to the RNDIS adapter), which gives the RNDIS side 192.168.137.1.

### 2026-11-11: jailbroken root flashed; RNDIS needs to come first (0216)

- **userdata now holds the jailbroken root** (owner's "Да, шей", 12:44 UTC): `build/flash-jb-root.ps1
  -BootVersion 0215n` (now also starts from fastboot; fastboot's stderr no longer aborts it under
  PowerShell 5.1). Hash, product sweet and userdata size 0x38405FB000 checked; 24 sparse chunks OKAY in
  377 s; 0215n booted (`build/a618-0215n-device/live-20261111T125046Z.log`, `flash.log`). SpringBoard
  and the GPU renderer up, no panic. Whether jbsetup/Sileo finished is not visible on the console
  (its log is /private/var/sweet-jb/jbsetup.log); ask the owner.
- 0215n RNDIS: Windows enumerated 1209:0003, usbser on MI_00 (COM15) works, but MI_02 (wceisvista.inf,
  usbrndis6) failed with Code 10 / STATUS_UNSUCCESSFUL (Kernel-PnP 411) and the phone saw no class
  request at all (no SEND_ENCAPSULATED_COMMAND). Guess (not proven): Windows' RNDIS driver wants its
  function at interface 0, as on Android tethering. **0216** (`build/make-0216.py`, local ca126d8,
  published ad8a960, kernel CI 43025343528): RNDIS on interfaces 0/1, ACM console on 2/3, PID
  1209:0004; local compile shows no new diagnostics. `read-sweet-usb-0181.ps1` accepts PID_0004&MI_02.
  Image 0216n (SWEET_SRGB=1, SWEET_USBNET=1, wfi=0) is queued by finish-image2 (`a618-0216n-device/
  finish.log`), boots at the next recovery.
- 0215n frames (299 samples, with first-boot jailbreak work): median 7.9 ms, p90 18.4 ms, 45/299 over
  16.7 ms; 2.4 ms a frame in GL calls, 8.0 ms outside them. The renderer's "frames ended on big cores
  N, little M" comes from topaz and reads TPIDR_EL0 < 4 as big: it is meaningless here (0203 binds the
  submitting threads to A76 core 7 and the log shows the binding). CPUFREQ: A55 1804, A76 2304 MHz.
  Smoothness ideas: spread bound render threads over both A76 (6 and 7; today every bound thread
  shares core 7), test wfi=1 on this kernel (0214) against heat throttling.

### 2026-11-11: 0215 asynchronous submission; jailbroken root being packed

- **0215 on the phone, booted 12:30:30 UTC** (`build/a618-0215-device/live-20261111T123030Z.log`).
  Owner: "super smooth". The image chain failed once more after CI: `build/prepare-a618-0181-image.py`
  also asserted the old dyld policy string; changed to `dyld policy for %s input=` and the image was
  rebuilt by hand (`prepare-kernel-renderer.py 0215 d89c963 43018335227 43011732196 43020615305
  13855430225 0215 15cf9f6`, SWEET_SRGB=1, wfi=0, sweetusb=3, boot image SHA-256 f03d63af...).
  frame-stats over the first 157 samples, 0215 vs 0212b: frame median 3.9 ms vs 14.8 ms, p90 18.8 vs
  27.5 ms; handing on median 0.8 vs 7.0 ms; copy out median 1.0 vs 3.3 ms; frames with 60+ draws median
  15.8 vs 25.2 ms; frames over 16.7 ms 29/157 vs 62/155; GL time outside calls 8.2 vs 16.2 ms a frame;
  submit field median 0.42 vs 1.43 ms. No panic, no crash, no `GPU stopped completing work`, no
  `submit disabled`; `fence waits mean` not printed yet in the first 4 minutes.
- Image 0215n (same kernel, renderer and compact, SWEET_USBNET=1 so sweetusb=4, otherwise as 0215;
  boot image SHA-256 54e7ab33...) is built in `build/a618-0215n-device` for the jailbroken root:
  `flash-jb-root.ps1 -BootVersion 0215n`. Not flashed yet; the owner confirms the flash first.

- 0215 (local 4ad3840, published ee4b106, kernel CI 43014173346; includes 0213, 0214): the ring writer
  waits only for ring room (RPTR outside the words to write), publishes WPTR and returns; completion =
  fill page word 16 written by CACHE_FLUSH_TS (`a618_renderer.done`); `sweet_a618_render_wait(fence,
  max_ms)` spins 10 us / 8 ms then sleeps, checks a618_cp_guard every 1 ms, poisons when no fence
  completes for 500 ms (logs `GPU stopped completing work`, `fence waits mean`); SweetAdreno: per-BO
  `fence` set at submit, MSM_WAIT_FENCE and MSM_GEM_CPU_PREP wait (absolute CLOCK_MONOTONIC timeouts via
  mach_continuous_time, capped 3 s; NOSYNC -> busy), closed BOs still in use go to `zombies` (1024) and
  are released by reapLocked at submit / wait; client close waits for the last submitted fence.
  Local compile: 0 errors, no new warnings; preflight passes.
- Kernel CI 43014173346 (ee4b106) FAILED in "Verify required SWEET GPU patch": the kernel no longer
  has `SWEET CA: backboardd dyld policy input=` because 0213 renamed it to `dyld policy for %s input=`
  (first CI kernel with 0213). Fixed the workflow check (local 2010e8e, published 15cf9f6); every other
  required string was checked against 0201-0215 and none is removed. Kernel CI 43018335227 (15cf9f6).
- Image 0215 = kernel 43018335227 + renderer 43011732196 (d89c963: Mesa cache 96/16 MiB + sweetnet),
  SWEET_SRGB=1, wfi=0, sweetusb=3; `build/a618-0215-device/finish.log` (the failed first try is
  `finish-ee4b106-failed.log`), boots at the next recovery.
- Jailbroken root: renderer 43011732196 passed; sweetnet fetched (69632 B,
  `artifacts/sweet-renderer-43011732196/sweet/bin/sweetnet`); `mk-jb-root.sh` finished its edits and
  wrote `work/jb-root/ios16-root-sweet-k6a-20H392-jb1.simg` (12259629736 B, sparse SHA-256
  013bcd6c5b9bd57f958e7ef2d76ee6e3262a6c176a1662adef171aeee098c469; fsck clean). Read-only check of the raw
  image: sweetnet, ellekit/loader, TweakInject.dylib, /bin/sh, prep_bootstrap.sh, jbsetup/respring, apt
  source, the GPU root files (sweet/lib loader, usr/libexec/real/backboardd) and dpkg present; 5 jobs in
  launchd.plist; SpringBoard env has DYLD_INSERT_LIBRARIES. `build/flash-jb-root.ps1 -BootVersion V`
  flashes it (checks hash, single sweet target, product, userdata size 0x38405FB000) and boots V.
  Not flashed yet: waiting for 0215 to prove itself first.

### 2026-11-11: 0212b on the phone; where a frame goes now; Vulkan question

- 0212b booted 11:29:39 UTC (`build/a618-0212b-device/live-20261111T112928Z.log`). Owner: a bit smoother in
  animations, still wants more. At 2200 frames: 19.4 ms a frame with 81 draws on average; 8.2 ms handing
  commands on (synchronous GPU wait in glFlush), 4.6 ms the panel blit, 1.4 ms textures of IOSurfaces;
  glTexImage2D 2.3 ms a frame (0208: 9.7, 0207: 1.6); no pool or GL memory errors, no crashes.
- Owner asked about Vulkan instead of OpenGL. CoreAnimation on iOS 16 has only Metal and its legacy
  OpenGL ES backends; Vulkan (Mesa turnip) would need a Metal implementation on top of it (none exists
  here; HakiOS notes only a shader compiler). The measured cost is the synchronous submission, which
  Vulkan would not remove. Next: asynchronous submit with fences (Topaz/K20 style).

### 2026-11-11: 0212 black screen: GPU guards also need idle off; 0212b restores; 0214

- 0212 (kernel CI 43009473506, renderer 43009462022, SWEET_WFI=1) booted 11:24 UTC: GMU up, renderer
  armed, `SWEET IDLE: CPU idle enabled`, then the first submission `SWEET CA: submit disabled rc=-3`,
  backboardd SIGSEGV, black screen (owner). Cause (code): a618_cp_guard -> GMU health -> post_check ->
  boot_check(s, 3) returned -1 when idle_enable was TRUE.
- 0212b = the same kernel and renderer with wfi=0 (no idle): built directly with prepare-kernel-renderer
  (compact 43011414062, artifact 13850247584), image SHA-256 22f0491e...; boot-when-recovery started.
- 0214 (local 958b151, published 276983e, kernel CI 43012234354; includes 0213): boot_check ignores
  idle_enable at phase 3 (run time); phases 0..2 still require it off. Not tested yet. This kernel run
  replaced the 0213-only run 43011744862 (cancelled by concurrency).

### 2026-11-11: jailbreak root in preparation (owner approved the userdata reflash)

- Owner approved: reflash userdata (losing iOS data since gpu0177), deleting the six old root images
  (001, repair, mg-timeout, mg-nowait, apps32-experimental, gpu0174 .simg; deleted, 75 GB free after),
  and downloading the jailbreak packages. Kept: `artifacts/gpu0177/...gpu0177.simg` (the root on the
  phone, sparse SHA-256 aefd7d64...) and the partition backups.
- Downloads in `D:/ios-sweet/jb/downloads` (SHA256SUMS there): palera1n bootstrap-1800.tar.zst
  (20482240 B), ElleKit 1.2, Sileo 2.5.1, NewTerm 3.0~beta1, libpcapa 1.10.4, network-cmds 669,
  OpenSSH 9.7p1-1 client/server/sftp-server. Sileo repo list `D:/ios-sweet/jb/repos.sources` (S9's).
- `build/mk-jb-root.sh` (WSL root) + `build/jb-launchd-sweet.py`: from gpu0177 -> raw
  `work/jb-root/jb-root.img` -> bootstrap + ElleKit data + debs to /private/var/sweet-jb/debs +
  `/usr/libexec/sweetnet` + first-boot `sweet-jbsetup` (prep_bootstrap, root/mobile password `alpine`,
  dpkg, uicache, respring) + `sweet-respring` + launchd jobs (com.sweet.jbsetup/sweetnet/ellekit/
  respring, com.openssh.sshd) + SpringBoard DYLD_INSERT_LIBRARIES=/usr/lib/TweakInject.dylib + Sileo
  repos + BTAudioHALPlugin moved to /Library/Audio/Plug-Ins/HAL.disabled -> fsck -> img2simg
  `work/jb-root/ios16-root-sweet-k6a-20H392-jb1.simg`. Not run yet (needs sweetnet).
- 0213 (local e36b2e4): kernel no longer injects its loader into SpringBoard unless sweetsbloader=1;
  AMFI 0x5a allows DYLD variables for every 64-bit launchd child (logs `dyld policy for NAME`).
  sweetnet (local b1edb72, `userland/jb/sweet-net.c`, from S9's s9net, 192.168.137.2 via .1, DNS .1 /
  1.1.1.1 / 8.8.8.8) builds with the renderer; the workflow now uploads `sweet/bin/sweetnet`.
  `build/chain-0213.sh` publishes both after image 0212 and dispatches renderer + kernel
  (`build/runs-0213.txt`). Compile of 0213 files: no new errors.

### 2026-11-11: 0209 lost the GPU (wfi=1 refused by the bring-up); 0212; 0211 RNDIS

- 0209 (kernel CI 43006713818 = 0209+0210, image 5e07ebf9..., SWEET_WFI=1) booted 11:04:46 UTC:
  `SWEET IDLE: CPU idle enabled after GPU start (wfi=1)` but `SWEET GMU BOOT: requires jtag=1 wfi=0`:
  `sweet_gpu_probe.c` refused the GMU with wfi=1, no renderer armed, backboardd `Adreno service
  unavailable`, CPU rendering. Owner: "as if switched to the CPU". (The idle flip itself worked.)
- 0212 (local 447dd73, published 5159485): both probe checks take wfi 0 or 1; jtag=1 (idle_enable FALSE)
  still keeps CPU idle off until bsd_init. Preflight passes. Kernel CI 43009473506, renderer CI
  43009462022 (renderer = Mesa BO cache 96/16 MiB). Image 0212: SWEET_SRGB=1 SWEET_WFI=1, sweetusb=3.
- 0211 (local 9828b3b, published in df32d5f; in the 0212 kernel): `sweetusb=4` = composite device,
  ACM console (IAD 02/02/01, interfaces 0/1, endpoints 0x82/0x81/0x01, PID 1209:0003) + RNDIS (IAD
  E0/01/03, interfaces 2/3, endpoints 0x84/0x83/0x03, TX FIFOs 3/4), ue0 192.168.137.2/24 for Windows
  ICS. RNDIS INIT/QUERY/SET/RESET/KEEPALIVE/HALT, 44-byte packet headers, host MAC 02:00:5e:77:ee:01
  as the adapter address. Logs `SWEET USB: RNDIS message ..`, `packet filter ..`, `TX FIFOs ..`.
  `prepare-kernel-renderer.py` SWEET_USBNET=1 swaps sweetusb=3 -> 4; `read-sweet-usb-0181.ps1` now also
  finds PID_0003&MI_00. Compile: no new errors. Not booted yet. No default route/DNS: iOS needs a
  configd service for ue0 (S9's `s9net`), to go into the jailbreak root.

### 2026-11-11: owner asks for Wi-Fi (password), internet through the PC, and the jailbreak

- Internet through the PC: we already have USB CDC-ECM from upstream (0075-0077, `sweetusb=2`, phone
  192.168.7.2, host 192.168.7.1, kernel log on UDP 5140, `tools/sweet-usbnet.sh` for a Linux host). Our
  images use `sweetusb=3` (ACM console, read as COM12). Windows 10 has no in-box CDC-ECM host driver
  (RNDIS yes; NCM uncertain on 19045), so this needs RNDIS/NCM on the phone or usbipd-win into WSL.
  Not yet tested on sweet_k6a.
- Wi-Fi: the K20 Pro stack is public in `oosexgang/hakios-xnu-kernel` (pushed 2026-11-10):
  `drivers/modem/hakios.mpss.c` (MPSS boot: the WCN399x firmware runs on the modem), `drivers/wifi/`
  (`hakios.wlfw.c` QMI WLFW, `hakios.lx.c` + `wifi/lx/` LinuxKPI around Linux ath10k SNOC,
  `hakios.sta.c` + `lx_wpa.c` WPA2/WPA3 in the kernel, `hakios.apple80211.c` answering wifid). Docs saved
  in `research/hakios-wifi-docs/`. Their chain: MPSS signed load (PAS 4), SMEM, SMP2P, GLINK, QRTR,
  RMTFS, TFTP, PD mapper, PDR, DMS, BDF, MSA/SMMU, PMIC supplies; then SNOC CE IRQs/NAPI/HTC/WMI.
  sweet_k6a (sdmmagpie) is the same WCN399x/ICNSS/MPSS architecture as the K20 (SM8150), so this is the
  base to port; register addresses, GPIOs, supplies, BDF and firmware must come from our own FDT and
  partitions (modem partition firmware not yet extracted; NV backups in backup/sweet-k6a-20261027).
  Multi-step work; the owner was told so.

### 2026-11-11: owner on 0208; jailbreak wish

- Owner on 0208: no freezes any more; scrolling smooth; lag when opening apps. (Matches the measured BO
  creation cost; next: Mesa BO cache 96/16 MiB (local e96ecb9), then async submit.)
- Owner wants a jailbreak with tweaks. syncmodz/ios-s9 has a working layer for the same iOS 16.7.16
  iPhone X userland (`s9/jailbreak/README.md`, `fetch-jailbreak.sh`, `tools/prep-ios6.sh`,
  `tools/jb-launchd.py`, `tools/trim-daemons.py`, copies in `build/ios-s9/`): palera1n Procursus rootful
  bootstrap 1800, ElleKit (pspawn loaded into launchd; DYLD_INSERT_LIBRARIES on SpringBoard), Sileo,
  NewTerm, OpenSSH, PreferenceLoader, a one-respring-per-boot job, ~82 crash-looping daemons trimmed.
  They build it into the root image offline and flash it; Sileo needs a network (theirs: USB CDC-ECM +
  `s9net` publishing it to configd). Here: putting it on the root means either rebuilding and reflashing
  userdata (destructive, needs the owner's explicit approval per AGENTS.md) or a careful in-place write;
  without Wi-Fi or USB networking Sileo cannot download, so tweaks would be preinstalled.

### 2026-11-11: 0208 result: no more pool exhaustion; BO creation now costs more

- 0208 (kernel CI 43004542261, renderer 43002130748, image 0eb6aa2e...) booted 10:48 UTC,
  `build/a618-0208-device/live-20261111T104752Z.log`. Observed: 1024 window BOs made by frame ~600,
  442 live using 205 MB; `no contiguous range` 0, GL out-of-memory 0, BO pressure retries 0, GL errors 0
  (0207: 4, 0205: 47), no SpringBoard/backboardd crash, TLB invalidated x8 without fault.
- Cost: at 600 frames glTexImage2D 9.7 ms a frame and 'making textures of IOSurfaces' 6.7 ms
  (0207 at 1400: 1.6 and 1.0); frame 29.9 ms average (boot period, not matched). Likely each new BO now
  pays a kernel allocation + WC attribute change + zeroing + 4 KiB leaf writes, and Mesa reuses little
  because GPT's bo-pressure patch caps its BO cache at 24/8 MiB.
- Local 62565da (see git log, not yet published: wait until image 0209 is built so its compact job keeps
  its head): `mesa-sweet-bo-pressure.patch` cache limit 96/16 MiB. Topaz/K20 also keeps freed buffers in
  the kernel (gpu_kept, 160 MB, 60 s); a kernel-side keep cache is the next step if Mesa's is not enough.
- Kernel CI 43006713818 (published 96776d2 = 0209 + 0210) is building; `build/chain-0209.sh` makes image
  0209 (SWEET_WFI=1) with renderer 43002130748 and boots it at the next recovery.

### 2026-11-11: syncmodz/ios-s9 (Galaxy S9 fork of upstream ios-sweet) and patch 0210

- Read via the GitHub API (fetched patches in `build/ios-s9/`, tree `build/ios-s9-tree.txt`,
  README `build/ios-s9-README.md`). A fork of dipa-studio/ios-sweet for the SDM845 Galaxy S9, last push
  2026-10-25. CPU rendering only (GPU study just started), no Wi-Fi/BT/cellular/camera; USB network.
  Useful for us:
  - their 0099: skip the L1 set/way clean before every idle WFI (cores keep power) -> our 0210;
  - their 0092: SweetKeyStore wrap/unwrap (sel 10/11) answered 'unsupported' made securityd retry
    ~300/s (80 % of a core); we see securityd sel 10 210 times in 14 min, not a storm, and log every AKS
    call (5596 lines in 14 min on 0205; their note: logging every call cost CPU);
  - their 0092/0094: render and UI threads on fast cores, the touch thread on a slow one;
  - @2x XR canvas (828x1792) instead of @3x: 46 % fewer pixels (a GPU fill-rate option, changes the UI).
- 0210 (local f7722ee, not yet published): `osfmk/arm64/cpu.c` cpu_idle skips platform_cache_idle_enter
  on SWEET unless boot-arg sweetidleflush=1. Compile: 0 errors before and after. `build/chain-0209.sh`
  now cherry-picks 0209 and 0210 together after image 0208 is built.

### Owner's feature list after smoothness and heat (2026-11-11)

Wi-Fi, flashlight, brightness, sound, camera, cellular. Reference: the K20 Pro port
(`research/hackios-k20-raphael/ru_notes.md`, table "Что работает и чего нет"): Wi-Fi (ath10k, Safari
loads pages), sound through the ADSP (`adsp=1 sound=N`), camera in Camera.app (`cam=5`), flashlight
(`torch=N`, PM8350C LED over SPMI, MobileGestalt `camera-flash` from /product/camera) work there;
cellular and Bluetooth are "not working" in our copy of their notes, but the owner saw cellular
working on the K20 port in a TikTok video (no public code for it; our copy may also be older than
their current repo: check for a newer one before starting cellular). Brightness is not in their table. Proposed order:
brightness and flashlight (PMIC/panel registers, small), Wi-Fi (WCN39xx firmware + QMI, K20 code),
sound (ADSP), camera (biggest), cellular last (unsolved on the K20 too). sweet_k6a's SoC (sdmmagpie
family) differs from the K20's SM8150, so register details must come from our own device tree dumps.

### 2026-11-11: idle heat: cores never idle; 0209 enables WFI after GPU start

- Owner: the phone gets warm while lying idle. Causes found in code and logs:
  - Boot flags `jtag=1 wfi=0`. jtag=1 sets idle_enable FALSE (osfmk/arm64/cpu.c), so cpu_idle never runs:
    all 8 cores spin in the idle thread. The GMU/RPMh GPU bring-up guards require idle_enable FALSE
    (`sweet_gpu_gmu_start.cpp` boot_check and line 252, `sweet_rpmh_gpu_bw.inc`), so it cannot simply be
    dropped. GPU bring-up finishes (`renderer armed`) before bsd_init's SWEET hooks.
  - AegirPoster (Astronomy poster) crash loop: 94 crashes in 14 min on 0205 (sig 6), each a launch +
    ReportCrash. Not addressed yet.
  - backboardd keeps drawing at idle (0205: 13680 frames in ~14 min, about 16 fps) and the GPU is held
    at level 7 (800 MHz) with no GPU idle/power collapse. Not addressed yet.
- 0209 (local 52f8fc6, not yet published: waits for image 0208 so 0208's compact job runs at its own head):
  bsd_init, after sweet_cpufreq_start, sets idle_enable TRUE when boot-arg wfi != 0 and logs
  `SWEET IDLE: CPU idle enabled after GPU start` / `unchanged`. WFI is clock gating only (no PSCI
  suspend). SweetCPU registers no processor_idle callback; SGIs and the timer IRQ are verified, so idle
  cores wake. platform_cache_idle_enter (non-Apple caches.c) cleans L1 to PoU at each idle entry.
- `build/prepare-kernel-renderer.py`: SWEET_WFI=1 swaps `wfi=0` for `wfi=1` (same length).
  `build/chain-0209.sh` (log `build/chain-0209.log`) publishes 0209, dispatches the kernel and builds
  image 0209 (SWEET_SRGB=1 SWEET_WFI=1, renderer 43002130748), then boots it at the next recovery.
- Local compile of bsd_init.c base vs 0209: same 22 environment errors, none new.

### 2026-11-11: 0208 GPU buffers from system memory (built, booting)

- Owner on 0207g (GMEM allowed): feels the same as before. GMEM stays allowed in the renderer.
- 0208 (local 6bde9c3, published 67a0d16, kernel CI 43004542261): GEM_NEW first makes a write-combined
  IOBufferMemoryDescriptor of its own (SweetAdrenoBO::initBacking, user mappings forced WC as for the
  pool), zeroes it, enters its 4 KiB pages into the 0206/0207 window (shared with imported surfaces,
  same stale-VA + TLBIASID rule) and falls back to the pinned pool only on failure. GEM close clears the
  leaves and marks the range stale. `sweet_a618_render_submit` accepts IBs in the pool or the window.
  Logs `SWEET CA: window BO .. KB at GPU VA ..; N window BOs, M MB; K made` (first 8, then every 1024)
  and `window BO of .. KB refused (...)`. Local compile 0 errors; preflight passes.
- Image 0208 = that kernel + renderer 43002130748 (GMEM allowed; disk copied from 0207g), SWEET_SRGB=1.
- Check: no `BO pool has no contiguous range`, no GL error 0x505, no backboardd crash; window MB in use.

### 2026-11-11: 0207g result; the 256 MiB pinned pool runs out in every boot

- 0207g (renderer CI 43002130748, image booted 10:22 UTC, `build/a618-0207g-device/live-20261111T102158Z.log`):
  `FD_MESA_DEBUG cleared: GMEM rendering allowed` logged; no GPU fault, no submit disabled. backboardd
  crashed at frame ~150 (FAR 0x14 after `SWEET BO: pressure retry size=4194304 recovered=0`), then
  glFlush/glTexImage2D/glDrawElements error 0x505 (GL_OUT_OF_MEMORY). Too little data to judge GMEM's
  speed (85 sampled frames, 1 touch).
- Pool exhaustion is not new: every recent boot hits `BO pool has no contiguous range` (8 = the log cap)
  between frames 100 and 280, with 19..29 GL out-of-memory errors; max in_use 14809..15830 of 16384
  units. 0206 and 0207g lost backboardd to it (screen freezes while it restarts). Fragmentation matters:
  `pages=768 in_use=14711/16384` failed with 1673 units free.
- Likely the freezes the owner reports. Proposed fix (as Topaz/K20): GEM_NEW BOs from wired system
  memory (write-combined IOBufferMemoryDescriptor), entered page by page into GPU VA (the 0206 import
  window machinery: no physical contiguity, TLB invalidation before VA reuse), instead of contiguous
  runs of the fixed pinned pool. IBs would then live outside the pool too: the IB range check in
  `sweet_a618_render_submit` must accept the window.

### 2026-11-11: 0207g tries GMEM (tiled) rendering

- `userland/gpu/eagl-gmem.patch` (local 785eb14, published c9b94f8, renderer CI 43002130748): EAGL's
  constructor unsets FD_MESA_DEBUG (the root's loader sets `sysmem` before loading EAGL) and logs
  `redwood-gl: FD_MESA_DEBUG cleared: GMEM rendering allowed`. The renderer disk holds only EAGL and
  OSMesa; the loader lives on the root, so changing the loader source alone would not deploy.
- Image 0207g = kernel 0207 (run 42997584422) + this renderer, SWEET_SRGB=1,
  `build/a618-0207g-device/finish.log`. Risk: GPU hang or garbage if GMEM setup is wrong; fall back
  to image 0207.

### 2026-11-11: 0207: zero-copy works; the GPU's synchronous work is now the bulk of a frame

- 0207 (kernel CI 42997584422, renderer 42993564102, SWEET_SRGB=1) booted 10:08 UTC,
  `build/a618-0207-device/live-20261111T100813Z.log`. Observed: `IOSurface import window at GPU VA
  60000000, 512 MiB`, `read in place` (surface 552, 1125x2436, 2744 pages, imported again and again
  at new VAs as CA recreates its texture), `SMMU TLB invalidated before import space is reused` x3,
  no GPU fault, no submit disabled, no SpringBoard/backboardd crash in the first ~2000 frames.
  Summary at 2000 frames: 169 IOSurfaces were the textures' memory, 438 still copied (non-BGRA,
  unaligned rows, wrapped memory); GL errors 4 (0205: 47 at 1400 frames). Owner: "maybe better".
- Frame at 2000 frames: 19.6 ms average with 94 draws (0205: 14.3 ms with 66 draws; per draw about
  the same). Of it: 8.0 ms handing commands on (synchronous GPU wait), 4.2 ms the panel blit, 1.0 ms
  making textures of IOSurfaces (0205: 1.2), the rest CoreAnimation's CPU work. GPU wait mean 1.9 ms
  a submission.
- Remaining big costs, both GPU-side: (1) Mesa runs in sysmem mode always
  (`FD_MESA_DEBUG=sysmem` set by `userland/gpu/sweet-renderer-loader.c` since the first renderer,
  dcbb460, as a precaution; GMEM/tiled rendering was never tried), so every blended draw goes to DRAM;
  (2) submissions are synchronous, so CPU and GPU never overlap (Topaz/K20 submit asynchronously
  with fences and deferred buffer release).

### 2026-11-11: 0206 booted without the import window; 0207 fixes the allocation

- 0206 (kernel CI 42993944945, renderer 42993564102, image SHA-256 e3a0b68a...) booted 09:37:55 UTC,
  `build/a618-0206-device/live-20261111T093745Z.log`. Logged `SWEET CA: IOSurface import window
  unavailable; surfaces stay copied`, `0 IOSurfaces were the textures' memory, 363 had to be copied`.
  So 0206 ran like 0205. Owner: still freezes and lags. backboardd crashed once (pool pressure, as
  before).
- Cause (code): sweet_gpu_memory_create_nc refuses more than GPU_MAX_PAGES = 128 pages; 0206 asked
  for 256 at once. 0207 (local 6bc62fc, published 9575414, kernel CI 42997584422) takes two halves
  of 128. Preflight passes locally; compile 0 errors. Image 0207 = that kernel + renderer 42993564102
  (disk copied from 0206), SWEET_SRGB=1, `build/a618-0207-device/finish.log`.

### 2026-11-11: 0206 zero-copy for shown BGRA IOSurfaces (built, not yet booted)

- What 0205 still copied: 'IOSurface shown' BGRA textures (622 in the census, up to 2048x2955);
  sampled refills of 10962 KB (a full-screen surface) took 8..40 ms before the frame, and the
  renderer added up every shown surface's memory each frame or two to notice changes.
- 0206 (local d20ceb6, published ca4a312; kernel CI 42993578056, renderer CI 42993564102):
  - `bsd/dev/sweet_a618_render_pool.{h,c}`: import window 0x60000000..0x80000000 (L2 256..511,
    256 L3 tables), `sweet_a618_import_{attach,check,set,clear}`; address_space check skips it.
  - `sweet_a618_mapping.inc`: tables attached empty before SID0 install, optional (logs
    `SWEET CA: IOSurface import window at GPU VA 60000000, 512 MiB` or `unavailable`).
  - `sweet_a618_renderer.inc` + `sweet_smmu_context_invalidate` (TLBIASID CB+0x610, TLBSYNC
    +0x7f0/+0x7f4, under the submit lock; failure poisons the renderer).
  - `SweetAdreno.cpp` importSurface: one-plane BGRA, rows % 64 == 0, IOBufferMemoryDescriptor only;
    prepare(), physical pages per 4 KiB, dedup per surface, flush_dcache on import; at submit a
    surface whose seed moved or not cleaned for 16 ms is cleaned; GEM close clears leaves and
    marks them stale; stale space is reused only after one invalidation. Logs `read in place at
    GPU VA`, `imported surfaces cleaned N times`, `SMMU TLB invalidated before import space is
    reused`, `not imported: ...`.
  - Renderer: `eagl-share-textures.patch` (share_targets = 0: drawn-into surfaces unchanged) and
    tools/build-sweet-renderer.sh no longer forces share_surfaces off. glcopy=1 would disable it
    but the 580-byte cmdline has no room.
- Local compile (WSL clang-18, build tree headers, `build/zc-compile.sh`): SweetAdreno.cpp,
  sweet_gpu_gmu_start.cpp (with the .inc files), render_pool.c, address_space.c, smmu_context.c:
  0 errors; a deliberate error is caught.
- Kernel CI 42993578056 failed in the GPU source preflight: the 0206 entry was listed before 0197 in
  tools/verify-gmu-service-patch.py, but 0206 is made on top of 0197's mapping.inc. Moved after it
  (local + published bcc4c57); the preflight passes locally. New kernel CI 42993944945.
- Image (kernel bcc4c57 run 42993944945, renderer ca4a312 run 42993564102): `SWEET_SRGB=1 bash build/finish-image2.sh 0206 ca4a3126... 42993578056 42993564102 ca4a3126...
  "read in place at GPU VA"`, log `build/a618-0206-device/finish.log`.
- Risks: wrong leaves or cache cleaning show as GPU faults (renderer poisoned, frozen picture) or
  stale/garbled textures. Fallback: image 0205 (e70be77b...) boots as before.

### 2026-11-11: 0205 works: BGRA frames go straight to the panel

- Kernel CI 42980632085 passed, image SHA-256 e70be77b35ebee996fd83cd381c20a8ac00d8f31ba094c766f104fcb908ad124
  (SWEET_SRGB=1, renderer 42975170436), booted 07:48:08 UTC, ran until ~08:02 UTC (log
  `build/a618-0205-device/live-20261111T074758Z.log`, 13680 frames, 1085 touch events). Phone was in
  recovery at 09:00; the log has no crash or panic at its end, so why it left is unknown.
- Observed: `SWEET FB: BGRA frame already on the panel` (8 logged), `SWEET DIRECT: frame .. on the
  panel`, crashes SpringBoard 0, backboardd 0, submit disabled 0.
- Frame times (every 20th frame): frames under 40 draws median 4.9 ms (0201: 7.1), 60+ draws median
  22.5 ms (0201: 32.3). 0205 had a much heavier workload (draws median 48 vs 25), so overall medians
  are not comparable. Average over 13600 frames: 14.5 ms a frame, 5.2 ms handing commands on,
  4.0 ms copying out (the panel blit), 1.1 ms making textures of IOSurfaces; glFlush 9.1 ms/frame,
  glTexImage2D 1.4 ms/frame. GPU wait mean 0.9..1.7 ms a submission.
- The Topaz "big/little" counter shows all 13600 frames on cpu >= 4, consistent with the core-7 bind.
- Pool: still 8 `no contiguous range` and 8 BO pressure retries, but no crash this time.
- Next: kernel zero-copy for BGRA IOSurface textures (plan in the 0202 section; BGRA surfaces now
  have 64-byte aligned rows, 4608), then asynchronous submit.

### 2026-11-11: 0204 proves sRGB gives BGRA; 0205 restores the direct panel path

- 0204 (kernel CI 42975181837, renderer CI 42975170436, compact 42979798471, image SHA-256
  688a8b9afea311ac2f26a786f36f5999f3cddd4005d64bd3bffbc908e6613852) booted 07:30:40 UTC,
  `build/a618-0204-device/live-20261111T073029Z.log`. Observed: every 1125x2436 surface is now
  `fmt 0x42475241` (BGRA, bpr 4608), no w30r/b3a8, 'BGRA' attachments, `MobileGestalt caches set
  aside for sRGB=0` (0 renamed: the path did not match; the sRGB answer came anyway),
  `GPU thread bound to A76` x3. Owner: feels like the CPU renderer.
- Cause (read in the code, then seen in the log): `AppleCLCD::present` calls
  `sweet_a618_note_display`/`direct_take` only inside the b3a8 branch, so IS_DISPLAY was false,
  `SWEET DIRECT: frame` 0 times, each frame read back by glReadPixels: copying-out median 20 ms,
  frame median 21.8 ms (0201: 4.3 and 7.4).
- 0205 (local f2d909e, published ab4dab3, kernel CI 42980632085): same check for a full-screen BGRA
  layer; logs `SWEET FB: BGRA frame already on the panel`. Image 0205 = that kernel + renderer
  42975170436 (disk copied from 0204), SWEET_SRGB=1; `build/a618-0205-device/finish.log`. Not booted
  when written.
- Also seen on 0204: backboardd crashed once, FAR 0x14 in OSMesa after `SWEET BO: pressure retry
  size=12582912 recovered=0` and 8 `no contiguous range` lines: the pool still runs out of 12 MB runs
  (old failure, the budget does not count render targets).
- Correction: `accessibility preferences set aside rc=17` (EEXIST). The renames use VFS_RENAME_EXCL,
  so with `.sweet-dark`/`.sweet-bold` present a later rename fails: turning dark mode or Bold Text on
  again would NOT be healed by a reboot, contrary to what the 0201 notes say.

### 2026-11-11: the K20 way is possible: sRGB device tree, BGRA surfaces (in progress)

- Correction of the section below: the K20 Pro port has the same iPhone X identity. Its
  `ru_notes.md` says the loader writes `artwork-display-gamut` = sRGB (the real iPhone X says P3);
  MobileGestalt then answers no HasExtendedColorDisplay and iOS uses BGRA instead of `w30r`/`b3a8`.
  Their zero-copy depends on that. Not yet verified that this also changes backboardd's display
  surfaces here.
- Published cd8fa92 (local same change; includes 0203). Kernel CI 42975181837, renderer CI
  42975170436 (dispatched by REST, not yet finished when written). 0204: bsd_init renames
  `.../SystemGroup/*/Library/Caches/com.apple.MobileGestalt.plist` to `.sweet-p3` once, logs
  `MobileGestalt caches set aside for sRGB=`. `userland/gpu/eagl-bgra-display.patch` +
  `sweet_probe_display`: a full-screen BGRA target also goes straight to the panel.
- Image: `SWEET_SRGB=1 bash build/finish-image2.sh 0204 cd8fa92ba2472f706b9a078dfee5e9d8fefa9957
  42975181837 42975170436 cd8fa92ba2472f706b9a078dfee5e9d8fefa9957 "MobileGestalt caches"`.
  `prepare-a618-0181-image.py` edits the ADT when SWEET_SRGB=1 (P3 -> sRGB, new file
  `sweet-srgb.adt` in the image directory). 0203 was not tested alone.
- Blocker: a new renderer disk needs WSL (`mk-full-renderer-disk.sh`), and WSL is stuck
  (WslService StopPending); needs a PC reboot. Then run the command above.
- Check after boot: `SWEET SURF: ... create ... 1125x2436 fmt` (BGRA 0x42475241 instead of w30r/b3a8),
  `SWEET DIRECT: frame .. on the panel`, `GPU thread bound to A76`, no SpringBoard crash. If it goes
  wrong, boot without SWEET_SRGB (image-only change). After that: kernel zero-copy per the plan below.

### 2026-11-11: 0202 result; 0203; why the K20 zero-copy plan does not fit yet

- 0202 booted 06:21:51 UTC, `build/a618-0202-device/live-20261111T062140Z.log`. Owner: smoother.
  Measured: field submission 1412 us median (0201: 1960), `GPU wait mean 1766 us longest 18110 us`
  over 4096 submissions. So the sleep was only about 0.5 ms a submission; the GPU really is busy
  ~1.8 ms a submission. The claim that sleeps explain the 25..40 ms frames was wrong. Workloads are
  not matched between logs, so frame-time medians are not a clean comparison.
- Averages (0202, 1440 frames, 21 ms a frame): glFlush 9.1 ms (synchronous GPU wait + panel),
  GL calls 5.1 ms; glTexImage2D 3.8 ms a frame; the rest is CoreAnimation's CPU work.
- The eagl.c "big/little" counter is Topaz's (cpu < 4 = big). Here cores 0-5 are A55 and 6-7 A76,
  so that line does not say what it seems to.
- Zero-copy as on the K20 does not hit the real copies here. Full-screen targets are `w30r` and
  `b3a8` (XR10), converted on the CPU (`xr10_upload`, `xr10_readback`; frames 32..60 spent 150+ ms
  in them); textures shown from IOSurfaces are small A008/LA08/RGhA, BGRA only 1 x 1. The kernel
  mapping design below still stands if BGRA or GPU-readable XR10 surfaces become the common case.
- 0203 (local 575d30b, published 09031c7, kernel CI 42974013855): each submitting thread is bound
  to A76 core 7 on first submit (at most four threads); logs `SWEET CA: GPU thread bound to A76`.
  A76 benefit not measured yet (the cpufreq loop benchmark reads A55 451, A76 417 thousand/ms, but
  it is a volatile-store loop). Image queued by `finish-image.sh`, log `a618-0203-device/finish.log`.
- CI: a dispatch right after a push can build the previous head (42973920881 took 0ad3da9).
  Check the run's SHA; a second dispatch cancels the stale one by concurrency.
- Candidates next: asynchronous GPU submit with fences (glFlush is the largest cost), XR10
  conversion by the GPU instead of the CPU.

### 2026-11-11: frame time is mostly the GPU wait; 0202 polls; zero-copy plan

- Measured on 0201 (`build/a618-0201-device/live-20261111T055809Z.log`, 3460 frames): median
  frame 7.4 ms, p90 45.8 ms. In the 1600-frame summary: glFlush 10.2 ms/frame, glTexImage2D
  2 ms/frame; 233 IOSurface textures copied, 0 shared; frames ended on big cores 546, little 1054.
- `a618_render_ring` is synchronous and slept `IOSleep(1)` between looks at the CP: a panel field
  submission took 1905..2017 us (14 samples, median 1960) regardless of work; about 4 submissions
  a frame on average (30 ring wraps). Guess, not measured per frame: blur frames do many more,
  which would explain their 25..40 ms unaccounted time.
- 0202 (local + published 0ad3da9, kernel CI 42970563145): polls every 10 us for 8 ms, then sleeps;
  limit 500 ms real time; logs `SWEET CA: GPU wait mean .. longest ..` every 4096 submissions.
  Image script: `build/finish-image.sh VERSION HEAD RUN MARKER` (renderer 42857891879, disk copied
  from a618-0201-device). Not booted when this was written.
- Zero-copy plan (not started in code). Kernel: 256 empty L3 tables at L2 256..511 (IOVA
  0x60000000..0x80000000, inside the existing L2 page; `a618_tree_check` must skip them); kSurface
  for ordinary IDs maps the surface's own (cached) pages there via invalid-to-valid PTE writes, keeps
  the SweetSurface retained, returns the existing handle if already imported. GEM close clears
  PTEs and does TLBIALL (CB1 +0x618) + TLBSYNC (+0x7f0, status +0x7f4; pattern in
  sweet_smmu_context.c); the GPU is idle then because submit is synchronous. At submit, clean+invalidate
  (flush_dcache) surfaces whose seed (state + 0xc) changed or not flushed recently, as Topaz does.
  Renderer: remove the two `share_surfaces` overrides in tools/build-sweet-renderer.sh, first with
  blit_targets off (shown textures only). Limits seen: `surface_shared` takes BGRA only, while the
  census shows mostly A8 (150) and RGBA16F (68); rows must be 64-byte aligned (37 of 91 logged
  creates are). 10.7 MB refills (40..180 ms each) are attached full-screen surfaces, so the
  mirror path matters for app launches. Userland import path already exists (freedreno-darwin,
  redwood-drm, used for the panel IDs).

### 2026-11-11: 0201 boots to the UI again; SpringBoard crash loop gone

- Kernel CI 42866493648 (526bff2) passed, compact 42968791255, image SHA-256
  210430077b40093481414f2351177efb307926e50319ae4635ca3b84c4ec28cc, temporary boot from recovery
  05:58:20 UTC, fastboot OKAY. Log `build/a618-0201-device/live-20261111T055809Z.log`.
- Observed at 4647 log lines: `accessibility preferences set aside rc=0`, dark mode rc=2,
  SpringBoard exec 1, SpringBoard crashes 0, backboardd crashes 0, 57 touch events. Owner confirms
  the UI is back. So com.apple.Accessibility.plist was the remaining trigger.
- Both renames run at every boot: turning dark mode or Bold Text on will crash SpringBoard again
  until the next boot, which sets the file aside again. Real fix: CoreImage needs a GPU path in
  SpringBoard.
- Still open in this log: AegirPoster crashes (5 so far), one CPU load sample at A55 100%.
  `SWEET BUDGET` lines: 0 so far, so the texture budget has not fired yet (not proven working);
  no allocation failures matched so far.
- First finish-and-boot run for 0201 exited 4 with an empty log (cause unknown; the host adb
  server was also down afterwards). `build/finish-0201.sh` reran it. `finish-kernel-image.py` now
  adds all listed runs to `known` before dispatching compact, so an older compact at the renderer
  head cannot be picked; the script checks the 0201 marker before booting.

### 2026-11-10 late: the SpringBoard crash is saved state (dark mode + Bold Text); 0201

- Observation: the same 0198 image (image and root SHA-256 identical in
  `build/a618-0198-device/boot-*.json`) ran SpringBoard fine at 12:35 UTC and crashed from 12:42.
  In the 12:42 log SpringBoard ran for ~3300 lines while the owner touched the screen, then
  crashed (line 4392) and has crashed at every start since, across reboots. The owner says they
  turned on dark mode and Bold Text then.
- 0199 removed dark mode: rc=0 once, rc=2 in 0200/0200b (file stays gone), crash unchanged.
- 0201 (local a9632d9, published 526bff2, kernel CI 42866493648 on macos-15-intel): bsd_init
  also renames `/private/var/mobile/Library/Preferences/com.apple.Accessibility.plist` to
  `.sweet-bold` (Bold Text = EnhancedTextLegibilityEnabled there, assumed, not read from the
  phone: WSL hung before the read-only inspection ran). Logs
  `SWEET APPS: accessibility preferences set aside rc=`. Image 0201 = that kernel + renderer
  42857891879 (same renderer disk as 0200b, copied), full renderer, cpus=8, GPU 7; queued in
  finish-and-boot.ps1 (log `build/a618-0201-device/finish-and-boot.log`).
- 0200's loader in SpringBoard never ran (no hook frame). Also a latent bug there: the
  objc_addLoadImageFunc callback runs under the runtime lock and calls objc_getClass. Fix or
  drop it before relying on the loader.
- WSL hung again (Wsl/CO_E_SERVER_EXEC_FAILURE, `wsl -l -v` hangs). Pipeline now works without
  it: `build/gh_token.py` takes the token from Windows Git Credential Manager (stored for
  nonrootus); push with `git -c credential.helper= -c credential.helper=manager push
  https://github.com/nonrootus/ios-sweet.git HEAD:codex/gpu-k6a-bo-macos15`;
  `finish-kernel-image.py` uses REST instead of the gh CLI; `prepare-a618-0181-image.py` uses
  `build/mkbootimg_v2.py` (byte-identical to the WSL mkbootimg on images 0198-0200b);
  `fetch-compact-0181.py` uses gh_token. Originals kept as `*.before-win`. A full-renderer disk
  still needs WSL unless `renderer.hfs` + `renderer-overlay.json` are copied from an image with
  the same renderer run. Read-only phone inspection (`run-when-recovery.ps1`) still needs WSL.
- Unified log of 0200b copied to `build/unified-log-0200/archive.logarchive` (not parsed: WSL).
- The owner suggested wiping userdata; not needed if 0201 works (and needs separate approval).

### 2026-11-10 night: 0199 did not help; 0200 puts SpringBoard's CoreImage on the CPU

- 0200 booted 16:41 UTC (`build/a618-0200-device/live-20261110T164105Z.log`): kernel added
  the loader to SpringBoard 8 times, dyld policy allowed it (18 'input=0x0 rc=0'), but
  SpringBoard still crashed (7) at the same lr: the loader's hook found no CIContext at load
  time (CoreUI loads CoreImage lazily). Also 815 'dyld policy did not match' lines.
  SpringBoard's stderr is not copied to the console, so loader lines are not visible there.
- 0200b (local 0759cc2, published 1dad7c9): the loader also registers objc_addLoadImageFunc
  and hooks -[CIContext initWithOptions:] once CoreImage is in; the mismatch line is printed
  only 4 times. Kernel CI 42857871859 (Intel), renderer CI 42857891879; image 0200b queued.

- First 0200 kernel (CI 42850337682) failed: the helper was inserted between `static` and
  `int` of exec_extract_strings (`static #if ...`). The local compile check missed it because
  clang stops at 20 errors and the environment errors come first; `build/check-c-nolimit.py`
  adds -ferror-limit=0 (compare in-file errors with the base file). Fixed (local 982e24f,
  published d12136c): helper before `__attribute__((noinline)) static int`. Kernel CI
  42854170228 (Intel); image 0200 with renderer 42848888914 queued, boots from recovery.

- 0199 booted 15:37 UTC (`build/a618-0199-device/live-20261110T153744Z.log`): `dark mode
  preference set aside rc=0`, but SpringBoard still crashed 9 times at the same lr (unslid
  0x194b3858c). Dark mode was not the trigger. Read-only from recovery: no appearance or
  teaching-moment key in Preferences (`build/inspect-sb-style.py`), the only poster
  configuration is CollectionsPoster (`build/inspect-poster-store2.py`), so neither a dark
  poster nor a preference explains it. The styled Control Center hint goes through CoreImage
  on every start.
- `-[CIContext initWithOptions:]` (0x1949a2f1c..) reads `software_renderer`,
  `kCIContextUseMetalRenderer`, `kCIContextAllowLowPower`, has a branch for client `CoreUI`;
  it does not fall back to the CPU by itself.
- 0200 (local ee0a7b1, published a5248af): kern_exec.c exec_extract_strings adds
  `DYLD_INSERT_LIBRARIES=/sweet/lib/libSweetRendererLoader.dylib` to SpringBoard's environment
  when sweetcagpu=1 (logs `SWEET CI: SpringBoard starts with the renderer loader`); the AMFI
  dyld query 0x5a answers for `/System/Library/CoreServices/SpringBoard.app/SpringBoard`
  (ppid 1) as for the real backboardd (cdhash check kept for backboardd). The loader, for
  SpringBoard, swaps -[CIContext initWithOptions:] to add software_renderer=YES and logs
  `SWEET CI: CoreImage contexts of SpringBoard use the CPU renderer`; it is now linked with
  -lobjc. Nothing on the root changes. Kernel compile check: same in-file errors as the base
  file (environment); sweet_amfi.c compiles clean.
- Kernel CI 42848803497 on the arm64 macos-15 runner stayed queued 8+ min (no capacity) and
  was cancelled; rerun on macos-15-intel as 42850337682 (dispatch script default is back to
  Intel; SWEET_RUNNER=macos-15 to try arm64 again). Earlier: renderer CI 42848888914 (two duplicate renderer runs were cancelled by
  concurrency). Image 0200 queued in finish-and-boot.ps1 (full renderer, cpus=8, GPU 7).

### 2026-11-10 night: SpringBoard crash = dark mode + CoreImage GL; 0199 building

- Renderer with the texture budget: published 6952d9a, renderer CI 42839721238 (passed).
  Image 0198t (kernel 0198 + that renderer, SWEET_FULL_RENDERER=1, cpus=8, GPU 7) booted
  15:07 UTC, `build/a618-0198t-device/live-20261110T150713Z.log`: pool 256 MiB, renderer
  armed, then black screen: SpringBoard crash loop (36), AegirPoster crash loop (38).
- AegirPoster (Astronomy) crashes (sig 6) in a loop since 0197 (76 per boot): CPU at 100%.
- SpringBoard crash, symbolized (`build/springboard-symbolize.py`, full stack from the .ips
  via `build/inspect-springboard-crash.py` read-only in recovery): SpringBoard startup ->
  SBLockScreenManager loadViewsIfNeeded -> CoverSheet -> CSTeachableMomentsContainerView
  _addControlCenterTutors -> UIImageView initWithImage -> UIImage _imageWithStylePresets ->
  CUICatalog imageByStylingImage:stylePresetName: -> CUIShapeEffectStack sharedCIContext ->
  CIContext contextWithOptions -> initWithOptions -> (no Metal) internalContextWithEAGLContext
  -> CI::GLContext::GLContext -> GLContext::init calls a NULL GL entry with 0xb71
  (GL_DEPTH_TEST). Apple's EAGL in SpringBoard has no driver (our EAGL is only in backboardd).
  `com.apple.uikitservices.userInterfaceStyleMode.plist`: UserInterfaceStyleMode = 2 (dark).
- 0199 (local 0915222, published 07779a0, kernel CI 42843293950): bsd_init renames that plist
  to `.sweet-dark` once (light default), logs `SWEET APPS: dark mode preference set aside rc=`.
  Image 0199 = that kernel + renderer 42839721238 (budget), full renderer, cpus=8, GPU 7,
  queued in finish-and-boot.ps1 (waits 90 min for recovery). Not booted yet.
- CI timing: kernel ~15-16 min on macos-15-intel, renderer 6-8 min, compact <1 min.
  `build/dispatch-a618-kernel-windows.py` now sends runner macos-15 (arm64, the workflow
  default) unless SWEET_RUNNER says otherwise; first arm64 kernel build not measured yet.
  Concurrency cancels a running build of the same kind on the same branch.
- Real fix later: CoreImage needs a GPU path in every process (our EAGL in SpringBoard and
  apps, or a Metal device); until then dark mode crashes SpringBoard.

### 2026-11-10 night: the pool "leak" is texture copies; EAGL texture budget committed

- Why the pool fills at any size (0194 7850/8192, 0197 15600/16384, 0198 14746/16384): EAGL
  forgets images on CoreAnimation's glDeleteTextures, so nothing leaks in that sense, but every
  texture made of an IOSurface is a full copy in the pinned pool (no zero-copy IOSurface
  import: redwood_surface 0x7e only knows the reserved panel/shadow IDs), and CoreAnimation
  caches textures as an iPhone with 3 GB unified memory would.
- Last 0198 boot (`build/a618-0198-device/live-20261110T124210Z.log`, 12:42 UTC): SpringBoard
  SIGSEGV 8 times, pc 0x0, lr 0x1cb0c858c (slide 0x36590000, unslid 0x194b3858c), same
  backtrace each time; not seen in any earlier boot, including 0198 at 12:35. Not symbolized.
- Local 8515a69 (not published): `userland/gpu/eagl-texture-budget.patch` (generator
  `build/make-eagl-texture-budget.py`), applied after eagl-readback-probe.patch. struct image
  gains last_used/resident/evicted; at frame end, if copies exceed 72 MiB, the least recently
  bound images not bound in the last two frames and bound to no unit shrink to 1x1 (unpack
  PBO unbound around it) until 56 MiB remain; my_glBindTexture refills an evicted image.
  Logs `SWEET BUDGET: frame .. images .. copies .. resident .. MiB, gave back ..`.
  Not compiled yet (eagl.c builds only on the macOS runner); GL names it uses are already
  used elsewhere in eagl.c, so eagl_gen.h declares them.
- Blocker: WSL hung (`WslService` StopPending, `wsl --shutdown` fails), so no gh token: no
  push, no CI. Needs an admin service restart or a PC reboot. Then: cherry-pick 8515a69 to the
  worktree, push, `dispatch-a618-renderer-windows.py`, then an image of kernel 0198 (kernel CI
  42809370548, compact 42811641996) with the new renderer: prepare-kernel-renderer.py with
  SWEET_GPU_LEVEL=7 SWEET_CPUS=8, then boot-when-recovery.ps1.

### 2026-11-10: preserved the rollback log from recovery

- Read the 0198 persistent console ring from recovery before another boot.
  Saved `build/a618-0198-device/persistent-after-rollback.log` (322353 bytes,
  flush 13). Eight reported pool allocation failures, seven XR10 readback
  failures, eight logged direct panel swaps, no backboardd crash in that
  capture.
- Temporary 0198 boot from recovery at 12:42 UTC succeeded, fastboot exit 0.
  No userdata flash.

### 2026-11-10: 0198b regressed; restored renderer 0198

- Renderer 42815228914 passed, 0198b temporary boot OKAY at 12:30:25 UTC,
  image SHA-256 3332950a5c8dd632fec53004c467e49a388bfcede70bb4d424df79325e475953.
  The old 0198a reader retained COM12 and picked up the beginning of the next
  boot after reconnect. The valid 0198b UI capture is
  `build/a618-0198b-device/live-20261110T123219Z.log`.
- Owner reported worse scrolling. All 12 recorded w30r 1125x2436 strip
  reads succeeded but took 28.5–156.1 ms each. The log still has eight
  reported contiguous-allocation failures and one backboardd SIGSEGV FAR
  0x14 after failed 5 and 4 MiB BO retries. The workaround shrank staging
  requests but did not fix active texture allocations or CPU pixel copies.
  Do not count the failed 0198b workload as a matched FPS benchmark.
- Restored the exact 0198 renderer sources (local 7d62bd4, publish d64f41a).
  The existing 0198 image was temporarily booted at 12:35:27 UTC, fastboot
  OKAY; read `build/a618-0198-device/live-20261110T123516Z.log` for that boot.
  Confirmed SpringBoard and direct panel output on the restored image. That
  boot also logs contiguous-allocation failures and XR10 readback OOM, so
  0198 is a rollback of the experimental path, not a stability fix.
- Exact faulting symbol remains unverified. In the stripped OSMesa artifacts,
  the 0198a-like and 0198b PCs have matching candidate instructions near
  0x5269f0/0x522a88, but mapping bases were inferred. Capture image load
  addresses and symbols before changing the suspected caller. Full-size
  offscreen IOSurface transfers and BO pressure remain the performance issues.

### 2026-11-10: 0198a scroll stutters; 0198b reduces XR10 staging pressure

- 0198a renderer 42812840622 passed and booted on kernel 0198 at 12:12:11
  UTC. Image SHA-256
  5fdf251b3ab82514355a1248f0e69db06ab0248259edaae6e2adfd240ef65e62.
  The original USB capture was empty. Reattached COM12; the current boot log
  is `build/a618-0198a-device/live-20261110T121953Z.log`.
- User reports severe stutter. The recovered log has direct GPU output and
  frames continue after pressure. No backboardd crash in the first 532894
  bytes. Eight logged contiguous allocation failures, eight retry results
  (three recovered), 10 GL 0x505 errors. No XR10 storage reuse marker.
  A 223.8 ms frame spends 172.3 ms in copy-out; large w30r offscreen targets
  and XR10 readback OOM appear nearby. Of 22 sampled active frames with at
  least 60 draws (excluding first 40), median 27.64 ms and p90 165.36 ms.
- 0198b local b6da14f, published 824d429, renderer CI 42815228914. Reads
  large w30r surfaces in strips of at most 256 rows; Mesa skips its
  whole-surface ReadPixels cache for these full-width partial requests.
  The existing CPU buffer accumulates the full image and publishes only
  after every strip succeeds. This reduces temporary allocation sizes;
  total pixel bytes and the CPU conversion remain. Both patch chains
  apply/reverse on pinned source. Waiter PID 35836 packages with unchanged
  0198 XNU/compact artifact, then waits for recovery. Hardware test pending.
  Compare `SWEET XR10: strip readback`, 0x505, copy-out and heavy-frame p90.

### 2026-11-10: 0198 tested; 0198a reuses XR10 texture storage

- Kernel 42809370548, renderer 42809382175 and compact 42811641996 passed.
  0198 booted temporarily at 11:58:54 UTC. Image SHA-256
  8078d145f09c4f4a24151ef6155b62c20c3354889df2ba5442be5f8024082b36.
  HFS+ overlay remount verified both dylibs; Mesa SHA-256
  af1e36941532fe116e73181d7896e18ba085805a7c19c652021c843b8b4b73f2.
- USB `build/a618-0198-device/live-20261110T115843Z.log`: mount rc=0,
  FD618, direct panel swaps, 256 MiB pool; no GPU pool failure, GL OOM, or
  backboardd crash in the 285194-byte capture. Owner scrolled Settings and
  reported lag but no freeze. Capture has 40 frame samples, only two with at
  least 60 draws, so timing does not establish a scrolling speed gain.
- 0198a local f14ceb2, published 7130932. XR10 updates an existing RGBA8
  texture with glTexSubImage2D when level-0 format and dimensions match.
  An OOM returns failure without trying to allocate the same storage again.
  Falls back to glTexImage2D for differing storage or other subimage failures.
  Full EAGL patch chain and reverse check passed. Renderer CI 42812840622;
  no new XNU build. D: `build/finish-0198a.py` (PID 40744) packages against
  0198 kernel and waits for a recovery target. Check `SWEET XR10: reused`,
  pool failures/crashes, and timing under the same UI action.

### 2026-11-10: 0198 tests a bounded Mesa BO cache

- Mesa 25.0.7 patch `userland/gpu/mesa-sweet-bo-pressure.patch`: cap normal
  idle BO cache at 24 MiB and ring cache at 8 MiB, track bytes under the
  existing cache lock, purge both caches and retry once when the backend
  allocation fails. Rate-limited marker `SWEET BO: pressure retry`. Active
  GPU allocations remain subject to the same 256 MiB pool and IOVA policy.
- Kernel patch 0198 and mkpayload now permit a page-aligned renderer overlay
  of 1–24 MiB. D: build scripts use a 20 MiB HFS+ overlay for signed EAGL and
  OSMesa, verify hashes after read-only remount and record the disk hash.
  The old 4 MiB EAGL-only path is still supported. The 20 MiB fixture passed
  fsck, both extracted SHA checks and byte-verified payload/ADT adjacency.
- Local dc21fe4, published 2154f52, kernel CI 42809370548, renderer CI
  42809382175. Both patch forward/reverse checks passed on reconstructed
  sources, including Mesa after pinned Topaz. Package/temporary boot waiter
  PID 3940, logs `build/finish-0198.*.log`. Hardware test pending.
- 0197 final baseline from the same log: 208 frame timing samples, median
  10.32 ms and p90 47.71 ms. On frames with at least 60 draws (62 samples):
  median 27.28 ms and p90 50.28 ms. User workload varies across captures;
  compare the same UI action when possible. The 0197 trace continued after
  one backboardd restart and contains 2,480 numbered frame events.

### 2026-11-10: 0197 restores GPU output, still freezes under memory pressure

- Kernel CI 42805523308 and compact 42807614532 succeeded. Image
  ef7f2c63af15c1dccd0c4ba978089a84ac7a1f324e331fe500fcdf0008f50021
  booted temporarily at 11:28:45 UTC, fastboot OKAY. USB log
  `build/a618-0197-device/live-20261110T112834Z.log` reports panel IOVA 58000000,
  pinned 256 MiB, renderer armed, FD618, hardware submits and direct panel swaps.
- User saw a freeze. At the observation snapshot (507054 bytes) the log had
  0 CPU pool fallbacks, 8 logged direct swaps,
  8 logged contiguous-allocation failures, 45 GL out-of-memory
  errors and 1 backboardd crash reports. First SIGSEGV FAR 0x14.
  At 15600/16384 slots in use, a 224-slot request fails despite 784 slots free
  in aggregate. Later 640 and 448 slots fail at 15237/16384.
- Separately, 600x600 IOSurface wraps at page offset 0x20 still fail because
  size and computed needed length are both 1440000. Some 180x180 wrap failures
  remain. Do not infer the user-visible icon state from log rate limiting.
- Next investigate short-lived/cached BO retention and the renderer's OOM
  handling. Mesa 25.0.7 freedreno bo_new returns NULL after a backend allocation
  failure without trying a cache trim. Measure reclaim before adjusting the pool
  size again. Fix of the initialization cap is confirmed, freeze is unresolved.

### 2026-11-10: 0197 combines the GPU allocation and IOSurface fixes

- The 0196 USB log contains `GPU pool unavailable; retaining CPU renderer`.
  The configured 128 GPU table pages exceeded `GPU_MAX_PAGES=64` in
  `sweet_gpu_memory_create_nc`. 0197 raises the cap to 128, asserts that the
  configured tables fit, and logs the actual pool size. The 0197 icon retry
  remains restricted to single-plane surfaces with element height 1.
- Local `c44a052` + `1a20186`, published together as `5f3ad76` on
  `codex/gpu-k6a-bo-macos15`. ARM64 single-file compile and ASan/UBSan allocator
  model passed, including the 128-page request, last page and reject above cap.
  Exact GPU mirrors (44) passed forward/reverse replay; complete 0197 and
  restored 0196 reverse checks passed on the reconstructed files.
- Kernel CI `42802328521`, renderer `42771210243` (`d96acf5`), GPU level 7,
  8 CPUs. Image packaging process 2616 waits for CI (build/finish-0197.stdout.log
  and stderr.log). A previous 0194 recovery waiter was still running at dispatch;
  only one waiter should be active when 0197 is ready. Pending temporary boot.
  Check panel VA 58000000, pool 256 MiB, direct frames, and no fallback, pool
  exhaustion or backboardd crashes in the device log.
- First CI `42802328521` compiled XNU, then failed in the post-build reverse
  check: 0132 still expected `GPU_MAX_PAGES 64u` in its context. Job log
  `build/ci-0197-kernel-job.log` line 276513. Reproduced against old and new
  sources. Local `84def19`, published `a5963db`, checks 0197 on the final tree
  and reverses 0197 in a scratch copy before checking 0196 and 0132 there.
  The revised gate passed locally. Retry CI `42805523308`. Packaging process
  30004 and temporary-boot waiter 37812, logs `build/*-0197-retry.*.log`.

### 2026-11-10: resumed 0196 verification and bounded the wrap retry

- `0194` baseline, final USB log `build/a618-0194-device/live-20261110T095927Z.log`:
  8 pool allocation failures (initially 7850/8192 slots), 92 GL out-of-memory lines,
  3 backboardd SIGSEGV reports, and 18,595 logged 180x180 create VM errors. Use the
  same marker counts on 0196, noting the new rate limit for icon create errors.
- `0197` local `c44a052`: the shorter retry in 0196 uses the base image row span,
  so limit it to single-plane images with element height 1. This preserves the
  observed 180x180 icons and keeps the full allocation span for other layouts.
  0196 and 0197 applied in order to reconstructed SweetSurface.cpp. Both reverse
  checks and Bash syntax passed. Clang 18 emitted arm64 assembly against the
  cached XNU headers; compiler warnings were present, exit 0. Not tested on phone.
- While 0196 builds, recovery on `sweet` reported 2026-11-10 10:16:25 UTC, but
  `rtc0/since_epoch` reported 1980117. Live FDT confirms QPNP RTC on PM6150
  SID 0, register blocks 0x6000 and 0x6100, RTC writes disabled. A raw PMIC
  counter cannot supply UTC by itself. Investigate the offset or boot time seed.

### 2026-11-10 evening: 0196 is SLOW - the 256 MiB pool failed, CPU renderer took over

- 0196 booted 10:38 UTC (`build/a618-0196-device/live-20261110T103840Z.log`): `SWEET CA: GPU
  pool unavailable; retaining CPU renderer`, `|backboardd| SWEET CA: Adreno service
  unavailable`. Owner: everything very slow. Cause: the pool's page tables come from
  `sweet_gpu_memory_create_nc(SWEET_A618_RENDER_TABLES)` and `xnu/gpu/sweet_gpu_memory.cpp`
  has `#define GPU_MAX_PAGES 64u` (array `pa[GPU_MAX_PAGES]`); 0195 asks for 128. Fix: raise
  GPU_MAX_PAGES to 128 (mirror -> iokit/Kernel/arm/sweet_gpu_memory.cpp, add to the verify
  PATCHES list). The host tests do not cover create_memory, so this was missed.
- Owner is getting 0194 again (`boot-when-recovery.ps1 -Version 0194`, image already built):
  GPU on, 128 MiB pool, flicker/backboardd crash risk remains.
- GPT reported a 0196 edge case (retry size counts one plane, can cut a multi-plane wrapped
  surface short) and is preparing 0197 to retry only single-plane images. Combine it with
  the GPU_MAX_PAGES fix; one agent at a time on the branch (a new CI dispatch cancels the
  running one).

### 2026-11-10 evening: handoff - 0195 (256 MiB pool) and 0196 (icon wraps) building

- Standalone Russian handoff: `D:\ios-sweet\HANDOFF-CLAUDE.md` (old one kept as
  `HANDOFF-CLAUDE-20261109.md`). Owner's limits ran out; stopped here.
- Owner on 0194: blue wallpaper, widgets work, but everything flickers sometimes, then the
  phone froze. 0194 log: pool `in_use=7850/8192`, 38x `XR10 texture allocation failed:
  0x505`, 29x `source surface N upload failed`, then backboardd SIGSEGV twice (far 0x18 and
  0x14, PCs outside the shared cache = our renderer libraries) and restarts.
  Also 16431 failed creates of 180x180 icon surfaces at IOSurfaceAddress (kIOReturnVMError),
  each logged.
- 0195 (local 6cfddc1, published 4b6df0c, kernel CI 42796563825): render pool 128 -> 256 MiB
  (128 L3 tables, L2 64..191), panel GPU VA 0x58000000 (L2 192). Host tests
  (build/test-render-pool.sh) and verify-gmu-service-patch.py pass. finish-and-boot queued
  (cpus=8, GPU 7, renderer 42771210243, waits 90 min); phone was in recovery.
- 0196 (local 31e76e4, published ef4759f, kernel CI 42796906280, includes 0195): icon
  surfaces retry the wrap with offset + bpr * height after a VM error; failed creates logged
  32 times then every 1024th; first 8 failures show page offset and sizes. Base rebuilt from
  the whole SweetSurface.cpp patch chain (build/recon-surface); strict compile against the
  tree headers shows the same warnings as before.
- CI 42796563825 (0195 alone) was cancelled by the workflow when 0196 was dispatched on the
  same branch. Image 0196 (kernel ef4759f = 0195 + 0196, renderer 42771210243, cpus=8,
  GPU 7) queued in finish-and-boot.ps1, waits 90 min for recovery. Not booted yet.

### 2026-11-10: 0194 booted - extension points work, posters and widgets launch

- 0194 booted 09:59 UTC, `build/a618-0194-device/live-20261110T095927Z.log`:
  `SWEET AMFI: AppleMobileFileIntegrity service registered`, `stores set aside for the AMFI
  service=1`, `boot-arg state query from lsd -> 0`, then twice
  `service call from lsd sel 6 in 1/20 out 0/0 -> 0x0` (20 bytes = cdhash). After that, for
  the first time: CollectionsPoster (2x), PhotosPosterProvider, Gradient, Extragalactic,
  Weather, Emoji, Unity and Pride poster extensions, extensionkitservice, chronod and ~30
  widget extensions (Calendar, Weather, Maps, Batteries, Music, Reminders, ...) exec'd.
  PosterBoard exec'd once with no CRASH line. Crashes (sig 6) seen: BooksWidgetExtension,
  ScreenTimeWidget, IntentsExtension, StocksDetailIntents, WeatherIntents, Siri TTS
  synthesizers (MacinTalkAUSP, KonaSynthesizer, SiriTTSSynthesizer), assetsd; driverkitd
  sig 9 as before. What the screen shows: not yet reported.

### 2026-11-10: 0193 booted; next AMFI wall is the IOKit service; 0194 building

- 0193 (kernel 10dc2b0 + renderer d96acf5, cpus=8, GPU level 7) booted 07:10 and 07:37 UTC,
  logs `build/a618-0193-device/live-20261110T071056Z.log` and the next one. Observed:
  `SWEET AMFI: boot-arg state query from lsd -> 0 (rc=0)`, `LaunchServices stores set aside
  for extension points=1`, governor fine. Fields blit without the fence: `fields ~4.2-4.5 ms:
  submit 2 in ~4.0 ms, fence 0` (so the two field blits themselves cost ~2 ms of GPU each).
  PosterBoard still SIGTRAPs on first start.
- Read-only from recovery after that boot (`build/inspect-ls-0193.py`): the rebuilt store is
  again 3997696 bytes with 1 appex, 0 posterkit, 0 widgetkit. Unified log of that boot
  (`build/unified-log-0193/filtered.jsonl`, boot F14E5A2B): no boot-arg error any more, but
  still `Failed to read extension point cache ... "Unable to find AMFI"`, and for each appex
  `MIPluginKitBundle overlaidInfoPlistWithError: ... specifies a value (...) for the
  NSExtensionPointIdentifier key ... that does not correspond to a known extension point` /
  `Ignoring app extension ... due to validation issue(s)` (519 of them).
- The function (ExtensionFoundation 0x193733d68..0x193736368, strings listed by
  `build/ef-inspect.py`): needs entitlement com.apple.private.amfi.can-check-trust-cache,
  reads the plist and its detached signature (`/System/Library/xpc/extensions.plist` and
  `.sig`; both exist on the root), SecStaticCode checks, pushes the signature to the kernel,
  then `IOServiceMatching("AppleMobileFileIntegrity")`, IOServiceOpen type 0,
  IOConnectCallMethod selector 6 with one scalar (1) and the cdhash as struct input, no
  output; 0 = "cdhash is trusted", kIOReturnNotFound = "not in trust cache". "Unable to find
  AMFI" is the missing service. All steps before it already pass on our kernel.
- 0194 (local d5f204f, published 7bd3dbb, kernel CI 42792764701): built-in IOService
  `AppleMobileFileIntegrity` + user client (source `xnu/amfi/SweetAMFIService.cpp`, kernel
  path iokit/Kernel/arm/SweetAMFIService.cpp, personality on IOResources). Selector 6
  returns success, everything else kIOReturnUnsupported; logs
  `SWEET AMFI: AppleMobileFileIntegrity service registered` and the first 24 calls as
  `SWEET AMFI: service call from <proc> sel N in a/b out c/d -> 0x..`. Also a third
  one-time store set-aside (suffix `.sweet-before-amfi-service`). Compiled locally against
  the build tree headers (`build/check-gpu-memory.py` with GPU_SOURCE, and
  `build/check-iokit-strict.py`: same warning set as SweetKeyStore.cpp);
  `build/check-0194-reversal.py` replays the files.arm64 reversal checks. Image 0194 =
  that kernel + renderer run 42771210243, queued in finish-and-boot.ps1 (waits 90 min for
  recovery). Not booted yet.
- To check on 0194: service registered line; `service call from lsd sel 6 ... -> 0x0`;
  store set aside for the AMFI service=1; no "does not correspond to a known extension
  point"; CollectionsPoster or another poster appex exec'd; PosterBoard stays up; wallpaper.
  PosterBoard's data store is `/var/mobile/Library/Application Support/
  PRBPosterExtensionDataStore/59/` (not its container).
- Idea for real smoothness, not started: scan out straight from backboardd's render target.
  The DPU source pipe can crop (22,18 1080x2400 from 1125x2436) and take any stride, so
  the ~4-5 ms per-frame field blits and the copy would go away and flips could be
  vsynced; the K20 Pro port flips three buffers through CTL flush. Needs MDSS/DPU register
  work and contiguous GPU memory for the target.

### 2026-11-10: 0191 governor works (A76 were at 300 MHz); AMFI 0x60 found; 0193 queued

- 0191 (kernel CI 42767598162, image cpus=8 + sweetgmudcvs=7) booted 06:38 UTC,
  `build/a618-0191-device/live-20261110T063816Z.log`. OSM tables read fine, per_core=0 on
  all groups. Firmware rows: A55 row 6 = 1497 MHz, **A76 row 0 = 300 MHz**, L3 row 7 =
  1190 MHz. Governor raised them to 1804 / 2304 / 1459 MHz; loop speed A55 317 -> 451,
  A76 54 -> 417 thousand/ms. So on 0190c the two A76 ran at 300 MHz. Owner: "much
  smoother, still a little laggy" (app open looked 20-30 fps before 0191).
- 0191 frames under use (58 sampled): total median 18.5 ms, p90 39.5 ms; GPU ("handing
  on") median 4.7 p90 8.5; panel copy ("copying out") median 5.2 p90 10.0; the rest (CPU)
  median 6.4 p90 24.8. Simple 70-call frames are ~6 ms, of which ~5 ms is the panel copy.
- Wallpaper root cause (unified log, `build/unified-log-0190/filtered.jsonl`): lsd's
  com.apple.extensionkit logs `amfi_interface_query_bootarg_state returned error Policy not
  found`, then `Failed to read extension point cache ... "Unable to find AMFI"` (code 12);
  pkd logs `could not create extension point record ... -10814` for 181 points; PosterBoard
  logs `extension point not found for query` on every boot. `build/find-amfi-call.py` decoded
  the 20H392 function at 0x1d1fe655c: `__mac_syscall("AMFI", 0x60, &state)`, 64-bit state
  copied to *out. Our "AMFI" policy (0175) answered only 0x5a for backboardd and returned
  ENOPOLICY for everything else.
- 0192 (local 9e74bea): the "AMFI" policy is registered always and answers 0x60 with 0 for
  every process, logs `SWEET AMFI: boot-arg state query from <proc> -> 0` once and
  `SWEET AMFI: first call 0x.. from <proc>` per other call number; 0x5a stays backboardd-only
  under sweetcagpu=1. 0193 (local f89b5b9): sets the LaunchServices store aside once more
  (suffix `.sweet-before-extpoints`), so lsd re-registers the 523 extensions against the
  extension points. Published 10dc2b0, kernel CI 42770980901 (the first 0192-only run
  42770786013 was cancelled).
- Renderer d96acf5 (local f2c4a81, renderer CI 42771210243): `sweet_fields_blit` no longer
  waits on a fence after glFlush (SWEET_FIELDS_WAIT=0; the kernel submit already waits),
  and logs `SWEET DIRECT: fields N us: submit/wait/prep/map` every 300 frames. Host test
  passes. Image 0193 = kernel 10dc2b0 + renderer d96acf5, cpus=8, GPU level 7; queued in
  `finish-and-boot.ps1` (finish-kernel-image.py now accepts a compact run at the renderer
  head). To check on boot: `SWEET AMFI: boot-arg state query from lsd`, `LaunchServices
  stores set aside for extension points=1`, CollectionsPoster exec, wallpaper, the fields
  timing lines, frame times.
- The first 0193 image run failed in fetch-compact.py: the compact job (42772924755,
  artifact 13741939989) ran at the renderer head d96acf5, not the kernel head.
  prepare-kernel-renderer.py now accepts either head (the kernel stays pinned by source_run
  and markers). Image 0193 built 07:10 UTC, sha256 4631d473..., kernel markers for 0191,
  0192, 0193 and the renderer's fields timing present; waiting for recovery (60 min).
- Remaining frame-time levers: synchronous submit (CPU and GPU never overlap), full-screen
  damage every frame, the scheduler not knowing the A76 are faster.

### 2026-11-10: eight cores (0190c), CPU governor 0191 building, unified log parsed

- Owner on 0190 at 800 MHz: still not smooth, does not feel like 60 fps. `sweetfb_hz=30`
  is not the cap: it only paces the old CPU copy path; direct GPU frames skip it and the
  vsync timer stays 16667 us. Heavy frames are 21-32 ms, mostly CPU, and `cpus=6` left
  only the six A55 running.
- 0190c = the 0190 kernel and renderer, image only, `cpus=8 sweetgmudcvs=7` (cmdline 580).
  `build/prepare-kernel-renderer.py` now takes SWEET_CPUS=N like SWEET_GPU_LEVEL=N. Booted
  06:18 UTC, `build/a618-0190c-device/live-20261110T061831Z.log`: `SWEET CPU: 8/8 CPUs
  initialized, SGI1 verified`, both A76 (mpidr 0x600, 0x700) alive, boot reached
  SpringBoard, GPU level 7 accepted. Early frames median 8.1 ms, p90 17.5 ms (boot frames
  only, not comparable yet). "copying out" stays 5-7 ms per frame (full-screen field
  blits; SWEET DMG says full=1 on every frame).
- 0191 (local 2c48fca, published 4f4dc6d, kernel CI 42767598162): OSM governor in
  `osfmk/arm64/sweet_cpufreq.c` (sources in `xnu/cpufreq`, host test
  `sweet_osm_lut_test.c` passes; stub-header compile with clang-18 -Weverything -Werror
  passes). Logs `SWEET CPUFREQ:` table rows, firmware rows, per-core mode, a loop-speed
  measurement per group before and after raising, and loads every 30 s. Started from
  bsd_init after the app move; sweet_touch.c boosts on touch. Boot-arg sweetcpufreq
  (0 off, 2 fixed max) exists but the cmdline has no room for it yet.
- Unified log: copied read-only to `build/unified-log-0190/archive.logarchive` (446 MB,
  203 s). Mandiant unifiedlog_iterator v0.7.0 (owner allowed) works in log-archive mode
  only on real directories, not symlinks; `build/parse-unified-log.sh` filters through a
  FIFO to `filtered.jsonl`.

### 2026-11-10: 0190 runs the GPU at 800 MHz; wallpaper cause narrowed to LaunchServices

- 0190 image with `sweetgmudcvs=7` booted 06:01 UTC
  (`build/a618-0190-device/live-20261110T060149Z.log`): `begin ATLEAST800MHz index7; BW
  level 11`, `done rc=0 ... ACK=1 return=00000000`, `requested index=7 perf=30000007
  bw=0000b00b level=11`. Frame times (summarize-0182c.py, 35 sampled frames): median 7.98 ms
  (16 ms at 180 MHz), p90 40.8 ms. Heavy frames: "handing on" 4.3-4.5 ms (was ~30 ms),
  "copying out" 5-10 ms; the rest (~11-17 ms in a 444-661 GL call frame) is CPU work.
  Heat and owner's impression not yet reported.
- Next speed lever is the CPU clock. Nothing in our kernel touches the OSM (live FDT
  `qcom,clk-cpu-osm-sdmmagpie`: L3 0x18321000, pwrcl 0x18323000, perfcl 0x18325800). Stock
  driver (`research/sweet-k6a-osm-10c33d40/clk-cpu-osm.c`): LUT at +0x110 + 32*i
  (src bits 31:30, lval 7:0, freq = 19.2 MHz * lval, core count 18:16, single-core rows are
  boost), request = write the row index to +0x920 + 4*core (per-core when CORE_DCVS_CTRL
  +0xbc bit 0). The K20 Pro port found its cores at 300 MHz without this and got 2.8x on one
  thread. Our boot flags have `wfi=0`, so idle cores spin: a fixed maximum would run hot;
  it needs a load governor like theirs (50 ms samples, drop after 200 ms idle).
- Wallpaper: read-only look from recovery after 0189 (`build/inspect-*-0189*.py`,
  outputs `build/*-0189*-inspect.txt`, store copies in `build/ls-store-0189`).
  The rebuilt LaunchServices store (3997696 bytes) holds 1 of the 523 `.appex` on disk
  (AuthenticationServicesUI's helper, whose extension point comes from
  `/System/Library/ExtensionKit/ExtensionPoints/*.appexpt`). No extension point declared by
  a framework's `NSExtensionSDK` is in the store (`com.apple.posterkit.provider` in
  PosterKit.framework, `com.apple.widgetkit-extension` in WidgetKit.framework: 0 hits), so
  every poster and widget extension is missing. PosterBoard then has no provider and
  SIGTRAPs in `_stateLock_setupSwitcherConfigurationForFirstTime` (newest report
  PosterBoard-1969-12-31-160509); its data container is empty. Why lsd skips the
  framework SDKs is unknown; the unified log (/private/var/db/diagnostics 290 MiB,
  uuidtext 128 MiB) should say. Mandiant unifiedlog_iterator v0.7.0 linux-musl is
  downloaded and its sha256 checked in `D:/ios-sweet/tools-download/unifiedlog`; running it
  is waiting for the owner's permission.
- The iOS clock starts at the epoch on every boot (crash reports are named
  1969-12-31-16xxxx, file times are seconds since boot). The PMIC RTC is not read. This
  will matter for TLS and anything that checks dates.

### 2026-11-10: 0189 booted, 0190 asks for higher GPU clocks

- 0189 booted 05:43 UTC (`build/a618-0189-device/live-20261110T054307Z.log`):
  `moved=0 absent=32` (0188 already moved them) and `LaunchServices stores set aside=1`.
  Owner: all apps appeared on the home screen. Wallpaper is still black. In this log
  PosterBoard was exec'd once and has no CRASH line (earlier boots SIGTRAPped in
  `_stateLock_setupSwitcherConfigurationForFirstTime`), and no poster extension process
  (CollectionsPoster, LegacyPoster, ...) was exec'd. Read-only look at PosterBoard's crash
  reports and data container from recovery: `build/inspect-posterboard-0189.py`.
- Baseline frame times (summarize-0182c.py): 0188 median 15.9 ms, p90 71 ms (37 sampled
  frames); 0189 median 16.1 ms, p90 45 ms. Heavy frames spend ~30 ms "handing on" (the
  synchronous GPU submit) and 6-9 ms "copying out" at 180 MHz.
- 0190 (local e16f007b, published 52dbf78, kernel CI 42763951927): `sweetgmudcvs=N` sends
  GMU perf index N (FREQ_VOTE(N, ATLEAST)) with bin 167's stock bus level (BW_VOTE):
  1=180 MHz/bus unchanged (old behaviour), 2=267/6, 3=355/7, 4=430/8, 5=565/9, 6=650/10,
  7=800/11. Sources: stock `a6xx_gmu_dcvs_nohfi`, `kgsl_pwrctrl_clk_set_rate` ("GMU scales
  GPU freq"), live FDT bin 167 `qcom,bus-freq`. The GPU is not a CX iPeak client on this
  phone (only vidc, mdss and camera are), so stock adds no extra limit at high levels.
  Host test `sweet_gmu_dcvs_test.c` passes (gcc ASan/UBSan); level 1 writes the same six
  values as before. verify-gmu-service-patch.py passes. Reversal excludes added for 0153,
  0154, 0160. `build/finish-and-boot.ps1 -GpuLevel N` builds the image with
  `sweetgmudcvs=N` (same length, cmdline stays 580). Queued: level 7, boots from recovery.
  To check: `SWEET GMU DCVS: requested index=7 perf=30000007 bw=0000b00b`, rc=0, then frame
  times and heat. If 800 MHz misbehaves, rebuild only the image with a lower level.
- Untested lead: the boot flags have `cpus=6`; 0078 ran `cpus=8` (cpu6/7 are the A76 big
  cores). Why it went to 6 is not recorded.

### 2026-11-10: 0188 moved the apps, 0189 resets the LaunchServices store, K20 Pro review

- 0188 booted: `moved=32`, but the home screen still showed three apps (owner) and the
  wallpaper stays black. Guess: lsd keeps the store it built before the move.
- 0189 (local 3b284e6, published 387894d, kernel CI 42761623086, renderer 42677350104 /
  838dfda): bsd_init renames every
  `InternalDaemon/<UUID>/Library/Caches/com.apple.LaunchServices-4035-v2.csstore` to
  `...csstore.sweet-before-apps` once (VFS_RENAME_EXCL), logs
  `SWEET APPS: LaunchServices stores set aside=N`. `build/finish-and-boot.ps1` boots it
  temporarily when the phone is in recovery. Not booted at this point.
- Observation from our source: the GPU is held at index 1 = 180 MHz, the lowest level
  (`sweet_gmu_board_profile.c` sets `max_requested_gpu_index=1`, `sweet_gmu_dcvs.c` rejects
  anything else). Bin 167 also lists 267/355/430/565/650/800 MHz. The K20 Pro port cut draw and
  readback time by raising its GPU clock (257 to 427 MHz). This is the next GPU speed step:
  request higher perf indexes through the existing DCVS path once the votes are checked.
- K20 Pro items that apply to sweet: Wi-Fi (same WCN3990/ICNSS, their ath10k SNOC host in
  XNU plus MPSS/QRTR/RMTFS/PD mapper; needs modem.mdt, wlanmdsp.mbn, firmware-5.bin, BDF and
  NV images from this phone, never in git). Kernel code there is APSL, the rest MIT.
  Their wallpaper fix lives in their own launchd job generator and their /private/var is a
  fresh ramfs each boot, so it does not carry over to our stock launchd and persistent var.

### 2026-11-10: home screen icons fixed (0187), staged apps move in 0188

- 0187 = kernel c6a5996 (local a3e42e1, kernel CI 42756599334) with renderer 838dfda.
  Booted 04:47 UTC, log `build/a618-0187-device/live-*.log`. Owner: icons appeared.
  The fix is SweetSurface::create wrapping the creator's memory when IOSurfaceAddress is
  given. Icon data lives in the IconServices cache (`systemgroup.com.apple.lsd.iconscache`,
  129632-byte .isdata files = 180x180x4 + 32).
- Live read-only look from recovery (build/adb-hfs-readonly/inspect-ls-db.sh): the lsd data
  container and `/private/var/db/lsd` hold no LaunchServices store, so there is no saved
  database to reset. PosterBoard has 9 crash reports with the same stack and no `asi` text.
- 0188 (local f0d6122, published 87c9242, kernel CI 42758072668): bsd_init renames the 32
  bundles of /private/var/staged_system_apps into /Applications before launchd, with
  VFS_RENAME_EXCL; logs `SWEET APPS: staged system apps moved=.. absent=.. kept=.. failed=..`.
  Owner asked to fix the apps ("фикси все"). This changes the installed root but only
  renames within the volume; moving the bundles back undoes it.
- Reference for later: github.com/HeliumStudio-Dev/hackios-xnu-kernel (Redmi K20 Pro,
  raphael-bringup). Full home screen, stock wallpaper, and Wi-Fi on WCN3990 through an
  ath10k-style host (`wifi/lx/ath10k`, docs/RAPHAEL-WIFI.md); sweet's Wi-Fi is WCN3990 too.
  Their /private/var is a fresh ramfs each boot. Docs saved in research/hackios-k20-raphael.

### 2026-11-10 morning: 0186 booted, icon cause found, 0187 building

- 0186 (kernel+renderer 838dfda, kernel CI 42677318845, renderer CI 42677350104, compact
  42755101396, image 6880e919...) booted 04:22 UTC, log
  `build/a618-0186-device/live-20261110T042237Z.log`. No flash.
- Icons, cause established from the 0186 evidence: backboardd creates the 180x180,
  180x179 and 129x129 fmt=0 surfaces with `IOSurfaceAddress` and `IOSurfaceAllocSize`
  (also IOSurfaceName, a string): the picture is already in backboardd's memory. Only
  backboardd maps them. SweetSurface::create ignored the address and gave zeroed memory.
  Patch 0187 (local a3e42e1, published c6a5996) wraps the creator's memory when the
  address is given, like the 0185 wrap selectors. Kernel build dispatched; untested.
- The Apple logo screen: backboardd itself renders it. Its frames have the boot screen's
  signature (14 draws, 28 triangles, 5 clears), seen at frames 13-23 at boot on 0181c and
  again late in 0182c (720, 840, 880, 1040) and 0186 (320), after `SWEET FB: display on`.
  So it is not stale panel content. Why iOS shows it is unknown; a guess is that
  SpringBoard is slow to come back on wake because the lock screen has no poster
  (PosterBoard SIGTRAP). The reattach fix in 1793eec stays: it was a real path to stale
  content, but it is not shown to be the cause of what the owner saw.
- Pool: `no contiguous range pages=2560` (40 MB) requests appear on 0186; who asks for
  40 MB is unknown. One `XR10 readback failed: 0x505` near frame 620.
- To build an image with a kernel and a renderer from another commit:
  `build/finish-kernel-image.py VERSION KERNEL_HEAD KERNEL_RUN RENDERER_RUN RENDERER_HEAD`.
  To boot: `build/boot-when-recovery.ps1 -Version VERSION` waits for the phone in
  recovery, checks it is sweet, starts the USB reader and does `fastboot boot`.

### 2026-11-09 where things stand (0186 pending a boot)

- Works and is measured: frames go to the panel through the GPU, about 28 ms a frame
  (0182b). Owner: much smoother. b3a8 readback is only the fallback now.
- 0182c = kernel 0184+0185 (local 4a52008 and earlier, published af2c1d2, kernel CI
  42672069064, compact 42675407877) with renderer 83fcdf3. Booted, log
  `build/a618-0182c-device/live-20261109T183742Z.log`. Owner: same defects. Frame time
  median 27.0 ms. Wrap selector 6 now succeeds (A008, LA08, RGhA, BGRA images) but
  did not bring the icons back.
- Apple logo flash: 0184 was not the cause, or not all of it. After direct frames begin
  surfaces 2 and 3 are attached to new textures (7, 9, 242 in that log) and xr10_upload
  loaded the stale b3a8 memory, which still held the boot logo. Commit 1793eec starts a
  re-attached display surface from the texture of its last frame, or from the panel.
  Untested. Reasoned from the log and the code, not yet confirmed on screen.
- Home icons: not a daemon crash (iconservicesagent, lsd, pkd exec once, no crash). The
  180x180 fmt=0 surfaces come from plain `create` in backboardd (keys 8), are all zero
  at every upload, and no later upload has content. So nothing has filled them; what
  should fill them is unknown. Kernel 0186 logs each such surface's property keys
  (`SWEET SURF: id N made of:`) and which processes map it (`SWEET SURF: X maps id`).
- 0186: local 1793eec, published 838dfda, kernel CI 42677318845, renderer CI 42677350104.
  `build/finish-kernel-image.py` builds the image into `build/a618-0186-device`. To test:
  phone in recovery, start read-usb.ps1, then `python build/a618-0186-device/boot.py 0186`.
- Black wallpaper: PosterBoard still SIGTRAPs (`failure in ...` assertion in
  _stateLock_setupSwitcherConfigurationForFirstTime); the assertion text is unread.
- Build notes: `.github/workflows/xnu.yml` hit GitHub's 21000 character step limit, so
  the reversal checks now live in `tools/check-sweet-patch-reversal.sh`; add new patches
  there. A compact run once failed at startup for no visible reason and passed on retry.

### 2026-11-09 full frames on the panel through the GPU (0182b)

- Renderer local a96361b, published 83fcdf3, CI 42666959418, on the 0182 kernel. Image
  SHA-256 efcce119ad4c142f6b07ef69d2024710f98d6eb29b2507e79db1fff5754a9fd6, record
  `build/a618-0182b-device/boot-20261109T175714Z.json`, log `live-20261109T175704Z.log`.
- Frame time after frame 10, 74 logged frames: median 27.9 ms, p90 69 ms, max 525 ms,
  against about 345 ms on 0181c/d. Copy-out median 7.8 ms (the two GPU fields), submit
  ("handing on") median 11.6 ms. Typical frames 26-34 ms with 50-70 draws. No backboardd
  or SpringBoard crash, no GL 0x505/0x506 in this capture, pool peak 6932/8192.
  Measure: 12x faster. It is not yet 60 fps.
- Owner: "much smoother", first time it feels fast. Defect: a black screen with the Apple
  logo appears briefly now and then and goes away. Not a respring (no crash in the log).
  Probable cause, not yet proven: direct frames stop updating the b3a8 surfaces, which
  keep backboardd's boot logo, and a late swap misses the one-slot match in
  sweet_a618_direct_take, so AppleCLCD unpacks the stale surface. Patch 0184 makes the
  match sticky until the client closes (local fb89c44, published 0c67174, kernel CI
  42670661347). Not yet tested on the phone.
- Home icons: every fmt=0 180x180 upload was all zero and the log has
  `SWEET SURF: backboardd unsupported client wrap selector 6`. CoreAnimation wraps
  client image memory with IOSurfaceWrapClientImage and 0176 refuses it. Patch 0185
  ports it (layout from ios-topaz 0132), local 2ee161f, published 6142415, combined
  kernel CI 42671235282 with 0184. Not yet tested. Expected to affect icons and
  possibly wallpapers; whether it does is unknown until the phone shows it.
- Still open: UISwitch knob; halo on lock screen text; black wallpaper (PosterBoard
  assertion, may or may not depend on wrap); 128 MiB GPU pool; frame time spikes.

### 2026-11-09 direct panel output checks passed on the phone (0182)

- Kernel patches 0182 (panel in the GPU tree at IOVA 0x50000000, selector 0x7e for
  reserved field IDs, selector 0x7f, pool taken from both ends) and 0183 (AppleCLCD
  skips its copy for a frame the GPU already wrote). Local b3b3156, published 1c103a5.
  Kernel CI 42662630834, compact CI 42665248185, renderer CI 42662831865. Image
  SHA-256 fc9e9290223f8f3d094afed21ee6cd81b2ac57449b4f4c3333989ba12b59fd2b, record
  `build/a618-0182-device/boot-20261109T173253Z.json`, log `live-20261109T173237Z.log`.
  No flash. Patches regenerated by `build/make-0182.py` from HEAD blobs and the
  repository series; verify-gmu-service-patch.py passed; GPU tree host tests passed.
- Interlaced fields at pitch 8640 work: real frame into a pool buffer of panel layout
  mismatches=0 alpha=0 kernel_guards=0, bias 0 (row s0+2d+1 as the model says), both
  fields 6.0-6.1 ms. GPU read of the panel against CPU read: 34560 pixels, different=0.
  First GPU write to the panel, 8 colour bars over 64 rows: 69120 pixels, different=0.
- The first backboardd session died: `BO pool has no contiguous range pages=256
  in_use=8144/8192`, then SIGSEGV far 0x14, the same family as far 0x18 on 0181e.
  Now that large runs succeed, the 128 MiB pool itself runs out, so pool exhaustion
  is a real limit, not only fragmentation. The readback's 12 MB staging and the 10 MB
  test buffer add to it; 11 full-size targets attached in that log.
- `SWEET ICON` lines: every fmt=0 surface, 180x180 and 87x87, is all zero at its first
  upload, including the 87x87 Settings icons that show correctly. So zero at first
  upload is normal and says nothing about the broken home icons; 0182b reports only
  filled uploads.

### 2026-11-09 direct output stage 0 passed on the phone (0181e)

- Local 12f6cc1, published 18c44fd, renderer CI 42657180756, image SHA-256
  b2e6480f0d55df24f636425a628c9ce83c759c90e89b5614dcef5292b6375ae8, same 0181 kernel.
  Record `build/a618-0181e-device/boot-20261109T164828Z.json`, log
  `build/a618-0181e-device/live-20261109T164818Z.log`. No flash, panel untouched.
- `SWEET DIRECT: pattern` and `frame`: mismatches=0, alpha=0, guards=0,0, err=0, no
  RGBA fallback, in both backboardd sessions of that boot. A real frame cropped at
  (22,18) by the GPU, read at stride 4320, matches the b3a8 planes through
  sweet_b3a8_unpack pixel for pixel. Crop blit: submit 3.6 ms, sync 4.2-5.1 ms.
  The target was a tiled texture: this does not cover linear memory or the pitch limit.
- Pool fragmentation is real without the probe's buffers: 8 `BO pool has no contiguous
  range pages=768 in_use=5828-5935/8192` before frame 96, when the probe held nothing.
- backboardd SIGSEGV far 0x18 (pc 0x1055829dc) in the first session at frame ~103,
  after the probe's own reads hit 0x505 on an exhausted pool (client full read
  err 0x505, PBO 0x502/0x501). It relaunched. The second session hit the same GL
  errors without crashing. Cause not established; image of that pc not resolved.
- Owner's photos on 0181e: red veil gone, wallpaper black on lock and home screen.
  Settings list, its row icons and text are correct; Airplane Mode switch has no knob.
  Home screen icons (Photos, App Store, Settings) are missing, labels are fine;
  widgets are blank pale tiles; a blue switch-like glyph sits at the top right of
  the lock screen; clock, date and home bar have a bright halo. Pale screens look
  pinkish on the photos; camera white balance is not excluded.
  Owner wants smoothness first.

### 2026-11-09 readback measured on the phone (0181d)

- Local a13baf7, published daee2c1, renderer CI 42654048659, image SHA-256
  18acba5be54d303393f9b477fabe6f2b897f2410ee980dc78908d1d1e2d59323, same 0181
  kernel. `fastboot boot` only, record `build/a618-0181d-device/boot-20261109T162957Z.json`,
  log `build/a618-0181d-device/live-20261109T162947Z.log`. No userdata write.
- Measured, 1125x2436 RGBA, one sample each at frames 40-46 (microseconds):
  client glReadPixels 1 row 1759, 609 rows 72448, 2436 rows 280955. CPU part
  (time outside driver calls) 713 / 69398 / 277633. Driver submit, which waits
  for the GPU, 725 / 2121 / 3322. Proportional to area with about 1.6 ms fixed.
- PBO, full height: request 148, sync 8625 (submit 7592), map 28, memcpy from the
  map 223520 and again 230132. Second pass equal, so not page faults. Control
  cached memcpy of the same 10962000 bytes: 4919-5293. Reading the WC BO is about
  45x slower (49 MB/s against 2.2 GB/s). The working hypothesis is now measured:
  CPU reads from WC memory are about 97% of glReadPixels; the GPU blit is 3-8 ms.
- Damage: CoreAnimation draws these targets with no scissor at all, 64/64 frames
  on surfaces 2 and 3, so scissor gives nothing. Real change against the surface's
  previous contents (18 sampled frames, 14 of them after frame 16): changed pixels
  median 12.7%, bounding box median 81% of the screen and 94% of its height, p90 100%.
  Partial readback would not help while the UI moves. Do not spend time on it.
- `SWEET DIRECT` did not run: `target incomplete 0x8cdd` because the kernel logged
  `BO pool has no contiguous range pages=768 in_use=6264/8192`. A 1080x2400 target
  needs a 12 MB run. CoreAnimation then also failed `glTexImage2D` with 0x505 and
  drew with 0x506 (36) from line 3966. My probe was holding a 12 MB PBO, so this
  run does not show the failure exists without the probe; earlier captures stop
  at frame 40-150. Treat pool fragmentation as a suspect for missing textures,
  not as established. 12 full-screen targets (b3a8 and w30r) were seen by frame 160.
- Stride: `RB_MRT[].PITCH` and `RB_A2D_DEST_BUFFER_PITCH` have shr=6, 2D base has
  align=64. Panel stride 4320 = 67.5 x 64 cannot be programmed. Plan and gates in
  `docs/sweet-direct-panel-output.md`. b3a8 stays the working path; panel untouched.
- PosterBoard SIGTRAP symbolized on UUID 8F970452: PC is in
  `-[PBFPosterExtensionDataStore _stateLock_setupSwitcherConfigurationForFirstTime]`
  +0x7f8, from `_stateLock_updateExtensions:...` <- `executeUpdate:...` <-
  `prewarmWithCompletion:`. It logs the format string `failure in %{public}@ of
  <%{public}@:%p> (%{public}@:%i) : %{public}@`, then traps. Which assertion it is
  has not been read. `ipsw dyld a2s` cannot be used here: parsing this cache's
  ObjC data asks for 22 GB. `build/posterboard-symbolize.py` reads the image
  table and uses `symaddr` per image instead. Output in `build/posterboard-symbols/`.
- Owner's report on 0181d, first visual check since the 0181c colour matrix fix:
  the clock is white where it was red on 0181 (owner notes it was 4 am, so an
  automatic appearance change is not excluded); icons are broken; switches
  (UISwitch) are broken. No statement yet on the wallpaper or the red veil.

### 2026-11-09 temporary renderer library deployment

- User asked to boot the new renderer. Recovery ADB available as root on
  sweet. Recovery kernel has no HFS+ filesystem. Avoid the live HFS catalog
  and raw UFS writes. 0181 mounts a small read-only HFS+ union from `/dev/md1`
  at `/sweet/lib` after devfs mount and before launchd. It contains only the
  new `libSweetEAGL.dylib`; other names fall back to 0177. The existing
  firmware `RAMDisk` property and bytes remain separate from the new
  adjacent `SweetRendererDisk` range. No new boot argument.
- Claude also recommended RAM-only HFS before launchd and confirmed the
  kernel-local mount argument ABI. Used a dedicated read-only HFS kernel
  mount flag and retained union lookup and existing signature policy. Verify
  mount success and actual renderer timings on the device before treating
  it as a successful update. The user will still be booting the installed
  0177 root and normal iOS data writes may occur during boot.
- New 4 MiB disk `build/a618-0181-device/renderer.hfs`, SHA-256
  16ab131ea40c67ba805c7cc9a63b55feea4c39d6b7fd5e268b0033f3b92a22dd.
  `fsck.hfsplus -fn` passed. Remounted read-only and verified the sole
  signed dylib's hash, permissions, and ownership. The packer generated a
  byte-identical original 0180b payload when called without the disk and
  verified both region addresses and contents when supplied one.
- Local 805c007 and 317df18. The final change reads both properties via
  IOBSDRegistryEntryForDeviceTree after the IOKit import. Published
  ed68c3c, kernel CI 42620402082 supersedes 42619701760. Kernel and compact
  CI 42622620673 succeeded. Compact ZIP (4762720 bytes) SHA-256
  8d7c3db8f467f62d92413a5a8b2163726be7415716d90b1626c5c7b0bf2e8544.
  Temporary 0181 boot image SHA-256
  2df3cfda5a93ed6169610f3fcd0500c888dc718588cfe9875310ab79f374508d.
  The installed Mesa exports all 386 symbols imported by the replacement
  EAGL. Its exports and dependency versions match the new Mesa artifact.
- Recovery to fastboot verified. 0181 `fastboot boot` Sending OKAY 0.503 s,
  Booting OKAY 0.153 s, exit 0, `boot-20261109T130906Z.json`. No flash.
  COM12 captured `build/a618-0181-device/live-20261109T130703Z.log`.
  Existing firmware on md0, 4 MiB md1 and renderer RAM disk mount rc=0.
  SpringBoard exec and backboardd EAGL loaded. Mesa identified FD618,
  hardware fences and nonzero b3a8 scanout observed. Eight new readback
  lines prove the RAM-loaded library is active: GL readback including
  any GPU wait 259981–299666 us, CPU pack 31651–32096 us on 1125x2436.
  Timing confirms the larger delay is inside GL readback. It does not
  distinguish GPU synchronization from mapped-memory transfer. Colors,
  wallpaper, icons and w30r rendering still need runtime confirmation.
  Phone left running 0181. Boot prep under `build/prepare-0181-deployment.py`.
- Owner reports the same visual defects on 0181. Initial 30 frames showed
  no GL errors, and the captured home-screen frames used the two b3a8 display
  targets, many untagged four-byte surfaces and LA08. No w30r or untagged
  eight-byte target appeared in this run. Even small draws took ~310 ms.
- The EAGL-only integration omitted Topaz's CoreAnimation uniform hook.
  Topaz documents the exact red-veil symptom when the vibrantColorMatrix
  mask is drawn as ordinary pixels. Independently decoded the saved 20H392
  cache's `__DATA_CONST` slot 0x1d5b2fa80 to the expected 0x1884b21ac,
  checked cache UUID and patch forward/reverse. Local bf84f0a, published
  97ddaaa, renderer CI 42624267273. The replacement EAGL passes uniforms
  while preserving the original virtual call and restores ABGR order on
  copy-back to wrapped targets already read as ABGR. Includes a bounded
  explicit GPU wait timing before readback for the first four frames.
  Color and icon effects require a device test. Can reuse 0181 kernel and
  build only a new RAM disk with `build/prepare-0181c-renderer.py`.
- Renderer CI 42624267273 passed. Verified signed EAGL SHA-256
  10a9143c43997aa7631b0b26f07ba1d4f28a242e99cda9064162392d3881b116.
  Verified 0181c image SHA-256
  5978b84d1090aee809552d63310cf62842128201b7d4a7efe159cecc0f1c015b.
  Temporary boot succeeded, Sending 0.497 s and Booting 0.151 s, record
  `build/a618-0181c-device/boot-20261109T132656Z.json`. No flash. USB log
  `build/a618-0181c-device/live-20261109T132638Z.log` proves md1 mount,
  uniform hook installed, functions 20 and 45 supplied, both shaders
  linked, FD618 hardware submissions and changing b3a8 scanout. Sampled
  RGB sum at swaps 9–10 changed from ~413k on 0181 to 49458 on 0181c;
  these are different boots and do not establish visual correctness.
  w30r targets 22/25 attached. No fresh owner visual assessment of 0181c.
- First four b3a8 frames: explicit glFinish 3839–9940 us, then glReadPixels
  257774–278124 us, packing 31682–32530 us. This largely excludes waiting
  for the original draw as the bottleneck. A staging blit or WC mapping
  read can still dominate. 30-frame mean 359056 us/frame. Claude agreed
  on the missing uniform bridge and the split timing; locally confirmed
  its vtable and two context loads on the exact cache. The test leaves
  the existing blur/group defaults active, so this was not a matrix-only
  isolation test. Next compare one-row, quarter and full reads plus actual
  scissor damage per IOSurface before choosing the fast path.
- PosterBoard SIGTRAP in 0181c, unslid PC 0x1c1778268, log lines 3502–3505.
  It relaunched. No backboardd or SpringBoard panic/crash in that capture.
  Investigate PosterBoard separately from renderer color. Latest ADB
  found sweet in recovery and a separate ADB device, so select explicitly.
  No pending device operation; standalone handoff is D:/ios-sweet/HANDOFF-CLAUDE.md.

### 2026-11-09 first accelerated CoreAnimation output

- On return, recovery was available over Windows ADB. Temporarily booted
  verified 0180b over the installed 0177 root. Sending OKAY (0.406 s),
  Booting OKAY (0.151 s), exit 0. Boot record boot-20261109T121536Z.json;
  no userdata writes. USB COM12 streamed
  D:/ios-sweet/build/a618-0180b-device/live-20261109T121517Z.log.
- Shim evidence 5, fill probe 256/256 with guards intact, renderer armed
  and Mesa identified FD618. First two display surfaces have 4544-byte
  RGB stride and 1152-byte alpha stride. Both attached and read back.
  Kernel confirmed fences 1–4 and eight sampled nonzero b3a8 swaps.
  Samples changed from 22554 to 413476, and BO ranges were returned to the
  pool eight times (including 768-page buffers). This confirms the actual
  Adreno render/readback/scanout path. USB remained available and SpringBoard
  launched; in the first 267494 captured bytes there were 0 SpringBoard/backboardd
  crashes. User reported slow scrolling, red wallpaper, missing/broken
  icons, blue UI elements and a small white artifact. A Preferences exec
  was observed. This is working Adreno scanout with incomplete UI fidelity.
- Current limitations: the b3a8 readback and CPU packing take about 300 ms
  per full frame, so these results do not establish smooth graphics.
  Secondary w30r targets (FourCC 0x77333072, single 4-byte plane) are
  rejected by attachImage, producing GL_INVALID_FRAMEBUFFER_OPERATION
  (0x506) in subsequent frames. Fix their texture path and profile
  transfer time before optimizing. Keep 0180b as a reproducible baseline.
  The log also shows surface 23 (b3a8) sampled through texImageIOSurface
  as plane 0, GL_RGBA internal, GL_BGRA / GL_UNSIGNED_BYTE transfer.
  Old generic upload copies XR10 color bytes as BGRA8 and omits its
  separate alpha. Local 6455bd1 and published 78c3db8 add correct XR10
  source upload, w30r target attachment/readback, and separate GL
  readback versus CPU packing times. Patches applied/reversed locally and
  renderer CI 42616583415 succeeded. Claude independently confirmed both
  format defects. The b3a8 source appears late in the trace, so neither
  defect establishes the cause of the red wallpaper. The untyped upload's
  alpha-first channel rotation is another candidate, and the untyped
  8-byte-per-pixel target still needs identification. Slow CPU reads from
  GPU memory are a candidate for the frame delay. The new GL readback
  timing includes any GPU wait and is measured separately from packing.
  Verified the CI archive and signed arm64 iOS 16 dylibs on D: under
  artifacts/sweet-renderer-42616583415. The new libSweetEAGL.dylib is
  347472 bytes, up from 347216, so a same-length extent replacement does
  not apply. Existing 0180b remains running. The renderer change is
  untested on the phone. No userdata change.

### 2026-11-09 unattended GPU test

- The phone remained accessible in installed recovery over Windows ADB.
  User is away and unavailable to press buttons or report the display.
  No new userdata flash is needed. 0178 successfully built in 42601187047,
  compact 42604144582. Verified temporary image on D: in
  build/a618-0178-device, SHA256
  3a27980dae0bd23a16e414b7473e122ed693bf676cf2784fad64fab23e778696.
  Kept it as the stride-only fallback.
- 0179 early CI 42602588721 stopped at exact patched tree comparison.
  Updated the mirrors, inserted a DSB after clearing recycled BO memory,
  and added CP_WAIT_FOR_IDLE after A6xx CACHE_INVALIDATE before IB fetch.
  Claude's read-only review agreed on per-range descriptor lifetimes and
  pointed out those synchronization checks. Intermediate run 42604290797
  exposed a second exact-verifier requirement: enumerate 0179 in the
  verifier's forward/reverse patch list. Fixed and verified all 44 canonical
  files against the exact published baseline.
- 0180 adds opt-in CDC ACM output (sweetusb=3) from the existing log ring
  and samples nonzero RGB on b3a8 scanout. Verified USB and framebuffer
  translation units locally with ARM64 Clang and patch application both
  ways. Host reader is D:/ios-sweet/build/read-sweet-usb-console.ps1; it
  uses Windows inbox Usbser.sys, accepts only the Sweet test VID/PID, and
  writes the raw stream to D:. USB enumeration on this k6a is untested.
  Final candidate local 7a47dee, public 2452c67, CI 42605144896, includes
  EP0 receive alignment, 0178 stride, and 0179 GPU buffer recycling.
  Check hardware submits, successful b3a8 readbacks, nonzero/changing
  pixels, and sustained SpringBoard without crashes before claiming
  usable accelerated graphics. The CPU still performs final copies.

- Full CI 42605144896 and compact CI 42607209527 succeeded. Verified
  4,744,402-byte compact ZIP SHA256
  9ae053f9d9143a5f44ee375519b59e388ddcf9be332af35ef50dbc456d901697.
  Recovery to fastboot, then 0180 fastboot boot passed (Sending 0.410 s,
  Booting 0.152 s, exit 0). No userdata write. Windows enumerated COM12
  and captured D:/ios-sweet/build/a618-0180-device/live-20261109T110408Z.log.
  SpringBoard exec and BGRA swaps were observed. Hardware GPU was skipped
  before init: the image generator placed sweetusb=3 after sweetzaplayout=1.
  The tested shim requires that request at the very end, so it supplied no
  live FDT evidence (low memory evidence=0 rc=-1). Neither b3a8 output nor
  the new BO lifecycle was exercised by this boot.
- Repacked the same verified kernel as 0180b, inserting sweetusb=3 before
  the final sweetzaplayout=1. D:/ios-sweet/build/a618-0180b-device/
  shim-boot-sweet-a618-gpu.img SHA256
  b5fa1bc4a1d79cfe473dc6377a1b16cd45568ebb1a32bc80bb3356d05ec9ad60.
  Added mkpayload.py guards for exact suffix and evidence space. Tested
  rejecting the real 0180 flags and accepting 0180b and the boundary length.
  iOS 0180 currently exposes the USB output-only console, with no ADB or
  fastboot. Await recovery/fastboot; boot using boot-a618-over-0177.py 0180b
  and capture a new serial log. No change to the installed root is needed.

### 2026-11-09 b3a8 compatibility

- 0177 adds support for the 1125x2436 b3a8 target observed in the 0175
  phone log. The EAGL adapter accepts only valid two-plane RGB10+A8 geometry,
  renders into an RGBA8 texture, and uses synchronized readback and packing
  into the two IOSurface planes. XNU AppleCLCD unpacks the visible area to
  the panel's BGRA8 scanout. Both paths use the same conversion header.
  This is an SDR compatibility path with CPU copies at presentation.
- Forward/reverse application passed for both new patches on the pinned
  renderer and staged XNU. The local C model passed all 256 SDR levels,
  channel ordering, alpha and overflow/bounds assertions. SweetFramebuffer
  compiled to ARM64. Full XNU and renderer builds and device boot are
  separate gates. Phone was observed in recovery via ADB.
- Local source `8e5b5a3` and published source-only commit `406a5d1`.
  Renderer CI `42588399475` and XNU CI `42588399503` both started on
  that commit. Renderer CI succeeded. Verified the 4119646-byte ZIP and
  all three ARM64 iOS 16 Mach-O signatures/manifest hashes. New EAGL SHA256
  f3c48253fa87d5c57cd7c56a5136a392217d23d5311c503c9e5d269a199bf1c6.
  XNU CI completed successfully. Compact run 42590174822 succeeded and
  the downloaded ZIP SHA256 was 110570bad8c60246515255fccd00d7673200ece1633db6c220170a27630f343a.
  Verified the temporary 0177 boot image in build/a618-0177-device,
  SHA256 ac95889e16f16721180aaa8fa3b2c6c39da8e7aa1dc9ebb1d57db459d5097d8d,
  and preserved the 581-byte XNU command line with room for the shim token.
  The 0174 base hash, HFS fsck before and after replacing the renderer, and
  QCOW consistency check passed. Exported full 12159768324-byte
  Android sparse root (no DONT_CARE) at
  D:/ios-sweet/artifacts/gpu0177/ios16-root-sweet-k6a-20H392-gpu0177.simg.
  All 16 GiB expanded bytes matched the offline overlay.
  Sparse SHA256 aefd7d64b39ee96f82ef75f081d6f82f05ba6635b001ef68713b3ebec41aa08e.
  Expanded SHA256 095ddd00c158ec647bbbb56a750e3183eadc0b2ddb3fb84990c8746cf31e3675.
  User explicitly approved this 0177 userdata write. Recovery ADB rebooted
  to fastboot, the device identity matched recovery, and fastboot confirmed
  product sweet and userdata size 0x38405FB000. All 24/24 sparse writes
  returned OKAY, exit 0, 411.2 seconds. The post-flash
  fastboot command timed out. The user restarted FASTBOOT with the keys,
  and D:/ios-sweet/build/boot-0177-userdata.py then temporarily launched
  0177 with Sending OKAY (0.403 s), Booting OKAY (0.153 s), and exit 0.
  Boot record boot-20261109T101634Z.json. Asked user to test Settings scrolling and return
  to recovery, then capture the new SWEETLOG. Flash record flash-20261109T100840Z.json.
  The user observed a black screen and returned to recovery. Fresh log
  research/sweet-k6a-live-capture-20261027/a618-ui-0177-20261109.bin/.txt,
  flush #22, 449417 bytes, raw SHA256
  2d331491756128c7940eefc74315681637657212c6126d44c32ea3d7f3e0b9be.
  SpringBoard execs and Mesa reports FD618. Three renderer hardware
  submissions were logged (fences 1, 2, 3); these lines do not establish
  presentation of rendered pixels. EAGL still rejects the b3a8 surface
  during attachment; the log shows repeated 0x506 errors, b3a8 swaps, and
  no b3a8 readback. The old selector-6 stub now reports unsupported. The
  later backboardd SIGSEGVs have FAR 0x18/0x1c, distinct from 0175's 0x30.
  The exact 20H392 IOSurfaceClientGetBytesPerRowOfPlane reads client
  +0xe0, stride 0x80 per plane. The lock result begins at client +0x68
  and the first plane begins at result +0x68, so this field belongs at
  plane +0x10. SWEET had put it at +0x08, leaving the real stride zero.
  0178 moves that field and logs b3a8 plane dimensions, strides and
  offsets. Patch forward/reverse application and ARM64 compile passed.
  Local commit 81dc5ba, source-only publication ce466d1, kernel CI
  42601187047. Test by temporary fastboot boot over the installed 0177 root.
  Both 0177 fault PCs matched libOSMesa instructions with the observed
  null dereference offsets and with their respective direct caller BLs.
  The two caller sites each pass a null BO returned by the same allocator
  after requesting 4096 bytes and 4 bytes respectively. 0174 deliberately
  never returns successful allocations to its bitmap; the exact point
  of exhaustion was not logged. 0179 gives each BO range its own
  IOGeneralMemoryDescriptor for the existing pre-pinned WC kernel VA.
  Its IOMemoryMap retains that descriptor until unmap; BO close and
  GPU submission share the client lock through the synchronous fence.
  Only the final descriptor release returns the range to the bitmap.
  Verified patch application in both directions and compiled to ARM64.
  Local 0e5b4f9, source-only 4c39f46 on codex/gpu-k6a-bo-macos15, kernel
  CI 42602588721. It includes 0178; the earlier 0178 run remains a fallback.
  D:/ios-sweet/build/wait-compact-a618.py packages completed kernels.
  D:/ios-sweet/build/boot-a618-over-0177.py can boot either temporarily.
  The effective cache mode, release accounting, and desktop must be
  checked on the device. Offline
  preparation tools in `D:/ios-sweet/build`: `fetch-0177-renderer.py`, `stage-0177-b3a8-root.py`,
  `fetch-compact-0177.py`, `prepare-a618-0177-image.py`.
- At start, D: had 10.8 GB free and the previous full sparse root was
  12.16 GB. Stage the new renderer using local files and verify the image
  before requesting approval for any userdata write.


### 2026-11-08 GPU UI integration update

- Corrected 0174 phone run booted to the iOS desktop. The user reported
  unchanged fluidity and returned to recovery. Fresh persistent log
  `research/sweet-k6a-live-capture-20261027/a618-ui-0174-fixed-20261108.bin/.txt`
  contains 240882 bytes, flush #14, raw SHA256
  `01623d4fb30297523dffde94df92a0f1ce8f2c4aec73ccbd036cc53d02c3a2e1`.
  Live FDT evidence is 5, the 128 MiB pool is pinned, ZAP/PAS and CP complete,
  the hardware fill writes 256/256 pixels with guards intact, and the Mesa
  ring arms at tail 80. Both wrapper and real backboardd exec are observed
  (real path also appears in its ObjC output). Backboardd opens AppleCLCD,
  submits framebuffer swaps, and repeatedly finds no IOAcceleratorES.
  The log has no SweetAdreno lookup/open, EAGL loader diagnostic or hardware
  submit from Mesa. GPU initialization passes, UI acceleration is absent.
  The exact 20H392 dyld from a read-only mount of the staged root uses
  `__mac_syscall("AMFI", 0x5a, &query)` with two 64-bit words (input flags,
  output pointer). Apple's published dyld 1066.10 gates path environment
  variables on that policy reply and uses zero flags on an error. SWEET had
  no policy named `AMFI`, so this query could not enable the loader variable.
- 0175 implements that single policy query when `sweetcagpu=1`. It checks
  the 20H392 backboardd CDHash, vnode path and launchd parent, grants the path
  variable flag and allows failed optional insertion, and logs the reply.
  Patch forward/reverse checks and ARM64 compilation passed locally.
  Source-only commits `bc47c2f` (local) and `7495a45` (published). Kernel
  Kernel CI `42509661049` and compact packaging `42511031100` succeeded.
  Compact ZIP SHA256 `f7f5e45a367b6c835db4a65976871aa491f93e954eb0fab9c89235aa2464e5de`
  and kernel SHA256 `762908b3e511dc717d6aa2f4be06d1c6962e3b7cf943b6f9fc92740a7ea37006`
  verified. `build/a618-0175-device/shim-boot-sweet-a618-gpu.img` reuses the
  corrected 581-byte command line and has SHA256
  `2a8b76bb70b65595a30cd7f4ad746a86dd13c1a5ff6de7e168be576db9432c11`.
  Recovery -> fastboot -> temporary boot returned Sending OKAY (0.412 s),
  Booting OKAY (0.153 s), exit 0. Existing 0174 userdata was used.
- 0175 did not reach a usable desktop. User returned the phone to recovery.
  Fresh `research/sweet-k6a-live-capture-20261027/a618-ui-0175-20261108.bin/.txt`
  has 245841 bytes, flush #28, raw SHA256
  `a21273fa9e462091ceeeef03cb8d25a1447826b72143bfee95206aab408f069c`.
  The AMFI query succeeds, all seven EAGL methods install, `SweetAdreno`
  opens and CoreAnimation creates a Mesa GLES 3.2 context reporting `FD618`.
  Its first `b3a8` IOSurface has two planes and is rejected by the renderer,
  which only accepts BGRA or untyped single-plane targets. `glDrawElements`
  then reports `0x506`. Six `backboardd` restarts follow SIGSEGV at `0x30`;
  the 20H392 QuartzCore frames resolve to `iosurface_get_edr_factor`,
  `IOSurface::wrap_buffer`, and `GLESContext::retain_image`. The exact fault
  is `__platform_memmove` from `IOSurfaceGetBulkAttachments`: the user-client
  state pointer at +0x70 is null, so the read starts at 0x30. The kernel log
  shows IOSurface selector 6 just before the fault. Topaz 0131/0132 confirms
  selector 6 wraps a client image and requires a lock result. SWEET accepted
  this unimplemented selector and zeroed its result. Local patch 0176 rejects
  unimplemented wrap selectors 6 and 7 explicitly, verified by reverse
  application and ARM64 compilation. The unsupported framebuffer format is
  separate and still needs addressing before another GPU boot. No Mesa
  hardware submit/fence was observed. Corrected 0174 remains the last
  temporary image with a desktop and the phone remains in recovery.

- First 0174 phone run: user reported iOS desktop loaded but no improvement in
  fluidity. The phone returned to recovery and a fresh 4 MiB persistent log was
  saved as `research/sweet-k6a-live-capture-20261027/a618-ui-0174-first-20261108.bin/.txt`
  (171077 decoded bytes, flush #9). It contains `sweetgpufill=1 sweetcagpu=1`
  in launchd's boot args but stops at `SWEET A618 FILL: low memory evidence=0
  rc=-1`. No GMU/Mesa/GPU submit attempt occurred. This is a boot-argument
  assembly error, not evidence that Mesa or the GPU renderer failed: the
  594-byte static command line left insufficient space for the shim's dynamic
  ` sweetzapfdt=0x05` token (its check needs 19 spare bytes).
- Kept the first boot image and manifest with `-missing-fdt` suffix in
  `build/a618-0174-device`. Rebuilt the same XNU and root with only the
  optional `sweetiolog=-` flag removed; static command line is now 581 bytes,
  which satisfies the shim's append-size assertion. New verified temporary
  image SHA256 `d523fa0a8b54ae62a49789dda65cdd6b2b34960e3c160c28df75c94b9338d234`.
  Recovery -> fastboot -> temporary boot returned Sending OKAY (0.407 s),
  Booting OKAY (0.151 s), exit 0. No second userdata flash. Await user report
  and fresh recovery log. The first run's unchanged fluidity must not be used
  as a performance verdict for this corrected second boot.

- User explicitly approved flashing the prepared 0174 full sparse image to
  `userdata`. Windows fastboot 35.0.2 verified product `sweet` and partition
  size `0x38405FB000`; `fastboot flash -S 512M userdata` completed all 24/24
  chunks with OKAY, exit 0, 365.809 s. As on prior large flashes, ABL then
  stopped answering `getvar`; user restarted FASTBOOT with the hardware keys.
  `getvar product` resumed, and temporary `fastboot boot` of the verified 0174
  image returned Sending OKAY (0.409 s), Booting OKAY (0.153 s), exit 0.
  Requested screen report and FASTBOOT after 1–2 minutes. There is no iOS boot,
  Mesa submit or visual GPU acceleration observation yet. After the report,
  boot installed recovery and capture the fresh SWEETLOG via
  `build/pull-memory-probe-log.py`. Do not infer rendering from fastboot OKAY.

- 0174 source commit `89d15d7` was published as `f500454` on
  `codex/gpu-k6a-macos15`. CI run `42501523689` succeeded: XNU build,
  required patch verification, build-tree packaging and artifact upload all
  passed. This is a compile result, not a phone boot.
- Opt-in `backboardd` wrapper source commit `8ef793b` was published as
  `ec3f612`. Its separate macOS CI run `42502956669` succeeded; signed ARM64
  executable SHA256 `37a351553307ad228b280ab47bf1cce6fec9eb279281e25d8d78dbfb5074647b`
  is on D under `artifacts/sweet-wrapper-42502956669`. It sets
  `DYLD_INSERT_LIBRARIES` only with `sweetcagpu=1` and execs the original
  `/usr/libexec/real/backboardd`. The older three signed Mesa/EAGL dylibs
  remain under `artifacts/sweet-renderer-42495356828`.
- A separate CI run `42504902277` succeeded at fetching the verified 0174
  kernel artifact within GitHub and compressing only the DEVELOPMENT kernel
  into a 4.7 MB artifact. This avoids the 61 MB GitHub ZIP download, which
  repeatedly stalled on the local connection. The compact ZIP SHA256
  `8838bfbd147e40e59df6639555136caf2f0a8f2808dfc9a42d371393b9ae1581`
  and unpacked XNU kernel SHA256
  `365962c7873b65881321526216bd34c53a6da4e8ec32b63d7ba31af2d8b21cd7`
  passed checks on D.
- `D:/ios-sweet/build/stage-sweet-gpu-root.py` built a full local HFS+ sparse
  image from the saved `mg-nowait` root through a read-only source and QCOW
  overlay. The original backboardd is preserved at
  `/usr/libexec/real/backboardd`; the wrapper is gated by `sweetcagpu=1`, and
  the three signed Mesa/EAGL dylibs are under `/sweet/lib`. All 16 GiB of the
  exported image matched its expanded view byte for byte. HFS+ fsck and a
  separate read-only final-image remount passed, including original
  backboardd CDHash
  `89e6328541c2e37522d90fa4a693c746825b22a8624664f65662ce4e0786ffdc`
  and all staged file hashes. Local artifact
  `artifacts/ios16-root-sweet-k6a-20H392-gpu0174.simg` is 12,159,764,256
  bytes, SHA256 `10b33542e3950ed23cbe7a1463a544ae7c386378def2e0b915b5be4bdf081a5b`.
  It is a full image with no DONT_CARE chunks; flashing replaced the prior iOS
  userdata state. It has been flashed but the iOS outcome is pending.
- `D:/ios-sweet/build/prepare-a618-0174-image.py` built a verified temporary
  `fastboot boot` image at `build/a618-0174-device/shim-boot-sweet-a618-gpu.img`
  with `sweetgpufill=1 sweetcagpu=1`, SHA256
  `5274453663a980eb6d12460c863e60b11c72845143821c3c5f57bb26a54a989e`.
  Before flashing, Windows ADB saw the phone in recovery; saved
  persist/modem/fsg/fsc/vbmeta backups exist under
  `backup/sweet-k6a-20261027`. The userdata partition exceeds 16 GiB.
  User confirmed the destructive flash under AGENTS.md. The subsequent
  `fastboot boot` also completed. Capture the persistent log after the UI
  attempt. Real GPU UI rendering is unverified.

This section supersedes historical sweet-device handoffs below. The current
phone is Redmi Note 12 Pro 4G, sweet_k6a / SM7150 / Adreno 618. Historical
USB-networking, images, paths and success reports are not automatically evidence
for this device or its current image.

- 0174 Mesa client source is staged locally. `SweetAdreno` restricts opens to
  the local 20H392 backboardd code hash. It offers Mesa msm GEM BOs from the
  pre-pinned pool, bounded IB submissions, synchronous fences and a poisoned
  queue on uncertain completion. The first renderer uses CPU IOSurface readback.
  ARM64 translation units, patch staging and full 0174 CI passed. There is no
  0174 phone boot yet. BO ranges are held until device reset
  because an IOSubMemoryDescriptor map can outlive GEM_CLOSE. This limits the
  number of allocations during the first experiment.
- 0173 CI run 42498678835 compiled XNU successfully but its extra reverse
  patch check failed on `bsd/conf/files` after the new render pool entry.
  Added the required exclusion to 0158. 0174 also changes iokit/conf/files.arm64,
  so the 0139 reverse check was adjusted. Local workflow reverse checks now
  pass on the staged 0174 tree. The device is still in recovery.

- 0173 renderer memory pool in progress: 128 MiB wired Normal-NC storage is
  allocated and verified before the SID0 GPU root is installed. Sixty-four new
  L3 tables cover IOVA 0x48000000–0x4fffffff with user RW/XN leaves; the old
  fill/present pages remain separate. `sweetcagpu=1` opts in only when the
  existing fill boot is selected. Allocation failure retains the CPU renderer.
  Offline ASan/UBSan map tests, the prior GMU model and ARM64 XNU C/C++
  translation units passed. The kernel BO allocator/user client/submit path
  and root loading are not yet implemented, so do not boot this source alone
  expecting UI acceleration. Device remains in recovery at last user report.
  The backboardd binary in the local 20H392 root has code-directory hash
  `89e6328541c2e37522d90fa4a693c746825b22a8624664f65662ce4e0786ffdc`
  (first 20 bytes for XNU proc_getcdhash), for a restricted IOKit client.

- User requested the next phone run draw the actual iOS interface on Adreno.
  Skip the separate 0172 hardware run. The 0172 CI passed and the verified
  temporary image exists locally, SHA256
  `d56b94ee993b69a65eed653cd9fdba61d93018cd02bac7609a01c466db8345fb`.
  The next image needs CoreAnimation to produce an actual frame through Mesa.
  `ios-topaz` source `e4772911e116ab4ab6c4ac1f38e6106fefe8b483` has the same
  iPhone X `20H392` userland and reports hardware UI rendering on A610. Saved
  26 verified small source blobs on D. The local 20H392 cache UUID is
  `8F970452-C9E3-3E88-B114-FEB1864BC9E0`; both GLContext function symbols
  match the Topaz references. OpenGLES dispatch offsets for BindTexture,
  Clear, DrawArrays, DrawElements, Finish, Flush, UseProgram and
  FramebufferTexture2D match the HakiOS EAGL table relative to its context
  pointer. A618 hardware initialization stays ours.
  Added the ARM64 renderer build (`renderer_only` in `xnu.yml`) with pinned
  Mesa and EAGL sources and a `backboardd` loader gated on the exact cache,
  `sweetcagpu=1`, and the `SweetAdreno` IOKit service. For the first image,
  EAGL reads back the rendered IOSurface; direct imports are disabled.
  Need the kernel BO mapping and submit/fence ABI for `SweetAdreno`, load
  the dylibs in the staged iOS root, then verify Adreno GL_RENDERER, hardware
  submissions and an on-screen CoreAnimation frame in the same phone run.
  Renderer source locally `dcbb4608c7e839cf72d942bc3b2808529655f1bc` and
  in CI `1fec81943b3880f4744abb04eec34bfba8f78a5b`, run `42495356828`.
  CI passed. The three signed iOS 16 ARM64 dylibs are under
  `D:/ios-sweet/artifacts/sweet-renderer-42495356828`. The local artifact
  verifier checked each SHA256, Mach-O target, install name and signature
  record. The filesystem staging and GPU IOKit backend are unfinished.
  Draft full-ring writer `D:/ios-sweet/build/sweet-a618-render-ring.inc`
  passed ARM64 XNU code generation and the local ASan/UBSan model across
  all 8191 valid initial tails, page boundaries, wrap and publication
  failures. It is staged off-tree until the renderer's submit client can
  call it and stop the queue on failure. Next bind the signed `backboardd`
  client to its own NC buffer pool, implement the Mesa BO/submit/fence
  calls, and stage the loader on the local iOS root for the combined run.

- 0172 is an opt-in bounded queue exercise following the verified 0171
  handoff. `sweetgpufill=3` accepts at most 16 swaps with a nonuniform span,
  one 1024-byte span per frame, with a distinct completion fence and
  monotonic ring tail. Each submission still verifies all 256 words,
  source, guards, fence and live GPU state before AppleCLCD commits it.
  Any uncertain result disarms the path and the normal CPU copy resumes.
  Mode 2 retains its single attempt. The known ring has space for all 16
  packets with no wrap. The local ASan/UBSan model checks the exact PM4
  packet sequence, 16 ordered completions, distinct fences, bad data,
  timeout and no retry after failure. The two changed ARM64 translation
  units, patch application and workflow reverse checks passed. This exercises
  bounded reuse but still transfers only 1024 bytes per eligible frame;
  it does not accelerate CoreAnimation or the full framebuffer.
  Local source `6df254562394d2b5aab5d955c62298678cbd1241`, CI source
  `f841643a2c8fa1bab904b76f6e0844cedf350295`. Exact 0150–0172 forward/reverse
  preflight, all 36 canonical build-tree blobs and ARM64 checks passed.
  CI `42492574400` passed. The verified temporary image was prepared with
  `D:/ios-sweet/build/prepare-a618-0172-image.py 42492574400`. The image and
  corresponding boot/capture helpers are retained as an offline baseline.
  For sustained use, the configured ring has eight 4 KiB pages. 0172
  deliberately uses the first page only. Stock KGSL at `10c33d40`
  (`adreno_ringbuffer.h:29`, `adreno_ringbuffer.c:248–284`) keeps two words
  at the end and emits `CP_NOP` to pad to the hardware wrap. Match that
  rule, clean each touched ring page before WPTR publication, and validate
  RPTR/shadow progress over the wrapped interval. Confirm 0172 reuse before
  enabling wrap. Mesa needs an independent buffer ownership and GPU mapping
  contract before it can submit to this ring.
  Claude reviewed the next step and recommended one hardware run for ring
  wrap and an indirect command buffer in a private DMA pool mapped during
  cold boot. Defer live IOSurface mappings until the fence and TLB retire
  path is in place. A single guarded native page and a separate L3 can prove
  the initial indirect buffer and data path before allocating the proposed
  2 MiB. Keep 0172's direct packet path as the baseline, and distinguish an
  indirect buffer failure from a wrap failure in the log. Stock KGSL and
  Mesa `adreno_pm4.xml` agree on IB opcode `0x3f` and the address/size payload.

- 0171 adds the first AppleCLCD handoff to the verified A618 queue.
  `sweetgpufill=2` arms one attempt only after 0170's checked draw and
  OOB completion. Mode 1 keeps the private fill test alone. AppleCLCD
  uses the observed 1125x2436 BGRA layer and its clipped 1080x2400
  panel rectangle. On a nonuniform center span it stages 1024 bytes
  into the existing private NC page, submits CP_MEMCPY plus cache
  completion and RPTR, and verifies the full span, source, guards and
  fence. The CPU commits only the verified GPU output to scanout. A
  failed attempt, including timeout, returns to normal CPU presentation.
  No user address or scanout PA enters the GPU table. This path is a
  one-shot integration probe and does not measure speed or offload
  CoreAnimation. The local ARM64 display/adapter compilation and host
  model cover the exact packet, success, invalid/uniform skip, timeout,
  corrupt input/output or guards, missing fence and late guard failure.
  Claude's review identified possible stale GPU cache lines because the
  previous fill overlaps the staging source. The final candidate adds
  the Mesa A6xx CACHE_INVALIDATE event followed by WFI and requires a
  single enabled layer. First CI candidate `42488814983` was cancelled.
  The final local source is `031af94c1692750e30d0412aa8c9e20ff132eb58`,
  public source `343e24b57567c735cb36032dcbb93274bbbbf243`, CI
  `42489583599`. The final local patch and ARM64 checks passed.
  CI `42489583599` completed successfully. The verified temporary image
  SHA256 is `fd1937115b54374a2251438dfd5dcb2e53e0a5a302b21b2ec207f3c5b9be1fd1`.
  `fastboot boot` returned OKAY at `2026-11-08T14:44:33Z`; the owner
  returned the loaded iOS phone to recovery after opening Settings.
  Fresh complete capture `a618-fill-0171-20261108T144433Z.bin` has
  SHA256 `7a3fb2ac40e0a3c350404181350a8835c744e2a8251d9529a37a12004f3bec15`.
  It reports the expected 0170 private fill and SpringBoard, then ring
  `present` RPTR/WPTR/shadow 103, 256/256 copied IOSurface words, no
  changed source/guards, fence `1710c0de`, and exactly one AppleCLCD
  commit at swap 2/layer 0/1024 bytes. No SMMU fault was reported.
  This proves the first CP_MEMCPY-to-iOS-frame handoff on A618. The
  other bytes of that frame and all subsequent frames still use CPU
  presentation, so responsiveness is not yet changed or measured.
  For CoreAnimation, saved the pinned HakiOS EAGL, OSMesa and DRM shim
  sources locally for reference. Mesa's Freedreno database includes 618.
  The HakiOS path expects msm-style allocation, per-buffer mapping,
  submit, wait, and surface import. This port only has a fixed private
  context and kernel-built PM4. Before wiring EAGL, it needs persistent
  ring/fence handling and DMA lifetime/isolation for renderer buffers.
  Use HakiOS's user ABI as a reference without carrying over its shared
  command space or unrestricted IOSurface lookup. Measured full-screen
  present is also a separate track from hardware rendering of layers.

- 0170 keeps the corrected 0169 ZAP and CP start, and adds an optional
  private 4 KiB color/fence page at IOVA `0x40022000`. The fixed SID0
  tree has the original 18 pages without `sweetgpufill=1`. The extra
  page is RW, unprivileged, NX and Normal-NC, with alias validation
  and pinning before GMU release. RPTR still uses its privileged page.
  Both mode and draw report WPTR publication, completion or the failing
  check. A failed powered SMMU check reports the global and both context
  fault statuses, plus GPU fault address and syndrome. No fault clear
  or retry is added. The last guard runs after CPU pixel/fence readback.
  Claude agreed the target layout matches ordinary stock buffer access
  and suggested the late fault check and reporting the GMU FSR alongside
  the GPU FSR. Permission failure in 0169 remains a hypothesis.
  The stock S1 converter, address tree, composed boot model and PM4
  model cover the baseline and the additional leaf, distinct color
  and RPTR locations, and failure cases.
  Local source `23ed3a0dfa4bf59697b83c34d2481b480819acb4`, public CI
  source `bc45791b30843fff042e1cc1b5c3361b0cb9d7e6`, run `42485868637`.
  Final ARM64 target compilation and exact forward/reverse patch
  series passed before dispatch. Phone was confirmed in recovery.
  CI passed. Kernel SHA256
  `29db7dad4a12a88fd20908ab4a46e82397ce2f07a67a6b5dd109e247838d6c0f`.
  Temporary image SHA256
  `8889bc31e3ffc9f2c356d3dae01409484f553b5db5e0e26c664ea3918f6bf535`.
  Took a fresh read-only preboot capture. Fastboot reported Sending
  and Booting OKAY at `2026-11-08T13:49:41Z`. User returned the phone
  to recovery. Fresh capture `a618-fill-0170-20261108T134941Z.bin`,
  SHA256 `4bdeb668d73a877572b557837e9153433dda92efbfab7cfbb42bb0184a466544`,
  confirms the 19-page GPU mapping, PAS AUTH 0/0, TRUST 0, mode
  RPTR/WPTR/shadow 20 and draw RPTR/WPTR/shadow 80. All 256 GPU-written
  pixels match, both completion words match, guards unchanged, final
  rc 0, and SpringBoard executed. No SMMU failure record. This proves
  the private 2D path on the actual A618; it does not isolate the cause
  of the old generic failure or accelerate the iOS display path yet.
  Next: design bounded GPU work at the IOSurface/framebuffer boundary,
  with private pinned buffers, serialized submission and CPU fallback.
  The 0170 capture shows the live layer is BGRA 1125x2436 with 4608-byte
  stride. AppleCLCD crops and CPU-copies to 1080x2400 with 4320-byte
  stride, configured at `sweetfb_hz=30`. The latter stride cannot be
  encoded directly in A6xx's 64-byte-unit 2D destination pitch. An
  exact row-copy path is a candidate using A6xx CP_MEMCPY, whose packet
  carries a DWORD count and two addresses. Its behavior and throughput
  on the 618 are unverified. First validate the command on pinned,
  non-scanout buffers at the real strides, then compare measured
  presentation cost with the CPU path. Hardware composition by
  CoreAnimation remains a separate renderer integration.

- 0169 combines the remaining first-pixel stages in one opt-in
  `sweetgpufill=1` temporary boot. Same-boot ABL RAM evidence and XNU
  aperture/managed page checks gate the low ZAP candidate. For this
  XNU boot, size-only Linux pools are descriptors: no Linux allocator
  runs before the shim. The cold RPMh handoff keeps the known GPU floor
  while adding the PAS crypto path. An above-floor recorded TCS value
  causes refusal; unknown prior APPS hardware votes cannot be read back.
  With GX held, the same signed stock MDT and segment undergo SCM64
  INIT, MEM_SETUP, copy/unmap, AUTH before SQE release. Failed or uncertain
  requests stop the sequence and retain resources for reset. After
  successful CP init, the authenticated CP mode transition must settle
  before a 16x16 RGBA8 draw to a guarded subrange of the owned scratch
  page. Require both GPU-written cache fences, 256 exact pixels and intact
  surrounding words. The iOS display path is separate from this probe.
  Local ARM64 compilation of all four affected XNU units, existing
  composed host model and exact patch application checks passed. The
  PM4 model checked independent packet parity, sequencing, missing
  pixels, corrupt guards and missing fences. Original CI `42479796685`
  was canceled before hardware testing after the dedicated BCM host
  model found an out-of-bounds table walk from a shadowed count. The
  corrected model passes the 3-command and 6-command paths, including
  19/28 injected synchronization failures and above-floor history
  refusal. Only the corrected kernel may enter a hardware test.
  Corrected public source `b29874234a77f130ab7430db3b68dbf96c9462b4`
  passed CI `42480440294`; the exact linked kernel SHA256 is
  `a63d317934c3d0dae436ab6566887f954fd5fc62e47438179d6aa6f2c637c099`.
  Combined boot image SHA256
  `3c205ed6273b3f69bb141a223f5a544327831a250329295b2331defc05ade505`
  passed source, artifact CRC/SHA, payload segment, header and boot-arg
  checks. Fastboot `boot` reported Sending/Booting OKAY at
  `2026-11-08T12:38:07Z`; no partition was flashed. The phone panicked
  before iOS booted. The recovery log confirms six BCM commands ACKed,
  CM3 initialized, and HFI config and DCVS completed. Its last persisted
  line is the 1 s map sample. The photo supplies later evidence: the
  exact 0169 kernel symbols resolve the panic stack through
  `a618_zap_load+0x538`, `kmem_free_guard` and `vm_map_delete`. The
  attempted free was inside the permanent `io_submap` entry. The loader
  used `ml_io_map_wcomb`, whose allocation is permanent, then called
  `ml_io_unmap`, which frees from `kernel_map`. The corrected 0169 uses
  `ml_io_map_unmappable` with the same `VM_WIMG_WCOMB` attribute. All
  four affected ARM64 units and the exact patch/reverse checks passed.
  The generated adapter passes the original PA, 16 KiB and WIMG 6 to
  the new mapper and still unmaps before PAS AUTH. PAS AUTH and pixel
  completion await the corrected hardware test.
  The failed stack is after the return-value guards for PAS INIT and
  MEM_SETUP, so both guards passed before the unmap. The copy result
  cannot be inferred from the stack because teardown runs either way.
  Claude's source review agreed on the map/free pairing. The separate
  VA translation check stays conservative if the address is reused.
  Corrected source `8d9fac9dbc80c7464e0cbceb0e83afed6b40f096`
  passed CI `42483208301`. The selected kernel SHA256 is
  `a87b569a17c18939e5582c009051e0d2b36d62d479938cc4cc365d451c9b13d1`.
  Verified temporary image SHA256 is
  `20db15dd93e73845cfd3a522b7fd754b835b007d3f123208a01791c7c13d11a1`.
  Took a read-only preboot log snapshot and temporary fastboot boot
  reported Sending/Booting OKAY at `2026-11-08T13:17:52Z`.
  The user confirmed iOS loaded and the phone returned to recovery.
  Fresh log `a618-fill-0169-20261108T131752Z.bin`, SHA256
  `349ef08bb94d003b999f0e46b21e3b8599dbe00c14901a97b8d5a982a2a33b19`,
  confirms PAS INIT, MEM_SETUP and AUTH all returned 0/0, ZAP load rc 0,
  CP bootstrap rc 0 (RPTR/WPTR/shadow 15), normal-mode submission rc 0
  and TRUST 0, followed by SpringBoard. The fill attempt ended rc -3
  after its begin marker. That marker precedes the WPTR store. It does
  not establish publication or GPU execution. No pixel/fence result,
  CP fault line or failed power guard was persisted. The generic CP
  report classifies the entire OOB test as failure because its final rc
  includes the later fill failure.
  Next: give the 2D color/fence target an owned RW/NX unprivileged GPU
  page, leaving the privileged RPTR scratch page separate. The existing
  combined test aimed 2D at that privileged scratch page. The stock
  KGSL IOMMU gives ordinary GPU buffers unprivileged access unless the
  memdesc asks for `IOMMU_PRIV`. A permission fault is a hypothesis, not
  established by the 0169 log. In the same attempt, distinguish pre-WPTR
  guard, publication and polling failures; on an SMMU check failure
  capture read-only global/CB FSR, FAR and syndrome with the domain
  still powered. Keep the guard fail-closed and retain ownership.

- Recovery after 0169: at the user's request the exact known 0168
  image was temporarily booted again. Fastboot reported Sending and
  Booting OKAY. The user confirmed iOS loaded and returned to recovery.
  The fresh local 0168 journal confirms SpringBoard and first CP command
  completion. It is the comparison baseline for the next combined run.

- ACTUAL0168: phone back in recovery, fresh `a618-zap-0168-20261108T120043Z.bin`,
  SHA256 `fd85471befc8b2c8e78ee4bb262e0b2604cecd46134472786d45c00687e778a1`,
  total169828/flush26. Launchd recorded the shim result `sweetzapfdt=0x05`.
  The low candidate is inside RAM and outside the live FDT's fixed
  reservations, DTB itself, initrd, shim and XNU boot extents. Size-only
  pools can include the candidate but have no fixed address in the live
  tree. Stock Linux allocates them after handoff. Check any separate
  firmware ownership and the low region's XNU aliases before use. CP
  completed `RPTR=WPTR=shadow=15`, no fault, PAS INFO 64-bit 4/4 with TRUST
  1/1, and iOS reached SpringBoard and backboardd. This validates the
  live boot layout, not firmware activation. Next prove ownership and
  prepare the stock crypto bandwidth request without lowering shared votes.

- 0168 temporarily booted at 12:00:43 UTC, fastboot Sending/Booting OKAY.
  Reused the 0167 kernel, ADT, and firmware payload byte for byte except
  for the explicit final `sweetzaplayout=1` request. The locally rebuilt
  shim checks the live ABL FDT for the low candidate
  `0xb0000000..0xb0100000`. It reports RAM containment, fixed carveout
  overlap, dynamic pool possibility, FDT blob overlap and boot extent
  overlap separately. It reports the mask as `sweetzapfdt=0xNN` in
  the inherited boot arguments and on the early console. This is a
  diagnostic and grants no ownership. No candidate memory read or write,
  PAS loader call or new RPMh vote. Saved recovery FDT returned mask
  `0x05` (RAM and potential dynamic allocation). Packaged placeholder
  DTB returned `0x04`; a fixed splash carveout and malformed inputs
  were detected. Sanitized host fixture and ARM64 build passed.
  Image `build/a618-zap-fdt-preflight/shim/out/shim-boot.img`, SHA256
  `360ca5750b47a98e0f06830ffe17a7b1fdf90b5951ff6e7c9d71b524b9c2617c`.
  See ACTUAL0168 above. No new CI required for this shim-only test.
  Offline stock ELF recheck confirms exact MDT header+hash data and B02
  source bytes, one relocatable segment at offset zero, 4 KiB PAS span
  and 1 MiB alignment. Report `build/a618-zap-fdt-preflight/stock-zap-layout.json`.
  Xiaomi `drivers/of/of_reserved_mem.c` assigns addresses to size-only
  pools during Linux early boot. The shim records a potential overlap
  independently of fixed reservations so a size-only node cannot be
  mistaken for evidence of a live occupant or evidence of ownership.

- ACTUAL0167: fresh recovery capture `a618-zap-0167-20261108T111847Z.bin`,
  SHA256 `5c85040fe6620666f522f0a15f0e4e98c928084b6a01a4d324bf4e16d6816aed`,
  total162758/flush10, no wrap or decode errors, differs from 0166.
  `SWEET A618 ZAP: reserve verified pa=1fca00000 bytes=100000 pages=64`.
  CP completed `RPTR=WPTR=shadow=15`, clean fence and SMMU. PAS INFO
  repeated 64-bit 4/4, TRUST 1/1. Boot log reaches SpringBoard and
  backboardd; phone back in recovery. The high carveout is outside XNU
  managed RAM and the checked aliases. Bootloader ownership and PAS
  compatibility remain open. Check a low candidate against the live
  ABL FDT and actual initrd on the next image.

- 0167 implements a read-only runtime check of the opt-in ZAP reservation.
  It verifies the ADT descriptor and both XNU RAM limits, checks the PTOV
  entries for overlap, confirms the last managed page still translates,
  then verifies that all 64 reserve pages are unmanaged and absent from
  the physmap tail and bootstrap linear VA. The GPU test continues after
  logging the result, so a fresh boot can also confirm the 0166 CP/PAS
  baseline. No access to the reserve contents and no PAS loader call.
  Both actual XNU ARM64 translation units compiled with target headers.
  Exact patch application and all workflow reverse checks passed on the
  saved XNU tree. Exact published baseline and all 32 canonical blobs
  passed. Local `6ab5a9d`, published `ff27040880eb0434322d64fa761bd6dea088bc7b`.
  GitHub Actions `42474284974` succeeded. Build 11:07:14–11:16:23 UTC.
  Downloaded 6565542 compressed kernel bytes and verified CRC/SHA256
  `5d9bab28f9cdaa48fe8e5fe35024eb9897aba68d7ce799029e377055b5cafaf1`.
  Checked 48 existing kernel markers, both ZAP markers, exact payload
  reproduction and 10 segments. Reserve image SHA256
  `3bae447c0f58b985246c6f54b2f5a7c6cbc6878207439a0b7e4c5a3ab81491b8`.
  Fastboot temporary Sending/Booting OKAY at 11:18:47 UTC. Record
  `build/xnu-memory-probe-42474284974/boot-attempt-20261108T111847Z.json`.
  Runtime check passed in the fresh recovery capture above.
  Establish bootloader ownership separately before loading firmware. The
  shipped Android DTB has a placeholder memory node and cannot replace a
  check of the live ABL FDT, its fixed carveouts, and initrd bounds.

- Stock PAS bus preparation, offline: Xiaomi's crypto-to-EBI client uses
  393600000 B/s average and 3936000000 B/s instantaneous. The captured
  FDT binds all six BCMs to RSC APPS. Using its exact node widths, port
  counts, validated CmdDB, and stock division and clamp, the isolated
  average/instantaneous pairs are MC0 `444/8894`, SH0 `188/3766`, SN0
  and SN11 `742/7426` each (same VCD3), CE0 `16383/16383` (14-bit
  clamp), and ACV `0/8` (APPS bit). Current GPU-only floor is MC0
  `0/4076`, SH0 `0/1726`, ACV `0/8`. The captured disabled TCS history
  has SN0 and SN11 `1265/1265`, which could have a higher average than
  the isolated PAS vote. History does not identify live votes. Derive
  an owned or conservatively merged APPS transaction before sending
  requests. No new RPMh command or PAS call made. Private arithmetic
  record `build/a618-pas-crypto-isolated-votes.json`.

- Second review with Claude identified the stock DMA placement question.
  Confirmed in Xiaomi `drivers/of/device.c` that OF devices default to a
  32-bit coherent DMA mask. The captured `kgsl-hyp` hierarchy has no
  `dma-ranges`, and its PIL driver does not raise the device mask. The
  separate INIT metadata allocation explicitly sets a full DMA mask and
  uses strongly ordered memory. SCM64 availability does not establish
  that PAS13 accepts a segment above 4 GiB. `0xb0000000..0xb0100000` is
  an aligned low candidate from the saved recovery FDT, within RAM and
  clear of declared fixed carveouts. Verify current ABL FDT, initrd,
  ownership and aliases before selecting it. No low-memory mapping or
  write attempted. See Xiaomi 10c33d40 `arch/arm64/mm/dma-mapping.c` for
  cache flush and direct-map removal on its DMA allocation path.

- HakiOS reference from the owner: `oosexgang/hakios-metal` moved to
  `oosexgang/hakios-xnu-kernel/hakios-metal`. Reviewed selected public
  files at `63fc2b4633bac3af8e57dadab9f5a8d4cb940438`, verified against
  Git blob IDs and saved on D: under `research/hakios-xnu-source-63fc2b46`.
  Their measurements show Metal window-server rendering on POCO X5 Pro
  5G (`redwood`, SM7325, Adreno 642L, chip ID `0x06030500`, iOS 16.5).
  The comparable kernel path in `drivers/gpu/hakios.adreno.c` loads the
  signed ZAP, starts CP, submits `CP_SET_SECURE_MODE(0)`, proves a GPU
  write to scratch, then fills a rectangle via `CP_BLIT` and checks its
  memory. Use that sequence as a cross-check against Xiaomi A618 stock
  and Mesa. Their fixed `ZAP_MEMORY=0x8b71a000` is from redwood's DT.
  sweet_k6a's PAS13 node has no `memory-region`. Keep the A618 firmware,
  SMMU, CCU and GMU profile. Treat failed PAS calls as failures on sweet,
  rather than assuming a prior ZAP is loaded as the reference does.
  Once the A618 fill passes, `drivers/gpu/hakios.gpu.cpp` and
  `hakios-metal/include/hakios-metal/gpu.hpp` give a working IOKit/msm DRM
  buffer, submit and fence interface to adapt to our backend. `compiler.cpp`
  currently selects their chip at compile time. `HakiosMetalCA.m` and its
  QuartzCore shader selection are checked against 16.5 (20F66), so validate
  against our 16.7.16 (20H392) before trying the window server. Reference:
  https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/docs/reference/metal.md

- ZAP memory preparation: `tools/mkadt.py --highmem --a618-zap-reserve`
  creates an opt-in ADT with managed RAM ending at `0x1fca00000` and
  `/chosen/sweet-a618-zap-reserve` describing the aligned 1 MiB up to
  `0x1fcb00000`. The panic log remains at `0x1fcb00000..0x1fcc00000`.
  The FDT range is RAM with no fixed reservation overlap. Recovery's
  actual `mem_dump_region` was outside it, although the FDT declares that
  dynamic pool without placement constraints. Confirm actual boot use
  and the active XNU mappings before writing to the reservation.
  Offline: reproduced the entire default 0166 payload byte for byte,
  then packed the reserved layout with the same kernel, flags and
  firmware segments. Bootstrap 32 MiB floor `0x1fc000000` and
  `topOfKernelData=0x10251c000` fit below the reserve. The flag rejects
  QEMU and lowmem. Bundle SHA-256 and source-byte comparison passed.
  `build/a618-zap-reserve-preflight/payload-zap-reserve.bin` SHA256
  `e07d950cbfb0f05de30e5ce5bc0164a9652c1b2fe73c5f022a1dde357dbc1004`.
  Offline payload only. Next verify the physical range against runtime
  physmap/VM and validate the stock crypto-to-DDR vote for signed ZAP.

- 0166 adds an explicit `sweetgpupasprobe=1` option after the existing CP
  success path. It calls only stock SiP INFO `IS_CALL_AVAIL`, starting with
  the atomic self-query and falling back to 32-bit only on an unsupported
  reply. After detecting the convention it queries the availability of
  PIL INIT, MEM_SETUP, AUTH and SHUTDOWN by ID. Each is a query target,
  never a callable command in this patch. It verifies the GPU is idle,
  ring and memory pointers are still 15, fence clean, TRUST unchanged and
  CP/GMU/SMMU guards pass around every call. Host sanitizer model passes
  the opt-in, fallback and invalid-reply cases. ARM64 target-header build
  passed. Hardware availability is now confirmed below; firmware
  authentication, physical image ownership and pixel output remain to be
  verified.

- ACTUAL0166: owner confirmed iOS boot and returned the phone to recovery.
  Fresh `a618-pas-0166-20261108T103341Z.bin`, SHA256
  `cb269167e5aee822868230cd20ddc1a00f1b8eb7689dfdc01a1f0bbed566b808`,
  total170869/flush16, differs from 0165 preboot. CP again completed
  `RPTR=WPTR=shadow=15`, no recorded fault; OOB/HFI/DCVS checks passed.
  Protected monitor answered the 64-bit INFO self-query and reported
  PIL INIT, MEM_SETUP, AUTH and SHUTDOWN all available (4/4). TRUST
  remained 1 before and after, probe `rc=0`. These are availability
  queries, not firmware authentication or GPU rendering. Next establish
  exclusive physical memory for signed `a615_zap` and verify exact stock
  PIL loading sequence before making any secure loader call.

- CI0166: local `82d292a`, published
  `855a0c4091d2c7609b543fa0558605405eaef022`. First run
  `42470629500` failed before compile when the KDK download was invalid;
  the same source succeeded on retry `42470932692`. Build completed
  10:31:13 UTC; source/kernel checks passed, all 48 required kernel markers
  and SHA256 verified (`793da55116505d902b117a4212fae2379f937f167f21980cdc92cf4db069581a`).
  Payload reconstruction and all 10 segments passed. Temporary image is
  17321984 bytes, SHA256
  `87367ffc15dce3eb2abc44e2dff8793af01acbb8890b888fb61037b1ed490279`.
  `fastboot boot` Sending/Booting OKAY at 10:33:41 UTC; record
  `build/xnu-memory-probe-42470932692/boot-attempt-20261108T103341Z.json`.
  Fresh recovery log and owner boot confirmation recorded above.

- ACTUAL0165: first GPU command and GPU write to memory confirmed on
  sweet_k6a. Fresh recovery capture `a618-cp-0165-20261108T095722Z.bin`,
  SHA256 `5ae258a1ebefb09650b248875230a0feb85767d594122f5d7b1bdc12799820af`,
  total162110/flush15, no wrap or decode errors, different from preboot.
  The delayed ROQ path again showed zero at first and 100us, then exact
  stock values for all four registers at 10ms, fence range0x80a008a0 and
  fence control/status0. `ROQ settled to stock before SQE`, then
  `rc=0 configured_writes=80 sqe_attempted=1 RPTR=15 WPTR=15 shadow=15
  busy=71000000 fence=00000000 waited_us=0`. `CP_ME_INIT` and
  `CP_WHERE_AM_I` completed; the CPU initialized the shadow to zero and
  the GPU wrote the completed ring pointer. OOB ACK and ACK clear passed;
  vote, mappings and memory retained through reset. No recorded CP faults;
  the analyzer passed with zero issues. Boot log reaches SpringBoard and
  backboardd; phone returned to recovery. No pixel rendering tested yet.
  Next: validate stock signed a615_zap activation (PAS 13) and a guarded
  16x16 RGBA8 fill to owned memory. See render test preparation below.

- ACTUAL0164: phone back in recovery. Fresh
  `a618-cp-0164-20261108T092245Z.bin`, SHA256
  `73620d056529029a1851c9122a18e11e9bb8a3395d880555f35f7b28a5a48fba`,
  total167487/flush13, no wrap or decode errors. iOS log reaches SpringBoard.
  AXI reads248/13 and writes27/0. OOB, SMMU, HFI and DCVS healthy. Before
  the group ROQ2/ROQ1/pool all zero, FIFO already 0x00180000. The stock
  writes made ROQ1=0x8040362c and pool=0x80. ROQ2 remained zero at first
  and at 100us, then read the exact stock 0x010000c0 at the post-group
  10ms sample. All four then matched, range0x80a008a0, control/status0
  and clock0. `rc=-5 configured_writes=34 sqe_attempted=0` because the
  0164 diagnostic branch always stops. Dedicated OOB released cleanly.
  The sample proves the exact ROQ2 value is visible before SQE; it does
  not distinguish elapsed time from completion of adjacent writes.

- 0165 retains the exact stock order and the observed 10ms delay after
  the group. Only the specific immediate ROQ2 zero may reach the
  delayed check. Other mismatches stop, and all four readbacks, the
  original fence range, zero fence control/status and existing GPU/SMMU
  guards must pass before remaining setup. No retries or clock writes.
  The analyzer requires ordered and exact settlement evidence to treat
  the initial ROQ2 zero as resolved. Target-header ARM64 check passed;
  composed host model passed including persistent-zero and neighbor-fault
  cases. Parser accepted a synthetic success built from actual 0164
  measurements and rejected eight corrupted transcripts; actual 0164
  failure remains a failure. CP execution remains unconfirmed.

- CI0165: local `fcd765b`, published
  `f23d9e0be190e71d5aead9bbd5e5602ed9c77754`. Run `42468244180`
  failed before compiling: KDK 13.5 could not be mounted (`image not
  recognized`). The same source succeeded on run `42468333945`.
  Build 09:43:17-09:55:23 UTC, kernel marker checks passed 09:55:28 UTC.
  Downloaded 6555968 compressed kernel bytes, verified CRC and SHA256
  `b1f179cdee4039370945fa132a9dcfb619521cc3e8d71af5ff5bfee95aa5a423`.
  Checked 44 base markers plus ROQ fence, snapshot and settlement, exact
  payload reproduction and all 10 kernel segments. Image 17321984 bytes
  on D:, SHA256 `91b3919a5c3b0c8cb1cd3cc10af5bcf27b354cbdf726ad6fbfe4f523b2d3964a`.
  Payload SHA256 `762681273f0df9f9fc8264090dbf3cdf3a7d41e5b0188552bf71f200d266db76`.
  Temporary fastboot start 09:57:22 UTC; Sending/Booting OKAY
  (0.406s/0.151s). Record `build/xnu-memory-probe-42468333945/boot-attempt-20261108T095722Z.json`.
  The recovery watcher awaits fresh `a618-cp-0165-20261108T095722Z.bin`.

- BOOT0164: CI42465621779 succeeded for
  `311f0f13748fa6b363811967d442b58bc234c701` (local `4fb1a57`).
  Build 09:05:15-09:17:10 UTC; source/kernel checks passed 09:17:20 UTC.
  Kernel download 6560474 compressed bytes. CRC and SHA256 checked:
  `64de1c5fbc1a60f32e0e77e91623f0c395bef4fe04b1fc2f4befe3afc5880c2d`.
  44 base markers plus ROQ fence and snapshot markers, 10 segments and
  exact payload reproduction checked. Image 17321984 bytes on D:.
  Image SHA256 `a712387cf684d922c8c861e0e2c32194a5319d7bf11dc8b396d43f087e7da10a`.
  Payload SHA256 `00c3573bb505496882968a7848e52293d0efcf62f6f78cc14dc2d806f5f72e03`.
  Fastboot temporary Sending and Booting OKAY at 09:22:45 UTC
  (0.404s/0.152s). Record `build/xnu-memory-probe-42465621779/boot-attempt-20261108T092245Z.json`.
  See ACTUAL0164 above for the recovery result.

- ACTUAL0163: owner returned to recovery. Fresh
  `a618-cp-0163-20261108T083259Z.bin`, SHA256
  `ad931731ec80a927a426902fc1092dabd7b752cf08b99702656eb871bc8d6bf6`,
  total189388/flush76, no wrap or decode errors. iOS log reaches SpringBoard.
  AXI reads248/13 and writes27/0, clean HFI/DCVS/SMMU/OOB. ROQ2 at
  0x8c2 returned zero after the stock write 0x010000c0 and again at 100us.
  ROQ1 0x8040362c, pool 0x80 and FIFO 0x00180000 matched their writes.
  Fence control and status were zero on all five samples. RBBM_CLOCK_CNTL
  also zero. `rc=-5 configured_writes=34 sqe_attempted=0`, clean OOB release.
  The neighbours' initial values were not sampled. These observations do
  not establish that HWCG caused the ROQ2 result.

- 0164 adds read-only samples of the same four registers before the group
  and 10ms after the diagnostic group. Also check the programmed fence range
  0x80a008a0 and require exact zero fence status during the group. No changes
  to stock write values/order. Initial mismatch always stops before SQE,
  including when delayed ROQ2 matches. Claude suggested before/after
  samples and recommended stock comparison before attributing the zero to
  HWCG. Verified the current recovery config lacks kprobes, debugfs and
  function tracing; no passive pre-SQE register interface was found. Stock
  recovery KGSL open previously failed on missing SQE firmware. A
  temporary instrumented stock kernel is a distinct comparison path.
  ASan/UBSan model, ARM64 target headers, patch and log parser checks passed.
  Local `4fb1a57`, published `311f0f13748fa6b363811967d442b58bc234c701`.
  CI42465621779 dispatched with kernel-only download and local image
  preparation watchers. Phone in recovery after 0163.
  Prepared a private comparison patch
  `build/a618-stock-roq-readback-reference.patch` against Xiaomi
  10c33d40a11ecdc75cc1dadb5bd07894bab05815. It adds five read-and-log
  calls around the stock ROQ writes, SQE release and completed CP init.
  Apply/reverse checks passed. No stock kernel compiled or booted.
  The partial source checkout would need full build inputs for that test.

- BOOT0163: CI42462366234 succeeded for
  `29faa8a9111b7edde8ff25454789b4102e89c39d` (local `2353c1c`).
  Build 08:19:00-08:30:48 UTC; source/kernel verification passed at
  08:30:54 UTC. Kernel download 6570738 compressed bytes, CRC verified.
  Kernel SHA256 `238b062f72ae8a4a46eac2f4ecb27263e1742ed0de85c0c4ad91998b2bc5bcfe`.
  Checked 44 base markers plus the new ROQ marker. Verified all 10
  segments, image 17321984 bytes and exact payload reproduction.
  Image SHA256 `ca47fa314ae9bea486a036822a9d67445d6b19886211143e6a1764c7d7c9a6b1`.
  Payload SHA256 `7d93e5ec21efbb9698396ebbe6342e01bf7de99dddf30cc981617382f1a3d159`.
  Fastboot temporary Sending and Booting OKAY at 08:32:59 UTC
  (0.405s/0.151s). Record
  `build/xnu-memory-probe-42462366234/boot-attempt-20261108T083259Z.json`.
  See ACTUAL0163 above for the recovery result.

- ACTUAL0162: phone back in recovery. Fresh
  `a618-cp-0162-20261108T080356Z.bin`, SHA256
  `e5b41e49b02743ed7f0736dd39fa954d00b228759c27b41a47f6deb122439498`,
  total167074/flush29, no wrap or decode errors. The log reaches
  SpringBoard and records surface calls. AXI248/13 reads,27/0 writes,
  ACK3, GX0/0, TRUST1, TSB initially empty. The previous GMEM limit
  comparison passed. The 31st setup write failed at CP_ROQ_THRESHOLDS_2
  (0x8c2): stock 0x010000c0 read back zero. `rc=-5 sqe_attempted=0`,
  OOB released cleanly. The command processor did not execute.

- 0163: stock Xiaomi and upstream Linux both program 0x010000c0 for this
  family, and stock snapshot code reads the ROQ size back. Zero is not
  treated as a valid value. Log AHB fence control/status and top-level
  GPU clock control at the ROQ boundary. Only if the observed zero is
  stable after 100us and the fence and GPU stay healthy, collect the
  adjacent stock ROQ1, pool and FIFO values. Any diagnostic run exits
  before CP_AHB, protect, ring setup or SQE. Unstable reads, new bits,
  fence failures and guard faults stop the group. No fence or clock
  writes added. Claude agreed against accepting zero and suggested
  grouping adjacent writes with fence checks. We limited that to this
  single group and made the mismatch path return failure unconditionally.
  The packet and ring constants matched stock in the review. Composed ASan/UBSan model,
  target-header ARM64 compile and exact patch checks passed. Source
  `29faa8a9111b7edde8ff25454789b4102e89c39d` (local `2353c1c`)
  dispatched as CI42462366234 on macos-15-intel. Kernel-only download
  and local image preparation wait on CI.
  Recovery KGSL reports Adreno618v1, gpuclk180000000, HWCG1, SPTP_PC0,
  IFPC1, reset_count0 and empty snapshot timestamp/fault counters.
  These are recovery driver values. The XNU test samples the hardware
  clock-control register and AHB fence independently.
  Local log analyzer `a28320e` accepts the ordered clean ROQ marker,
  keeps diagnostic samples in JSON and rejects duplicate, reordered,
  fenced and unavailable samples. Synthetic cases and the actual 0162
  failure passed classification. This tool change requires no XNU rebuild.

- BOOT0162: CI42459716059 attempt 2 passed for source
  `5cb64a75df12de7f36e51c52986d0a02c886015b` (local `6e244dc`).
  Build 07:47:31-08:01:35 UTC; final source/kernel check passed at
  08:01:42 UTC. Downloaded only the kernel (6569389 compressed bytes)
  and its checksum. Kernel SHA256
  `83fe446b23f410533d8144315327114cff963c0ec28fc459103cb9b656afd7f4`.
  Local image 17321984 bytes, SHA256
  `3ecd631bd409797d5be172f490b8b55f48e08a0a8f681071cdcb58abcbdf75a7`.
  Verified 44 kernel markers, all 10 segments and payload reproduction.
  Payload SHA256 `54d68a601991dd73788db9bea09503d5184cd0b6004d702b6fe263f07704d4f0`.
  Fastboot temporary Sending and Booting OKAY at 08:03:56 UTC
  (0.403s/0.152s). Record
  `build/xnu-memory-probe-42459716059/boot-attempt-20261108T080356Z.json`.
  See ACTUAL0162 above for the recovery result.

- ACTUAL0161: owner confirmed iOS loaded and returned to recovery. Fresh
  `a618-cp-0161-20261108T073350Z.bin`, SHA256
  `3f08d71c0ef20bd0f51619d876201a01d741f6e25a4a06cea114c36bb712ec97`,
  total172818/flush12, no wrap or decode errors. AXI reads248/13, writes27/0
  with ACK3 and verified restoration. The 0161 busy-mask comparison passed.
  CP reached the 27th setup write. UCHE GMEM MAX LO (0xe0d) returned
  `0x0017f000` after the stock inclusive-limit write `0x0017ffff`.
  `rc=-5 sqe_attempted=0`, OOB released cleanly. 0162 keeps the stock
  inclusive-limit write and expects exactly the observed last-page base.
  No CP execution or rendering observed. 0162 model, ARM64 and exact patch
  checks passed. CI42459716059 builds source
  `5cb64a75df12de7f36e51c52986d0a02c886015b` (local `6e244dc`). Attempt 1
  exited 6 just after announcing macOS 13.5, before cloning XNU or compiling.
  The pinned build script next fetches the KDK manifest, so a network/DNS
  failure is likely. The log does not name the failed host. The empty build
  tree and failed kernel artifact upload were downstream symptoms. `gh`
  reran failed jobs on the same commit. Attempt 1 evidence and failed log
  are saved in `build/xnu-memory-probe-42459716059`. Watcher requires
  attempt 2 or newer before image preparation. Phone in recovery after 0161.

- ACTUAL0160: owner confirmed iOS loaded and returned to recovery. Fresh
  `a618-cp-0160-20261108T071308Z.bin`, SHA256
  `5485d9596a14b1619f5c046cb29d3ffda4717fab6eeb4e81521533cc5580aeb0`,
  total159846/flush10, no wrap or decode errors. CX counters started with
  EN/SEL/CLR0, measured AXI reads248/13 and writes27/0 at ACK3, and restored
  controls. HFI/DCVS/SMMU/OOB passed. GX0/0, CX0/3. CP passed the bus gate
  and reached the 18th configuration write. After the stock all-ones
  write, `RBBM_PERFCTR_GPU_BUSY_MASKED` (0x50b) returned `0x002f7fff`.
  `rc=-5 sqe_attempted=0`; dedicated OOB released cleanly. No CP execution.
  0161 keeps the stock write and requires the exact observed readback for
  this one register/value pair. All other readback comparisons are exact.
  Composed model passed, including refusing `0x002f7ffe`; ARM64 and exact
  patch checks passed. CI42458287007 passed for source
  `ace6fa02a41cfd349dc0c7667495fc9e865d9801` (local `5a42172`), build
  07:19:29–07:28:49 UTC. Selective kernel 6563043 compressed bytes, SHA256
  `eee42a0a85a1020f5aa68cc2e59a1a2d3590d1f46405f2feec51bfa4d58fc771`.
  Verified 44 markers, exact 10 segments and image SHA256
  `c66baa229b58567003e3c5970c60c28308a8d5b6e3067656772c6594e0df054f`.
  Payload SHA256 `ab3940ea21c270ef226776e760610171721290945167eb139005bd80d7e43b05`.
  Temporary fastboot Sending and Booting OKAY at 07:33:50 UTC. Boot record
  `build/xnu-memory-probe-42458287007/boot-attempt-20261108T073350Z.json`.
  See ACTUAL0161 above for the recovery result.

- 0160 prepared from 0159. It measures stock CX AXI read/write counters
  around the existing PERF/BW/TEST exchange before dedicated GPU OOB.
  One zero halt write, no counter clear or new HFI command. Requires clean
  power, both contexts, readable idle controls and verified restoration.
  If ACK3 persists, require fresh bidirectional CX traffic evidence before
  attempting the existing bounded SQE test. CX counts do not identify the
  master or prove GX traffic. Claude checked selectors and ownership and
  recommended GX health checks, persistent first-access markers and a
  read-only counter clear check; all are included. Composed ASan/UBSan,
  target-header ARM64, exact patch checks and log parser checks passed.
  CI42456713426 passed for source `b208b7fc85e224e188f9a55ecc0a0eb533f65555`
  (local `28062f8`), build 06:56:27–07:10:51 UTC. Selective 6557198-byte
  download, CRC/SHA256, 44 kernel markers and 10-segment payload passed.
  Kernel SHA256 `60bc182b1360dbcd0bbc7fef7929e8ed1d22e3ad33285f43aca31c5e4848fbc8`.
  Image size 17321984, SHA256
  `4154372212ac5261106659a1542a9a830e8967be216f1e62671b6f33ac661127`.
  Payload SHA256 `83ada3fdf3b76f30ad46fd33d5d5b31c1472652e087453082e7a9d3a25789580`.
  Temporary fastboot Sending and Booting OKAY at 07:13:08 UTC.
  Boot record `build/xnu-memory-probe-42456713426/boot-attempt-20261108T071308Z.json`.
  See ACTUAL0160 above for the recovery result.

- Parallel source check: live recovery FDT lists `GCC_DDRSS_GPU_AXI_CLK`
  (GCC ID 0x1b) for the GPU, GMU and KGSL IOMMU nodes. The pinned GCC
  driver places it at physical 0x0014452c, separate from the measured
  GPU MEMNOC branch at 0x0017100c. The stock GMU prepares both clocks.
  XNU has no direct vote or status read for the DDRSS branch today.
  Its actual state in XNU is unknown. If 0160 shows no traffic, a
  read-only sample of this branch during the same boot is a candidate
  follow-up. Zero counters alone would not prove a clock or bus fault.

- ACTUAL0159: owner confirmed iOS loaded and returned to recovery. Fresh
  `a618-cp-0159-20261108T063508Z.bin`, SHA256
  `5a0508bfe87876244c7d12286bb2fda08a13f9a2d4a5e7017140640a5cc18c30`,
  total159800/flush12, no wrap or decode errors. Both SMMU contexts, HFI,
  DCVS and dedicated OOB passed. Correct A615-family GX regs read0/0.
  CX req/ACK was0/3, ACK remained3 after the single zero write and100ms.
  `rc=-4 configured_writes=1 sqe_attempted=0`; OOB released cleanly.
  No first command was submitted. Next test measures AXI traffic directly.

- 0159 prepared from the 0158 device result. Read the A615-family GX request
  and reset-status registers with masks `0x1e0/0xf0`. For the observed CX
  request0 and ACK3, the opt-in path issues the stock GBIF deassert once,
  verifies request0 and observes ACK for up to100ms. A persistent ACK
  blocks CP configuration until bus traffic can be verified. Claude found
  that stock does not poll for ACK clear. We retained the stricter diagnostic
  gate and leave the GPU vote and DMA memory pinned after any SQE release.
  Host ASan/UBSan, ARM64 target-header compile and exact patch checks passed.
  CI42454440649 passed for source `0977f5e1734db7196ce88099e25db1238455e41e`
  (local `7bd5285`), build 06:22:21–06:31:22 UTC, kernel checks passed.
  Selective 6570156-byte compressed kernel download, CRC/SHA256, 40 kernel
  markers and exact 10-segment payload reproduction passed. Kernel SHA256
  `ee8c77bb48e6da7dbce0662a01e60d196b9ea33e73220e684ce5ca55ef0c0611`.
  Image size 17321984, SHA256
  `aa0aee108966dfa9454105673f3d787a158235f181c3e8c60c04cec788992c23`.
  Payload SHA256 `75817c10dabb5100486aac0b04cb72d29825b951d275bccf7120e206fc81c0bd`.
  Temporary fastboot boot at 06:35:08 UTC returned Sending and Booting OKAY.
  Boot record `build/xnu-memory-probe-42454440649/boot-attempt-20261108T063508Z.json`.
  See ACTUAL0159 above for the device result.

- ACTUAL0158: owner confirmed iOS loaded and returned to recovery. Fresh
  `a618-cp-0158-20261108T060958Z.bin`, SHA256
  `f2bad50eaa1f30c4d4451c84a1a24b4c57e6c35d080426618e47e83aff02d962`,
  total157401/flush16, no wrap or decode errors. GMU/HFI/config/DCVS,
  SID0/CB1 and SID5/CB0 health and dedicated GPU OOB ACK all passed.
  CP preflight read GBIF request/ack `0/3`, generic GX `deafbead/deafbead`,
  TRUST `1` and empty TSB. CP stopped with `rc=-3 configured_writes=0
  sqe_attempted=0`; dedicated vote released, cleanup0/IRQ0. No CP execution
  or GPU-written shadow observed. Stock Xiaomi10c33d40 uses GPR0_CTL0x18
  and VBIF_GX_RESET_STATUS0x215 for the A615 family including A618 and
  deasserts CX GBIF halt with a zero write at0x3c45 on start. Verify safe
  power and status for this exact family before attempting that sequence.

- 0158 first GPU command passed CI42452778965 from source
  b54644b2f92e614d29fc9a81334e2b93862b583b (local 39fa305). Build ran
  05:58:09–06:07:01 UTC and the required source and kernel checks passed.
  `sweetgpucp=1` opts into the stock A618 register setup,
  67-register powerup list, 15-word CP_ME_INIT/CP_WHERE_AM_I packet and a
  bounded 2-second RPTR plus GPU-written shadow check. It requires the 0157
  GPU power vote and 0156 SMMU mappings. GPU vote and all DMA memory remain
  pinned after any SQE release attempt; failures are not retried. Raw GPU IRQ,
  CP fault, SMMU, GBIF, power, write-drop and stock TSB checks precede and
  guard the attempt. The 0158 composed host ASan/UBSan model, ARM64 target
  compile, exact apply/reverse checks and log-parser synthetic cases passed.
  Selective kernel download and verified temporary boot scripts are ready.
  A passing device test would show first CP execution and DMA shadow only;
  rendering and iOS graphics integration remain outstanding.

- 0158 temporary boot sent at 06:09:58 UTC. Fastboot Sending and Booting
  both returned OKAY. Selective download was 6565359 compressed bytes.
  Kernel SHA256 `6f949617501de8fcd24dc3e8357100eef0c10cc84b049482cc16dda71a356a80`.
  Image size 17321984, SHA256
  `8ec2d165dc35ab190cd7e874f19a1004f67970e28c50ac8117e6aa1bc73887af`.
  Payload SHA256 `7e4e2aca93bb286104a4a01a7f6e470cd32b54096b9c3d4e31c9ac17d52a9fa9`.
  Verified 39 kernel markers, full payload reproduction and all 10 segments.
  Boot record `build/xnu-memory-probe-42452778965/boot-attempt-20261108T060958Z.json`.
  See ACTUAL0158 above for the recovery result.

- Next render test preparation: Mesa 63350a03 references are saved under
  `D:/ios-sweet/research/mesa-a618-63350a03`. Its A618 device entry uses one
  CCU, a 64 KiB sysmem depth cache and `blit_wfi_quirk`. The sysmem color
  offset is therefore 64 KiB, which encodes `RB_CCU_CNTL=0x08000000` with
  the Mesa A618 defaults. The POCO F3 example's `0x10000004` is for A650.
  For an RGBA8 linear solid fill Mesa leaves `LINEAR_YUV` clear and uses
  `SP_A2D_OUTPUT_INFO=0x0000f180` with full channel mask. Follow the A618
  idle wait before `CP_BLIT` and verify cache flush completion. Suggested
  first target is a separate owned 4 KiB page with a 16x16 RGBA8 rectangle,
  64-byte pitch, expected pixels and untouched guards. Add this mapping
  during cold setup. Stock A618 uses the signed a615_zap firmware path for
  normal graphics mode after CP init. Confirm that path before submitting
  blit packets. Mesa and stock source checks are offline preparation.

- Render firmware preparation: the 2026-11-07 recovery FDT lists
  `/soc/qcom,kgsl-hyp`, `qcom,pil-tz-generic`, `a615_zap`, PAS ID 13.
  Its only other property is a phandle; no `memory-region`,
  `qcom,mem-protect-id`, proxy clocks, regulators or IRQ are described
  on that node. The stock loader's conditional subsystem-VM assignment
  is therefore not part of this DT-described flow. The separate
  `/soc/qcom,kgsl-iommu@5040000/gfx3d_secure` child is present and
  enabled by default. Stock marks the MMU secured for that child.
  XNU's current nonsecure SID0 mapping does not set up that context.
  The captured MDT has one relocatable load segment, index 2, with entry
  and image base 0x5000, file/memory size 0x7c0, and 1 MiB alignment.
  Xiaomi 10c33d40 `peripheral-loader.c` rounds the image span to 4 KiB,
  allocates 1 MiB for this alignment, and passes the 4 KiB span to PAS
  memory setup. The load segment starts at offset zero in that owned
  allocation. `subsys-pil-tz.c` supplies the stock order of metadata init,
  memory setup, loading the signed segment and authentication. Firmware
  calls and the XNU allocation adapter remain to be validated on this phone.
  Pinned loader sources are saved under `research/sweet-k6a-stock-gmu-10c33d40`.
  Order for the opt-in render path: stock `a6xx_microcode_load()` loads
  signed ZAP after programming the SQE instruction base and before
  releasing SQE. `a6xx_rb_start()` then runs CP init, and only after it
  completes uses the authenticated ZAP path to switch to normal graphics
  mode. Keep the working 0165 diagnostic available independently.
  Xiaomi `drivers/soc/qcom/scm.c` detects the SiP convention with the
  atomic INFO self-query (64 then 32); it queries normal call availability
  with the unmasked SiP function ID. Existing PSCI/SMCCC success does
  not establish the Qualcomm SiP convention or PAS support on this boot.
  Treat a read-only probe as transport evidence only; separately require
  both transport and PAS success for each signed loader call. Do not
  truncate physical addresses if only the 32-bit convention is available.
  Second review corroborated stock order and identified the permanent
  XNU physmap alias as a possible hazard if PAS protects the region.
  Stock allocates the relocatable image with `DMA_ATTR_NO_KERNEL_MAPPING`
  and maps temporarily while copying. Resolve physical ownership and
  CPU alias removal before AUTH; the existing Normal-NC DMA helper only
  checks its own mapping. Verify exact PA alignment at allocation time.
  Stock votes crypto-to-DDR for INIT and AUTH, so verify the equivalent
  platform path before enabling those calls. A probe can query availability
  without issuing a PAS loader command, and record TRUST after the
  existing CP init as a baseline. Do not bypass signature verification.

- ACTUAL0157: owner confirms iOS loaded and returned to recovery. New
  capture a618-oob-0157-20261108T052914Z.bin SHA256
  8c8282ad9c65185cd1220232a8e33abb4048920602fa948ce33a1d7d95caa08a.
  Total156718/flush10, no wrap or decode errors. GPU OOB bit16 saw a
  fresh ACK bit24 on the first poll. While held: RBBM_STATUS1,
  CP_PROTECT_CNTL0, CP_ADDR_MODE_CNTL0. ACK cleared, release issued,
  cleanup0/IRQ0, GMU session and both SMMU contexts passed post-release
  check. GMU root104734000/GPU root104754000; earlier mapping samples
  at0/1/10s had global0, FSR400/400 and GPU FAR0. CP has not executed.
  Next: hold this vote across stock-proven CP setup and a bounded first
  submission, with GBIF, trusted-window, protection and fault checks.
  Full CI42449703601 passed at 66959be3039ef01b8a5aacde2755c61a9b74b881.
  Kernel SHA256 4a5a907a1be689abea0f9818472241efec37f2f240c5a2cca9d3b7916a0a078a.
  Image SHA256 65b092113f5c09c4167f1a978b9a1f45af247dfa1f9e5f94da621d77cf25c8df, 17321984 bytes.
  Verified 34 kernel markers, reproduced payload, 10 segments, boot parts
  and all flags. Temporary fastboot boot 2026-11-08T05:29:14.327063+00:00 had
  Sending/Booting OKAY (0.413s/0.152s). No partition flash. Evidence
  build/xnu-memory-probe-42449703601/boot-attempt-20261108T052914Z.json.

- DESIGN0157: after successful0156 mapping, opt-in sweetgpuoob1 exercises the
  dedicated GPU power vote used before command processor setup. Xiaomi
  10c33d40 A615-family profile includes A618, request0 uses set bit16,
  response bit24 and release bit24 in the opposite direction. Require
  quiet IRQ, same power/transport session and both SMMU contexts. Poll at
  100us with a 100ms deadline. Read RBBM_STATUS, CP_PROTECT_CNTL and
  CP_ADDR_MODE_CNTL while held. Acknowledge the dedicated bit and release
  only this vote if access remains healthy. Boot/DDR votes stay held.
  The test stops before GPU register programming and SQE launch. Actual
  adapter ASan/UBSan passes clean response, timeout, sticky/stale ACK,
  IRQ/SMMU faults, unavailable register and one-shot cases. ARM64 headers,
  exact0156→0157 patch, workflow reverse checks and log parser pass.
  Full build and phone evidence recorded above.

- NEXT CP SUBMISSION (offline, outside0157): stock CP_ME_INIT is followed by
  CP_WHERE_AM_I in adreno_ringbuffer_submit_spin. The new 15-DWORD encoder
  matches stock parity and both packets across all 1,048,575 aligned nonzero
  32-bit shadow-page IOVAs. Scratch DMA evidence requires a fresh write of
  RPTR=15 from GPU plus hardware idle and no observed fault. No DMA ran.
  import-a618-protect-profile.py pins three Xiaomi source hashes and the
  captured FDT hash. A618 capacity32, stock28 GPU groups and2 SMMU groups
  from qcom,protect 0x40000+0x10000 bytes. Verified all31 writes (including
  enable) against stock constructor with unsigned bit31 in host harness;
  slots30 and31 stay untouched. ASan/UBSan and ARM64 packet object pass.
  Claude reviewed the source and identified the held GPU OOB, GBIF/SECVID
  and protect/powerup ordering, and stock WHERE_AM_I as necessary checks.
  Verified packet and protection against Xiaomi code and FDT. Require
  fault-free preflight and keep fault evidence rather than clearing it.
  TSB policy/actual registers and GBIF/fence behavior remain unobserved.

- ACTUAL0156: owner confirms iOS loaded and returned to recovery. Fresh
  a618-map-0156-20261108T045704Z.bin SHA256
  2d9fb33cb6c6d11f29d1165d8235477c9bcb37bbb1228b762c7aaf09935cb925.
  Total162757/flush20, no wrap/decode errors. HFI, CONFIG, DCVS and MAP
  summaries pass. GPU SID0/CB1/slot1/ASID2 installed with root104774000
  before CM3 release. Separate GMU root104754000 remained intact. Three table
  and 18 data pages retained. At 0/1/10s global fault0, both FSR400 (format
  metadata), GPU FAR0. All 18 raw GPU reads finite, ring/SQE addresses and
  pointers zero, CP_SQE_CNTL0, RBBM_STATUS1, CP_STATUS_1=01000000. This is
  translation register readback, with the first GPU transaction still open.
  Next gate: stock-supported command processor setup and first bounded
  CP_ME_INIT, with GPU power ownership, memory visibility and fault checks.
  Verified stock geometry: RB0=32KiB, RPTR shadow offset0, RB_CNTL0800020c.
  Captured FDT for A618: HBB14, MAL32, UBWC2, macrotiling property absent.
  Previous0155 kernel/log both rejected by0156 validators. Phone in recovery.

- BOOT0156: full SWEET DEVELOPMENT XNU CI42372262645 passed for
  84b4b01fed3a3d77e1f35d74fa068b1f80706ef0. Preflight, full compilation
  and final exact source/kernel checks succeeded. Selective compressed
  kernel download6553427 bytes, verified SHA256
  c2317c30796b818f7cb27cfcf00866cf394fc6cc181e127f4a448276782c1669.
  Local image17321984 bytes SHA256
  69acba83dee1b2b086ee8d96b64cc6b231345e5e6b54d6ac155e949bf2d3885b.
  Payload reproduced,10segments/0fixups and Android v2 parts checked;
  cfg1/profile167/DCVS1/prep1/map1 flags verified. Target was in recovery;
  temporary fastboot boot 2026-11-08T04:57:04Z had Sending/Booting OKAY
  (0.406s/0.154s). No partition flash. Evidence
  build/xnu-memory-probe-42372262645/boot-attempt-20261108T045704Z.json.
  Device iOS and mapping results are confirmed above. Watcher
  build/watch-a618-0156-recovery.py captures a618-map-0156-20261108T045704Z
  and rejects the old0155 log. Do not repeat the boot if the watcher times out.

- DESIGN0156: fixed GPU SID0/CB1/slot1/ASID2 attaches
  BEFORE CM3 release, while the existing cold guard requires CM3 reset,
  retention0 and GX collapsed/DOWN. Existing GMU CB0/SID5/ASID1 stays owned.
  No live attach, global SMMU reinitialization/TLBI, CP write or execution.
  Three NC table pages map18 distinct NC data pages with pinned stock role
  permissions; software IOVAs SQE40001000/ring40010000/scratch40020000/
  pwrup40021000. Powerup page is reserved, not an initialized register list.
  Both contexts/pages remain retained until reset. Opt-in sweetgpumap1
  requires prep1/DCVS1; postboot verifies pair and faults at0/1/10seconds.
  Exact11target patch forward/reverse and complete126-156 series passed.
  Cold helper ASan/UBSan:160 callback failures,56 readcheck failures,
  36 corrupt registers/3 rejected roots pass; legacy context tests pass.
  Actual adapter ASan/UBSan and ARM64 target-header leaf/tree/context/
  probe/adapter code generation PASS (build/a618-0156-local-checks-passed.txt).
  Fixed tree model covered full4GiB walk,98304 bit corruptions/210 aliases.
  Log summary passed missing/duplicate/fault/order cases. Model caught the old
  CB0-only TTBR writer; CB1 now allowed only for explicit cold test before
  CM3 release. Full build and temporary boot evidence above.
  Claude call did NOT produce review: classifier stopped it, and it read
  only the old context/board files. No Claude approval is claimed. Initial
  live-attach proposal abandoned; cold design uses existing stopped guard.

- ACTUAL0155: owner confirms iOS loaded/recovery. Fresh capture
  a618-prep-0155-20261107T120021Z.bin SHA256
  f14dfdcd525e63fbb733c07b8b646c12eb70cffa1763672228b4601258ea661b;
  total160196/flush11/no wrap/decode errors, different from actual0154.
  HFI/CONFIG/DCVS/PREP summaries pass; watcher30523 completed0.18NCpages
  verified: SQE8/ring8/scratch1/pwrup-reserved1; SQEpayload32132, version
  016ee19a/patch01190001. All18rawGPUreads finite: RBBM_STATUS1,STATUS3/INT0;
  CP_SQE_CNTL0,RBbase/hi/cntl/RPTRaddr/RPTR/WPTR0,SQEbase/hi0,CP2GMU0,
  HWFAULT/INT/PROTECT0,CP_STATUS_1=01000000. Postclearguard IRQ0/0,GX28,
  HFI1,GDSCRf8222000,CFG00070400; finalguard passed. No inferred CP halt,
  ownership or GPU DMA proof from raw values. No SID0 mapping/start/rendering.
  GMU root104774000, SMMU global0/FSR400/FAR0/syndrome0. Phone recovery.
  Next: cold SID0 context attachment above, preserving GMU CB0/SID5;
  never rerun global SMMU prepare while CM3 executes.

- OFFLINE NEXT GPU LEAVES: sweet_a618_pte.c/.h/_test.py, unlinked and
  NOT in0155. Role-specific permissions match pinned stock S1 conversion:
  SQE RO/unprivileged/executable; ring RO/unprivileged/PXN+UXN; scratch/pwrup
  RW/privileged/PXN+UXN. Nonzero4KiB36-bit PA, MAIR0 Normal-NC, no IOVA or
  attachment. Existing GMU PTE and publisher unchanged; existing publisher
  deliberately REJECTS these XN leaves, so future explicit publisher support
  and separate SID0 ownership are required before use. ASan/UBSan stock
  converter comparison across4roles/range/boundaries and ARM64 header compile
  passed. Evidence build/a618-pte-offline-0155/verification.json.
  CFG completion semantics separately checked against Linuxv6.12 gdsc.c;
  bits16UP/15DOWN at GDSCR+4 for POLL_CFG_GDSCR. Source provenance saved in
  build/a618-0155-gdsc-reference.json, not confused with older KGSL regulator.

- ACTIVE0155: full XNU CI 42369170554 SUCCESS, compiled source a2ae3e8d8000bbbfd6f9ea62facb919147fa7b66.
  Exact preflight/build/final source+kernel checks passed. Selective download
  CRC/SHA verified;25actual kernel markers, reproduced payload,10segments,
  Androidparts and cfg1/profile167/dcvs1/prep1 verified. KernelSHA256
  5b327732c126f847f81adbf616d82f92b2bef39eb7bcb4dd5a196e5b77e352b3.
  ImageSHA256 b6125711f9ca44becd4c09c1f317019143379e345484ccdd38a4e88b0544704f, 17305600bytes.
  Temporary fastboot boot 2026-11-07T12:00:21.328554+00:00: Sending/Booting OKAY.
  Evidence build/xnu-memory-probe-42369170554/boot-attempt-20261107T120021Z.json and verification
  manifests. No partitionflash. User asked1-2min/no touches/recovery because
  jtag1/wfi0; iOS and inactive memory/raw register results confirmed above.
  Capture prefix a618-prep-0155-20261107T120021Z; watch-a618-0155-recovery.py reads
  once, rejects unchanged actual0154 baseline, saves HFI/CONFIG/DCVS/PREP
  summaries. Do not rerun boot merely because watcher expires.
  Later unlinked PTE helper (mainaa198db/public5c57abf) is NOT in this kernel.
  No GPU-client mapping, valid powerup list, SQE execution or rendering yet.

- PREPARED0155: same-session DCVS-success opt-in sweetgpuprep1 stages
  18 inactive Normal-NC pages (SQE8/ring8/scratch1/pwrup-reserved1), copies
  validated32132-byte SQE payload, zero-pads and verifies all CPU contents,
  checks cross-buffer PA uniqueness and retains through reboot. No IOVA,
  SID0 attach, initialized register list or GPU writes. Maps only first16KiB
  of captured GPU window and reads18 pinned raw RBBM/CP registers. Success
  is storage/readability only, not ownership/halt/clock measurement/rendering.
  Fresh post-clear guards before/after allocation, before each MMIO and at
  completion; one-shot and existing GMU/DDRfloor retained. Claude review
  adopted raw guard logging and smaller window. GX software-collapse bits
  are diagnostic; CFG UP/DOWN completion + SPTPRAC are required. No inferred
  PWR_ON control-bit assumption on this POLL_CFG_GDSCR device.
  ASan/UBSan actual adapter passed34 state/data cases,18 all-ones registers,
  21 timed guard failures plus existing CM3/HFI/CONFIG/DCVS cases; ARM64
  target-header probe/adapter passed. Exact3target forward/reverse and full
  126-155/46sources/YAML passed (gpu-context-series-6zn9pcbp). Logchecker
  four synthetic groups passed. Pinned18 offsets/FDT checks passed.
  Evidence build/a618-0155-{local-checks-passed.txt,profile-check.json}.
  FullCI passed; temporary boot/device result tracked in ACTIVE0155 above.

- ACTUAL0154: owner confirms iOS loaded and returned to recovery. Fresh
  gmu-dcvs-0154-20261107T112417Z capture SHA256
  a65e81bd6b9e2f5eb0c3943ad4bcfc4bd0e983315f635152d765db3fd8712e78;
  payload159938/flush11/no wrap or decode errors. Initial HFI, CONFIG and DCVS
  summaries all pass. DCVS rc0/request1/ACK1/return_valid1/return0;
  response_clear1/request_clear1/cleanup0/abandoned0/service0/late_ACK0.
  IRQ0/0/GX28, SMMU global0/FSR400/FAR0/syndrome0. Request acceptance only:
  ATLEAST/NONBLOCK does not measure180MHz, start SQE or prove rendering.
  Phone confirmed recovery. Next: GPU register readiness and inactive memory
  preparation, with separate GPU-client ownership/mapping still required.

- OFFLINE NEXT CP INPUT: sweet_a618_pwrup.c/.h/profile.h/_test.py plus
  tools/import-a618-pwrup-profile.py serialize4KiB register-list page from67
  captured values; pinnedstock IFPC38/shared28/A615extra1, header16/list134/76.
  Unlinked/no caller/no MMIO/no0154 inclusion. SHA-pinned source constructor
  comparison ASan/UBSan passed10002snapshots/67offsets/4096capacities plus
  counts/overlap/canaries. Target-header ARM64 compile passed. Evidence at
  build/a618-pwrup-offline-0154/verification.json and pwrup.arm64.s.
  Still needs initialized hardware-register capture and GPU-client mapping.

- ACTIVE0154: full XNU CI 42366861275 SUCCESS, compiled source c6171a99cde04de920eb98784e744257ed51d7e2.
  Completed exact preflight/build/final source and kernel checks. Selective
  CRC/SHA download,21actual kernel markers, reproduced payload,10segments,
  Androidparts and cfg1/profile167/dcvs1 verified. KernelSHA256
  f64f8054bf7c4663d4f2115a6d895a35a23f21d683c2f0dd64e4e7f0973e0f48.
  ImageSHA256 d4cd837db65bce3f27a0e7ef7582de636a3fdec5bc2301282ec1f94cac42ea5e, 17301504bytes.
  Temporary fastboot boot 2026-11-07T11:24:17.017148+00:00: Sending/Booting OKAY.
  Evidence build/xnu-memory-probe-42366861275/boot-attempt-20261107T112417Z.json and verification
  manifests. No partitionflash. User asked1-2min/no touches/recovery because
  jtag1/wfi0; iOS outcome and fresh DCVS success are recorded above.
  Capture prefix gmu-dcvs-0154-20261107T112417Z; watch-dcvs-0154-recovery.py reads
  once, rejects unchanged actual0153b baseline, saves initial/config/DCVS
  summaries. Do not rerun boot merely because a capture watcher expires.
  Unlinked powerup-page helper was committed later (main6b084c9/publicc27dd35),
  is NOT present in this kernel and has performed no GPU MMIO.
  Further pinned-source mapping findings at build/a618-mapping-findings-20261107.json,
  source hashes/URLs at a618-mapping-references-20261107.json. Stock ring32KiB,
  readonly/nonprivileged; scratch/pwrup privileged RW, SQE readonly executable.
  Existing PTE/publisher have no explicit NOEXEC support; plan GPU mapping
  permissions separately without changing the working GMU profile. SID0,
  ownership/retention and initialized register capture still unimplemented.

- PREPARED0154 opt-in DCVS integration: explicit dcvs1 requires cfg1/profile167/
  hfi1/start1 and config_rc0. Persistent global CAS, same-session guards,
  retained bootOOB/DDRfloor/memory; no retry/SQE/rendering. Claude review
  accepted core integration; sticky ACK now returns-3 after request-clear.
  The model initially failed because it did not publish firmware RETURN
  alongside ACK; corrected model now matches the response protocol.
  HostASan/UBSan integrated10paths/helper33failures/stock6writes passed;
  ARM64target-header helper/probe/adapter passed. Full126-154/45sources and
  exact5target forward/reverse passed (gpu-context-series-nln66s57).
  DCVS summary5synthetic groups passed. Build gate report at
  build/dcvs-0154-local-checks-passed.txt. HardwareDCVS/fullCI passed; see ACTUAL0154 above.
  All source under D, dirty tools/mkiosroot.sh remains untouched. Phone recovery.

- ACTUAL 0153b CONFIGURATION SUCCESS: owner confirms iOS loaded/recovery.
  Fresh capture gmu-hfi-0153b-20261107T105525Z.bin/.txt plus both summaries;
  SHA25654cf99c5e9ddbb69774c5fcd426f97dd34ae58a9be3529ba139c1594397e0504,
  ring total155752/flush9/no wrap, differs from0152 preboot capture. Boot chain
  evidence above pins compiled c0b72da/CI42364489199 and verified image.
  Profile167 binding0, GPU8/GMU2, initial1/4/max1. PERF/BW/TEST all attempted,
  published and ACKed with err0; CMD7/7->50/50->210/210->212/212.
  done rc0/phase15/configured1/next6/TXclosed1/poisoned0/observations3.
  Samples0/1/10s hostIRQ0/AOIRQ0/GX28/HFI1/MSG20/20/DBG0/0/CMD212/212.
  SMMU global0/FSR400/FAR0/syndrome0. Watcher33795 completed0. This proves
  configuration exchange and bounded health, not frequency/SQE/rendering.
  Phone recovery. Next integrate already-tested DCVS180 prototype behind
  explicit opt-in, global one-shot and retained successful configuration;
  preserve DDRfloor/bootOOB/memory. No userdata changes authorized by this test.

- OFFLINE CP PREP: new sweet_a618_cp_init.c/.h/_test.py, unlinked encoder
  only. Pinnedstock parity/type7/ordinals comparison passed1048575pages plus
  invalid/canary cases underASan/UBSan; ARM64 target-header compile passed.
  No driver call/bootflag/patch, no GPU mapping or execution. Requires mapped
  initialized4KiB stock powerup-register-list page, not guessed zero address.
  Reference adreno_a6xx.c + adreno_pm4types.h pinned hashes in runner;
  private build/a618-cp-init-offline-0153b. FDTbinding report/script at
  build/k6a-gpu-iommu-bindings-20261107.json and inspect-k6a-gpu-iommu.py:
  gfx userSID0/secure2, GMUuser4/kernel5. Existing context helper rejectsSID0
  by design; separate reviewed GPU mapping path still required. No MMIO done.

- ACTIVE 0153b: full CI 42364489199 SUCCESS at 2026-11-07T10:46:34Z,
  compiled source c0b72da1a1b1dfb60b38a8ff619c7202d876caa3. Exact preflight,
  build and final actual-source/kernel checks all passed. Selective download
  6546438 compressed bytes passed CRC/SHA256; kernel SHA256
  d72a79aefd5cf1d5c66b1e0d33819f5211b61d733bbf3c1bf496d5595a48f6d7.
  Actual kernel has all 17 required markers. Reproduced complete payload,
  independently compared 10 kernel segments and Android boot parts, verified
  cfg1/profile167 flags. Image SHA256
  d8451ccb60dcdee8dc7aea4dfad492073706028afe1e5d4a27718ce09f041077.
  Temporary boot at 2026-11-07T10:55:25Z: Sending 16896KB OKAY (0.407s),
  Booting OKAY (0.152s), total 0.583s. No partition flash. Device configuration
  result and iOS boot are now confirmed in ACTUAL0153b above.
  Evidence: build/xnu-memory-probe-42364489199/{ci-evidence.json,
  kernel-verification.json,hfi-image-verification.json,
  boot-attempt-20261107T105525Z.json,active-boot-record.txt}.
  Recovery watcher session33795/watch-hfi-0153b-recovery.py completed0;
  prefix gmu-hfi-0153b-20261107T105525Z, preboot baseline is actual0152.
  Owner returned to recovery; both initial and config summaries passed.
  Current public HEAD9810c9a includes unlinked DCVS/CP prototypes; those are
  NOT part of compiled c0b72da kernel. Main6c4dae9, dirty mkiosroot preserved.
  NEVER USE failed42362646988: it contains previous code, not configuration.
  New hardened builder bash syntax passed. Old LFfailure reproduced and fixed;
  new actual-tree positive passed/old0152 negative rejected as intended.

-0153 FIRST CI FAILED verification (Build itself succeeded), run42362646988.
  Actual job prefix confirms0153 skipped atomically: CRLF context for rpmh.c
  and bsd/conf/files failed against server LF. Hence this is OLD0152 kernel,
  never use it. No new image/boot. Fix normalizes7contextCRs; no runtime change.
  Reproduced oldfailure and fixed13target apply/reverse against LF. Fullchain
  checks43sources passed gpu-context-series-_bfzx0zf. Added actual11canonical
  source/build-wiring check inside dxb immediately afterpatches beforecompile.
  Positive0153 tree passes, negative0152 tree rejected. Local log suffix256KB
  and prefix2MB in build/xnu-memory-probe-42362646988; full47MB fetch abandoned.
  Phone recovery. Publish0153b and use only its fresh run/source/artifacts.

- OFFLINE NEXT STEP: sweet_gmu_dcvs.c/.h/test.c is UNLINKED, no driver
  caller/bootflag/patch. Stock extracted trace and prototype ASan/UBSan passed;
  33callback failures, pendingservice/rawFFFFFFFF/stickyACK/cleanuporder cases.
  ARM64 target-header compile passed. Claude fixes adopted (service IRQ must
  not suppress cleanup; raw firmware error distinct from all-ones status).
  Explicit index1/180MHz ATLEAST, BWunchanged; no frequency measurement claim.
  KeepDDRfloor/bootOOB/memory, no retry; future adapter must own global one-shot.
  Files/report build/gmu-dcvs-stock-trace-0153; new pinnedSQE source in research,
  provenance build/sqe-reference-20261107.json. No DCVS in0153 CI/image.
  Confirm actual0153 configuration first before linking next-stage code.

- PUBLISHED0153: main e1fe126/public 6478eb5fcdd62e6ea7e9bcabe87f14844a0f4e6e; push0/dispatch204.
  Run42362646988 created2026-11-07T10:08:07Z, exactpreflight passed, fullBuild running.
  Both committed11canonical raw preflights passed. Target-header ARM64 checks
  passed9C files and persistentC++adapter. Claude agrees with corelogic;
  conditionalinclude correction was already made and tested before publication.
  Keep conservative pending-event rejection as diagnostic-only failure.
  Watcher20892/watch-config-0153-build.py waits fullCI then selectivekernel;
  pipeline46412/prepare-config-0153-image.py requires exactsource/SHA/config
  markers, payloadreproduction/10segments and cfg1/profile167 bootflags.
  boot-hfi-0153-recorded.py tempboot authorized AFTER verification, then ask
  owner1-2min/no touches/recovery; jtag1/wfi0. Prebootbaselineactual0152.
  No new boot yet. Config summary5testgroups and initialsummary8groups passed;
  helper is offline only and is not part of the currently building kernel.

- PREPARED0153: same-session PERF/BW/TEST plus explicit recovery167 profile.
  Live ARC/BCM binding, bounded CMD retirement, per-command attempt/publish/ACK,
  irreversible TEST TXseal and0/1/10s health; no DCVS/SQE/rendering yet.
  ASan/UBSan adapter/transport/profile actualDB,988+30config faults and4324
  initialHFI callback faults passed.126-153 fullchain43sources passed in
  gpu-context-series-ybwjxg00. New getter stays inside ARM64 SWEET conditional.
  Source profile constants reconstruct pinned stock; no rawdump in Git.
  Target-header compilation/fullCI/runtime pending until recorded separately.
  Phone recovery. No new boot/flash. Userdirty tools/mkiosroot.sh untouched.

- ACTUAL0152 SUCCESS: owner confirms iOS loaded and recovery. New complete
  gmu-hfi-0152-20261107T093725Z.bin/.txt/.summary.json,154999bytes flush11 no wrap,
  SHA256d018ffe560be44810539c5013339af1d4e9e26e88d67b7eaaae5b53394feaff5. Watcher60601 completed0.
  CM3ready; HFI rc0 phase9 OOB1/1 SPTP1 HFI1 GX28/status1. INIT1/1 VERSION1/1,
  firmware10110000 (major1/minor17), wire0 legacy. ACK0012047e/00200001;
  CMD7/7 MSG8/8 DBG0/0. Both1s/10s observations clean host/AOIRQ0, noevents;
  SMMUglobal0/FSR400/FAR0/syndrome0. Initial HFI runtime IS NOW VERIFIED.
  No PERF/BW/TEST, registerDCVS/DDRhandoff, SQE commands or rendering yet.
  Next: same-session configuration exchange using prepared packets, per-command
  attempted/published/ACK evidence, retained sequence/queue guards and TXseal
  after possibly published TEST. Preserve RX diagnostics and all power/memory.
  Phone in recovery; no new boot/flash this milestone.

- READY+TEMPORARY0152: fullCI42359475531 PASSED at2026-11-07T09:35:48Z
  for sourcef9ae97ddca30c8e7858105300cf7bb0a34be39e2. Exactpreflight+Build+
  final source/kernel checks, CRC/SHA/13markers, exactpayload/10segments and
  bootparts/flags PASSED. KernelSHA2563fae830047614309b4c2efa94f8c1e7574fae5f7063648bf4efed3da19efb9f6.
  Image 17301504bytes SHA256a55a70b9a5726c1cb1ec55973b9e31da70369c88c4614f5eb3377bfd88055d7e.
  Temporary boot submitted2026-11-07T09:37:25.292025+00:00, fastboot Booting OKAY.
  Evidence build/xnu-memory-probe-42359475531/boot-attempt-20261107T093725Z.json; capture prefix
  gmu-hfi-0152-20261107T093725Z. Owner asked1-2min then recovery/no touches;
  jtag1/wfi0, avoid unattended run. No flash/root-image change.
  watch-hfi-0152-recovery.py waits360s for recovery, reads once and rejects
  unchanged0151 log SHA. If expired, restart only before capture exists.
  Runtime/iOS result pending; do not infer HFI success from Booting OKAY.
  New packet helper is unlinked and NOT part of this image. PERF/BW/TEST and
  GPU submission/rendering, wallpaper/apps/WiFi/BT/cameras remain unverified.

- While0152 CI runs, added unlinked offline sweet_hfi_config_prepare + tests.
  Atomically prepares PERF43/BW160/TEST2 seq3/4/5 after validating every table,
  explicit initial GPU/BW indexes and priorbootvote; samevote differentfreq
  allowed with explicitindex. Rejects aliasing and leaves output unchanged
  on error. Synthetic and captured-profile ASan/UBSan tests PASSED; target
  XNU-header ARM64 compile PASSED. No kernel patch/runtime caller/bootflag.
  Reconstructed fresh recovery BW table, same resources/DDR/CNOC as0142;
  pinned C query and160wordABI tests PASSED. Private reports in live-capture:
  bw-table-recovery-20261107.json and hfi-recovery-profile-consistency-20261107.json.
  FDT initialbin167 level6=180MHz -> GMU GPUindex1, DDRrow4(min3,max4).
  Common FDT/cmd-db hashes verified; all205packets match existingcodecs.
  Native test runner: xnu/gpu/sweet_hfi_config_test.py BUILD_DIR [PERF BW MATCH].
  Actual test build D/build/hfi-config-prepare-20261107. This is packet prep
  only; shared exchange/sequence/lifetime/TXseal completion API still pending.

- PUBLISHED0152 main ebbe6db/public f9ae97ddca30c8e7858105300cf7bb0a34be39e2; source push and
  workflow dispatch succeeded. Exact0150-0152 raw preflight passed in BOTH
  committed trees. Intel CI 42359475531 created 2026-11-07T09:22:35Z, preflight
  passed; Build running at last poll. Watcher66073/watch-ack-0152-build.py
  requires exact source and full success before selective kernel download.
  Pipeline55868/prepare-ack-0152-image.py requires CI/SHA/markers and exact
  payload/10segments/bootparts validation; it does not boot automatically.
  Prepared boot-hfi-0152-recorded.py and watch-hfi-0152-recovery.py use this
  fixed run/source and actual0151 log as preboot baseline. Phone recovery.
  After image verification temporary boot is authorized; request owner
  return to recovery after1-2min (jtag1/wfi0) and capture the new log.

- READY0152 source: removes only redundant full echoed-header equality.
  ASan/UBSan postboot4292callback failures+6deadlines+compact/full ACK+wrongID/
  seq/error/missingVERSION payload passed; adapter/SMMU/CM3 lifetime/no-retry
  passed. Stock receive_ack_cmd comparison8192metadata variants and4096seq
  passed. Summary8groups passed including compactecho and8wordMSGend.
  Full126-152 patchchain/reverse38canonicals/YAML passed gpu-context-series-99w073ef;
  target-header ARM64 compilation passed. Claude agrees; no broader guard
  relaxation or new hardware write. Exact committed preflight/push/CI pending.

- ACTUAL0151: owner confirms iOS loaded and recovery. Fresh complete log
  gmu-hfi-0151-20261107T091550Z.bin/.txt/.summary.json,168742bytes flush8 no wrap;
  SHA256dd39732f409e89940c9cb62e2ea0d509f933b64033cbc0732a3a4df818d241b8. Watcher39814 completed0.
  CM3freshready, OOB1/1 SPTP1 HFI1 GX28/status1; INIT packet consumed(CMD5/5),
  four-word response consumed(MSG4/4), ack0002047e/00100000, firmware_error0.
  Local whole-request-header equality rejected the valid ID0/seq1 echo with
  omitted length (sent00100500). INIT flag1/0, VERSION never attempted.
  Pinned kgsl_hfi.c receive_ack_cmd254-280 only compares sequence. Our codec
  already compares command ID+sequence and validates outer ACK/type/error.
  Prepared0152 removes only the redundant full-header equality; keeps all
  framing, identity, error, VERSION payload and hardware lifetime guards.
  Tests/CI/new boot outcome pending until recorded below. Phone in recovery.

- TEMPORARY0151 submitted at 2026-11-07T09:15:50.227674+00:00 after all CI/image checks.
  Source27c643ed47b882e0fb7c82c8a2ad968e29054c57, imageSHA256
  6b369f46cfb2f4487539ab121b6fef4042b636ee0bf02196e111aed25a884456.
  Recovery -> bootloader -> fastboot boot: Sending OKAY0.399s, Booting OKAY0.152s.
  Private evidence build/xnu-memory-probe-42357699877/boot-attempt-20261107T091550Z.json.
  Owner asked to wait1-2min, avoid touches, return recovery and report iOS result.
  Watcher39814 (watch-hfi-0151-recovery.py) waits read-only for a new log with
  prefix gmu-hfi-0151-20261107T091550Z; timeout is360s. If expired, check device
  and restart the same watcher only if its capture does not already exist.
  No flash/root-image change. jtag1/wfi0; do not leave this test unattended.
  Hardware HFI/iOS outcome still pending; fastboot OKAY is submission only.
  Build/docs publication mainb6dcd98/public9489b10 succeeded; docs-only push
  does not alter the compiled source identity. Main keeps pre-existing dirty
  tools/mkiosroot.sh untouched.

- READY0151: full Intel XNU CI42357699877 PASSED at2026-11-07T09:12:49Z
  for27c643ed47b882e0fb7c82c8a2ad968e29054c57. Preflight+Build+finalchecks passed.
  KernelSHA2564974844f659ddcb4397cc6eb2d86ec475076c4c5adb38508d76330edc9760e62.
  Temporary image build/xnu-memory-probe-42357699877/shim-boot-smmu-register.img,
  17301504bytes SHA2566b369f46cfb2f4487539ab121b6fef4042b636ee0bf02196e111aed25a884456.
  CRC/SHA/13markers, exactpayload/10segments/bootparts/HFIflags verified.
  Download/build/package complete; hardware outcome pending. Prepared
  boot-hfi-0151-recorded.py and watch-hfi-0151-recovery.py; do not infer boot
  success from this package record. Read the separate boot-attempt evidence.

- Additional recovery evidence while0151 compiles: read-only KGSL/devfreq
  sysfs reports Adreno618v1,7rates180/267/355/430/565/650/800MHz, defaultlevel6
  (180MHz). FreshFDT SHA6378a14e...sameasprevious; every-bin comparison yields
  unique table match167, initialGMUindex1, matching offline PERF candidate.
  Captures recovery-kgsl-profile-20261107.txt, recovery-live-fdt-20261107.dtb,
  recovery-gpu-profile-match-20261107.json under private live-capture directory.
  This is NOT direct fuse proof or voltage validation; candidate remains inactive.
  Native boundedARM64 GETPROPERTY helper compiled with crossGCC/static libc
  against pinned10c33d40 msm_kgsl.h (SHA143747705ad7e4d2d9490f3fc955ac55e1ad1a9c0cc78a64fbd3f0abc17b995d).
  O_RDONLY open returnedEAGAIN beforeioctl; sameattempt filteredkernel log says
  request_firmware(a630_sqe.fw) failed-11. RAMhelperremoved; no forced retry,
  firmwarepath change or clocks programmed. Querycode/build/capture scripts in
  D/build/kgsl-speed-bin.c and capture-recovery-speed-bin-native.py; failed
  evidence recovery-speed-bin-native-20261107.json. Pythonctypes/array attempts
  failedimports beforeopen. Recovery clock OPP logs are selective, notfulltable,
  and their uV-labelled49/385/417 are regulator encodings, notphysicalvoltages.

- Published0151 main3ce46d9/public27c643ed47b882e0fb7c82c8a2ad968e29054c57;
  exact preflight passed in BOTH committed trees, publication guard/push passed.
  Full Intel XNU CI42357699877 created08:58:19UTC, preflight passed and Build
  in progress. Watcher76455 (watch-sptp-0151-build.py) downloads only on success;
  package pipeline8735 (prepare-sptp-0151-image.py) verifies CI/kernel/segments
  and creates an image without booting. Owner is back; once fully verified,
  temporary boot is authorized, then request owner recovery return/newlog.
- Offline log summary now reports progress/stop stage/unattempted operations;
  missing VERSION before that stage is not labelled incompatible firmware.
  Eight test groups passed including synthetic0150-shaped GX rejection.
  This tool/doc update does not change the0151 kernel or require another CI.

- ACTUAL0150 result: owner confirms iOS loaded and recovery. New capture
  gmu-hfi-0150-20261107T085023Z.bin/.txt/.summary.json under private research/
  sweet-k6a-live-capture-20261027;145624bytes flush7 no wrap, binarySHA256
  052cd36d0428c99933f19ed1aac53b2b5f1348e06efcf1f256e854d809bd50a1.
  CM3freshready0/BABEFACE again. OOBrequest/ACK1/1; GX0x28 (offbitsclear,
  SPTPbit3alreadyon), host/AOerrorIRQ0. SMMUglobal0/FSR400/FAR0/syndrome0.
  HFI rc-3 phase3, SPTP0/HFI0, INIT0/0 VERSION0/0; no queue messages.
  Exact stop is our unsupported requirement that SPTP start off. Pinned stock
  a6xx_gmu_sptprac_enable759-781 unconditionally writes0x778000 then pollsbit3;
  fw_start1096-1115 calls it after OOB without requiring an off-to-on edge.
- Prepared0151 removes ONLY that guard; preserves stock write, bounded full
  status check, priorfresh CM3/OOB/HFI/queue guards and allmemory/powerholds.
  Host ASan/UBSan3219callbackfailures across0/8/0x28 passed; contradictory/off/
  allones paths stop before HFI. Integrated adapter + actual SMMU/CM3 helpers,
  retainedlifetime/no-retry tests passed including8/0x28. Stock16trace cases
  and target-header ARM64 engine compile passed. Full126-151 apply/reverse,
  38canonicalsources/YAML passed gpu-context-series-t48wg17l.
  Added exact0150+0151 preflight chain against immutable public0149 baseline;
  must check committed raw bytes before publishing. Claude review agrees;
  adopted delayedsettling/exactly-one-SPTPwrite/post-HFI-SPTPloss tests. Do NOT
  reject transitional ON+OFF before the write; boundedpoll handles convergence.
  ACTIVE is deliberate; default A618 IFPC skips manualSPTP. Our combined0xdc
  predicate is stricter than stock bit3-only startup poll, appropriate only
  while ACTIVE remains selected. Reviewer bit5 recollection is not adopted.
  Full0151 CI/image/hardware pending. Phone remains in recovery.

- Owner returned; temporary0150 boot submitted 2026-11-07T08:50:23Z.
  Rechecked successful CI42344518565, sourcecdcc69b, kernel SHA/13markers,
  exact payload/10segments/shim/DTB/flags. Image SHA remains
  bc65d34323b2f6eae22646d5ec0b21cc99469e3f1e66de87a8e3b3b1f9613af2.
  Saved preboot4MiB ring: gmu-hfi-0150-preboot-20261107.bin/.txt under private
  research/sweet-k6a-live-capture-20261027; total235500, flush17 (old0148).
  Recovery -> bootloader -> fastboot boot succeeded: Sending OKAY0.405s,
  Booting OKAY0.155s. This is submission evidence, NOT an observed iOS/HFI boot.
  Private boot-attempt-20261107T085023Z.json records hash/time/command result.
  Owner asked to wait1-2min, avoid screen touches, return recovery and report.
  Do not leave diagnostic wfi=0 running unattended. No flash/root-image change.
  Read-only recovery watcher40539 (watch-hfi-0150-recovery.py) will capture a
  distinct new log and summarize it; actual outcome pending at this checkpoint.

- Final handoff: mainff0e0bd committed; public753a8dab0af206256272c8c793b0252ae0a60221
  pushed successfully (docs/offline log tool only; compiled kernel remains
  sourcecdcc69b). Publication pattern guard passed. Public worktree clean;
  main only pre-existing tools/mkiosroot.sh dirty, left untouched. Final
  read-only ADB get-state: recovery. No test boot/flash during owner absence.
  All CI/download/package/export processes completed; no autonomous boot or
  outstanding CI is running. D free4,094,763,008 bytes at final check.
  GPU rendering, PERF/BW/TEST runtime completion, wallpaper, WiFi, Bluetooth,
  cameras and installed-app icon visibility are NOT claimed fixed. Apps32
  is a verified unbooted full image; preserve current userdata until a separate
  destructive-write decision. Next required runtime evidence is0150 recovery log.

- READY0150 temporary HFI image, NOT BOOTED: full Intel XNU CI42344518565
  PASSED at06:07:59UTC for cdcc69b4001ea9adea3f639fd2bfb39ff9c75171.
  Exact preflight, Build and final source/kernel checks all passed. Selective
  kernel download only6,542,254 compressed bytes; CRC/SHA and13 markers passed.
  Kernel SHA256698e76316e00bfec51c812ab9f7fba23d9a1f1ad0927a1974823ad74712f96fc.
  Image build/xnu-memory-probe-42344518565/shim-boot-smmu-register.img
  17,301,504 bytes; SHA256bc65d34323b2f6eae22646d5ec0b21cc99469e3f1e66de87a8e3b3b1f9613af2.
  Exact payload reproduction, independent comparison of10 kernel segments
  (zero chained fixups), boot shim/ADT/DTB/firmware and HFI flags PASSED;
  see kernel-verification.json and hfi-image-verification.json there.
  Initial packaging checker wrongly expected the entire Mach-O container as
  a substring of flat payload; fixed to the actual segment representation and
  reran successfully. Image bytes unchanged. Watcher38564 completed0; original
  pipeline8458 exited1 at that old checker, then direct corrected verification
  passed. Do not treat that earlier pipeline exit as an unresolved kernel error.
  Phone has NOT been booted or flashed this turn; leave recovery while owner
  away. Image uses jtag=1/wfi=0 and retained power, so no unattended boot.
  Next owner-present action: temporary boot this verified image, allow1-2min,
  return to recovery and capture a NEW log. Do not flash the apps image without
  confirming replacement of current iOS data. Last hardware evidence remains0148.
- Added tools/gpu-log-summary.py + seven offline test groups (PASS). Decoder
  validates SWEETLOG length/version/ring and refuses successful HFI inference
  from missing/duplicate/reordered/malformed/wrapped records, ACK/queue/version
  contradictions and error completions. Actual0148 binary reports CM3-only,
  expectedexit3. Positive HFI fixtures are SYNTHETIC, not phone evidence.
  No device I/O. Fresh capture/source identity still needs separate boot record.
- HakiOS refreshed/pinned to aa7f8e463c786502d93d574a58e3f4351eaaa1a4.
  All15 selected source files verified by Git blob/SHA256/length in private
  research/hakios-alioth-source-aa7f8e46/manifest.json. Selected GPU/GLES/WiFi/
  BT/camera files unchanged from previous cache. Changed inject_ui.c concerns
  third-party notification prompts, not A618 or wallpaper. New head's display
  timing claims are upstream POCOF3 measurements, not ours. No blindly copied
  driver. The prior moving-branch cache is now tied to exact current blobs.

- APPS IMAGE READY, unbooted: artifacts/ios16-root-sweet-k6a-20H392-apps32-experimental.simg
  12,145,201,660 bytes; SHA256fbf32671014ab8501b132e447eafa0316216d2f037c5ae3f41f290ef23e1f038.
  Expanded16GiB SHA2569e52a7ef6aa960f5d5a6d18e45bdf0ae76a0bef8fdc3cbd162d5aeb0adafd05a.
  Built locally from existing original mg-nowait sparse base +2.4MB QCOW.
  All32 promoted bundles retain inode/uid/gid/mode/Info SHA. HFS check0, QCOW
  check0, base+overlay opened O_RDONLY, overlay hash unchanged. Full exported
  sparse image has no DONT_CARE; all16GiB compared byte-for-byte with prepared
  filesystem. JSON manifest records hashes and unbooted/deployed=false.
  Export/FUSE/loop cleanup verified. No phone write or reboot. This FULL image
  replaces current iOS data if flashed; never apply as a delta. LaunchServices
  registration/visible icons not boot-validated; feature-tagged apps may still
  be filtered. No wallpaper/GPU/WiFi/BT/camera fix in this root image.
  D free about4.15GB after export; do not duplicate another full root image.
- Maintenance: restored unchanged historical NOTES suffix byte-for-byte from
  8366bc1 after Windows default-codepage reads re-encoded5 non-ASCII lines.
  Current new handoff retained. Future read/write of notes MUST specify UTF-8;
  source and images were unaffected. Historical pre-existing text preserved.

- Corrected0150 published main6391a32/buildcdcc69b4001ea9adea3f639fd2bfb39ff9c75171;
  CI42344518565 started05:52:08UTC. Exact preflight reached Build; no completed
  result yet. Watcher38564 (watch-service-0150-exact-build.py) downloads only
  after success. Pipeline8458 (prepare-exact-hfi-image.py) requires exact
  preflight + Build + final verification, CRC/SHA, then packages/verifies the
  actual image. No automatic boot. HFI image adds existing sweetiolog=- to
  suppress400 repetitive IOK matching lines; driver behavior unchanged.
  Raw38source reproduction also PASSED hfi-exact-ncnoqcur (no text normalization).
- Obtained failed CI bounded262144-byte job-tail.log using a positive HTTP
  range; it confirms0150 reverse-check failed for all5files. Build succeeded
  but the intended0150 source was NOT validated. Earlier full-log fetch was
  abandoned after exceeding its32MiB bound; no kernel artifact from failedrun.
- Claude reviewed futurePERF/BW/TEST API, not hardware. Adopt future explicit
  sequence/index guards, per-message publication/ACK evidence, shared exchange,
  TX seal after potentially published TEST, separate post-TEST observations.
  REJECT its unique-boot-vote rule: verified180/267MHz share00400202. Use an
  explicit initial performance index whose vote matches instead. Design is
  documented, completion API is NOT implemented; current0150 still INIT/VERSION.

- CI42342878712 FAILED final verification after Build step succeeded
  05:29:17-05:44:50UTC. No kernel downloaded or image booted. Exact raw-source
  reproduction found0150 was based on MAINf1b9b2f transport EOF CRLF, while
  PUBLIC0149(4a0bc2a) has LF there. Prior Windows fixture explicitly restored
  wrong main bytes and masked this divergence. Do not rely on that old check.
  Regenerated ONLY0150 against actual published4a0bc2a blobs; runtime canonical
  code unchanged. Added tools/verify-gmu-service-patch.py: all5 baseline/final
  Git blobs, exact apply/reverse, no newline normalization. It rejects broken
  96f6626 at both transport EOF contexts. New workflow runs this BEFORE Build,
  fetching the exact baseline object if absent. Full126-150 checks still pass
  gpu-context-series-ls4j6a89; corrected fullCI remains to run.
  Full failed-job log retrieval encountered network problems; do not invent
  its exact failing command. Local raw apply defect is independently reproduced.

- Published final0150 source96f66268b84cee3abdb50009bbdfb7f102ad42a2;
  full Intel XNU CI42342878712 started05:28:34UTC, still in progress at this
  checkpoint. Main9c53cd8 and public blobs are byte-identical for all16 changed
  source/patch files. Raw Linux0150 apply check passed. Phone not booted.
- Added offline tools/gpu-perf-table.py and stock-comparison test. Explicit
  recovery FDT bin167 resolves8GPU/2GMU entries; all ARC votes and whole43-word
  PERF packet match unchanged stock functions under ASan/UBSan. Initial test
  compile lacked stdbool.h in its shim; corrected and rerun passed. Original
  bin167140MHz is rejected (absent clock OPP); bin0level416 rejected because
  MXmax384. These are candidate data, no runtime caller or active-fuse proof.
  Private generated candidates remain D/build/perf-profile-167-check. Read-only
  recovery debugfs OPP/clock paths are unavailable; no clock writes attempted.
- FrontBoard capture completed with WAL; all32 staged identifiers absent from
  its77identifier rows. Camera/Safari/Photos/Settings identifiers are present;
  absence from FrontBoard alone is not a complete LaunchServices diagnosis.
  No app changes on phone. FUSE/loop capture mounts confirmed gone.
- Preparing full apps32 experimental sparse image from original mg-nowait
  base+existing2.4MB QCOW overlay, entirely on D. Reader/export/checks only;
  do NOT flash as delta onto current userdata. Full export/verification pending.

- Final0150 publication audit found three transport files retained one legacy
  CRLF EOF in main Git blobs while public blobs and generated0150 patch used LF.
  Normalized the three main files to LF, preserving semantics. Generator and
  full126-150/38source/YAML checks pass (gpu-context-series-mzi2gigy).
  CI42341729161 and42342506500 were cancelled as superseded; neither is a
  completed build validation. Next full CI must use byte-identical sources.
  FrontBoard read-only capture completed: 77 application identifiers, 140
  parsed /Applications bundles and32 staged bundles; WAL included. Files are
  private under research/.../frontboard-20261107. Apps/UI cause under analysis;
  nothing installed or modified on userdata. Phone remains recovery.

- Prepared0150-sweet-gmu-service-queue-health.patch after completed Claude
  implementation review. Fixed two real gaps: DBG may already contain records
  after CTRL_INIT, and late ERR events could previously be missed during health
  observation. Added bounded MSG/DBG receive/drain, event classification,
  per-queue indexes in samples, reject unexamined/side events, preserve ACK
  diagnostics across DEBUG. ERROR never becomes a successful health result.
  Host ASan/UBSan1073callbackfailures + early/late events in both queues passed;
  persistent adapter model and dedicated MSG/DBG wrap/invalidqueue tests passed.
  Target-header ARM64 engine/transport/ARC/probe/RPMh/adapter passed. Full
  126-150 apply/reverse/38source/YAML passed gpu-context-series-fged1rye.
- 0150 patch preserves canonical mixed newline bytes in legacy transport EOF.
  Windows autocrlf fixture initially obscured the difference (no semantic code
  discrepancy). New generator uses exact git blobs; raw canonical forward and
  reverse checks passed, including independent Linux git apply. Full Windows
  fixture normalizes ONLY after proving0149 content equals committed sources,
  then applies0150 with autocrlf=false. Stage0150 patch with autocrlf=false and
  verify committed bytes equal generated bytes. Never regenerate0149 baseline.
- Claude review adopted service-event fixes, fresh-state distinction and clearer
  requested/selected ARC logging. Its >=49 statement was off by one: stock
  subtractsOFFSET1 and requests48, rounded to64 in this database. Did not adopt
  reading IRQ before power guard: avoid potentially unpowered MMIO access.
  Review was read-only, no claimed device verdict. All initial-HFI hardware
  remains pending; full initialization PERF/BW/TEST still separate.
- Additional read-only phone evidence while CI runs: scoped SystemGroup capture
  systemgroup-registry-20261107.json/.console found lsdidentifiers plist5377B,
  lsd iconcache34files and FrontBoard applicationState.db+WAL/SHM. These paths
  were outside earlier scoped registry search. They prove some registry/cache
  state exists, not app registration correctness or wallpaper repair. FUSE/loop
  mountedro with phone O_RDONLY, cleanup completed (findmnt falls back to/mnt/d).
  Only578-byte reader uploaded to recovery/tmp RAM; no userdata writes/reboot.
- Published0149 mainf1b9b2f / build4a0bc2a0d09383f6134c2eda5b8669029cdce012;
  source guard passed, push0/dispatch204. Intel fullXNU CI42341729161 started
  2026-11-07T05:12:24Z, in_progress. Watcher build/watch-postboot-0149-build.py
  verifies head and saves completed CI evidence/downloads kernel only after
  success. Image tools support --hfi and independent actual-image verification.
  NO0149phone boot while user away; prepare image only. Source implementation
  review pending. Final source checks fixturegpu-context-series-b67_54z1.
- Prepared0149-sweet-gmu-gx-hfi-start.patch: explicit sweetgmuhfi=1 after
  successful freshCM3start; same persistent SID5 allocation and no-retry latch.
  ACTIVE(ifpc=0) stock path OOB22/ACK30 -> GX-on guard -> SPTPRAC -> HFI CTRL
  -> INITseq1 -> read protocol version -> FW_VERSIONseq2 ->1s/10s health.
  No PERF/BW/TEST or GPU submission. Cold guards still require GXcollapsed;
  new phase3 permits GX change and checks CX/clocks/reset/retention/SMMU.
  All outcomes retain request/votes/memory through reboot; no timeout cleanup.
  ERR/DEBUG events classified; only matching ACK counts, v2 rejected before
  VERSION. Fresh statuses and queue indexes required, live RX/TX request flags
  may change0/1. No private event text published/logged.
- New bootrail profile is pinned stock180MHz VDD_GX_MIN/MIN_SVS level48+1.
  This does NOT set/measure frequency or identify active speedbin. Neither
  captured FDT has opp-microvolt; both use GPUCC OPP-provider phandles.
  Pinned clk.c creates OPPs from voltage class; gpucc-sdmmagpie and regulator
  binding establish49. Runtime read-only ARC accessor now permits mx.lvl;
  pure calculator derives indexes. Actual verified CMDDB plus unchanged stock
  formula test passed2/2packed00400202. No phone database bytes in git.
- 0149 local checks: host postboot ASan/UBSan673 callback failure points,
  six deadlines, malformed/error/debug ACK handling, stale/unsupported states,
  health/fault guards and no retry. Actual persistent adapter+SMMU/CM3/HFI
  model passed27cold power gates plus GXtransition, ARCerror/timeout/SMMU/idle
  rejection and permanent retention. Pinned stock16path trace passed.
  ARM64 target-header compile passed engine/ARC/probe/RPMh/adapter; final
  request-flag comparison model and target compile passed again. Full126-149 patch
  apply/reverse/38canonical/YAML passed fixturegpu-context-series-b67_54z1.
  Superseded0144config/0147probe/0148adapter reversehunks excluded; final
  source comparisons and exact build-entry checks remain mandatory.
- Claude NEWpost-CM3 architecture review completed; adopted ACTIVEprofile
  distinction, GX guard, fresh triggers, INIT-before-version ordering,
  event classification and delayed health samples. Rejected suggestion to
  read OPPvoltages directly from FDT because actual FDTs have none; verified
  dynamic source above. Focused implementation review pending. Earlier
  classifier-stopped inactive-teardown review remains unrelated, never retried.
- User left for gym for~2hours. Keep phone in recovery; DO NOT temporarily boot
  CPU-idle-disabled/GX-held test while unattended. Prepare verified0149 image
  only, then hardware test when user returns. No newphone writes/boot this turn.
  CI not yet dispatched at this checkpoint. mkiosroot.sh left untouched.
- 0148 hardware SUCCESS at first CM3 initialization. User confirmed iOS boot
  and recovery. Read-only gmu-start-0148.bin/.txt: ring235500 bytes, flush17,
  no wrap; prepare0/install0, phases1-8, rc0 held1 release1 fresh BABEFACE.
  CM3_CFG52, bus/cache read_mask7 and all three reads0. SMMU global0/FSR400/
  FAR0/syndrome0, host/ao error IRQ0 in sampled result. All mappings retained.
  This establishes CM3 initialization, NOT GX/HFI/DMA/rendering. Phone recovery.
  NEXT: implement new one-shot post-CM3 GX/OOB, SPTPRAC and initial HFI exchange
  using pinned stock order; separate post-GX power guard from collapsed-only
  cold-start guard. Preserve DDR/clocks/memory until reboot, no teardown/retry.
  Exact next power profile and live HFI protocol must be validated before use.
- 0148 full XNU CI42338621208 SUCCESS, source
  efb35f2f8c28171f18589e71f07790fcc8adc5d7. Build04:29:17-04:45:23UTC,
  required source/kernel checks04:45:23-04:45:29UTC on2026-11-07. Selective
  download6511833 compressed bytes, CRC/size/SHA passed. Kernel SHA256
  9d211d62abe6d3af99d1328ac7d2f0475453bfaadddec62272ea74d4700d9285.
  New build/verify-gmu-first-start-build.py RUN SOURCE checks saved completed
  CI identity/required steps, SHA and7actual-kernel markers including bus/cache;
  all passed. Evidence in build/xnu-memory-probe-42338621208.
  Built image SHA256
  8eab2c99f8f613244bfcb17053c35eefef61514be60a727fab45d84b5d75188b.
  Exact payload/required flags and targeted recovery verified. Temporary boot
  Sending16880KB0.403sOKAY, Booting0.152sOKAY,total0.566s; no partition flash.
  Asked user wait1-2min, avoid touch and return recovery/report iOS; CPU idle
  disabled. Hardware result recorded above. Fresh BABEFACE is CM3
  initialization, not HFI, GX or rendering. Runtime CI source remains efb35f2; later source-only
  postboot test/docs commit3e3774e pushed0 and did not dispatch another CI.
- Published0148 runtime as efb35f2f8c28171f18589e71f07790fcc8adc5d7,
  source push0/dispatch204, Intel CI42338621208 created2026-11-07T04:28:41Z.
  Watcher build/watch-bus-cache-0148-build.py checks exact SHA, observes step
  changes, saves CI evidence and selectively downloads only after full success.
  Full CI and first-CM3 device result passed as recorded above.
- Publication error/remediation: initially copied ALL main NOTES history into
  publish worktree, unlike its prior concise public history; six occurrences
  of the target serial inadvertently entered public commit a9c649b and run
  42338485517. User informed immediately on discovery. Replaced with original
  public NOTES from3706c62 plus concise0148 handoff; amended ONLY our newest
  commit and force-pushed with exact old-head lease. Verified remote nowefb35f2.
  Runtime code identical. Old run confirmed cancelled; deletion requested.
  Main NOTES serial occurrences replaced with <TARGET_SERIAL>. Added local
  build/check-gpu-publication.py guard to BOTH push scripts, scanning committed
  tree for target identifier and credential patterns before authentication/
  push. Negative control blocks a9c649b; corrected HEAD passes. This does not
  guarantee deletion of dangling/cached GitHub objects. NEVER copy full local
  NOTES to publish worktree again: publish only a reviewed concise handoff.
- Cancelled mistaken CI42338485517 was deleted successfully (API204).
  During corrected0148 CI, added independent host-only stock postboot trace
  sweet_gmu_postboot_stock_test.py. Extracts unmodified pinned GX/OOB,
  SPTPRAC/HFI and parent firmware-start functions; stubs all pre-CM3 work.
  Tests16 combinations of synthetic table/default indices and timeout stages.
  Confirms BOOT0/PRI/SEC writes, host requestbit22/ACKbit30/ACKclearbit30,
  no host request clear on success, SPTPRAC778000/statusbit3/10ms then HFI
  INIT1/statusbit0/100ms. Stock timeout cleanup is reference only, not a new
  adapter policy. ASan/UBSan passed with pinned Makefile's fno-strict-overflow
  and fatal sanitizer errors. Initial harness shadowed device pointer; fixed
  mock name. First run before that kernel flag reported signed preboot fence
  macro1<<31; corrected host flags and reran clean. No production code change.
- Power-index analysis: pinned kgsl_pwrctrl.c772-783 sysfs getter returns
  INTERNAL num_pwrlevels-1; frequency listing also excludes trailing off0.
  DO NOT use captured sysfs7 as internal table count. Offline report
  gmu-power-indices-20261107.json (script build/inspect-gmu-power-indices.py)
  validates both captured FDTs: all bins have final frequency0, default GMU
  index1. Recovery bin167 uniquely matches180..800/sysfs7/default6 => internal8;
  original bin167 has140..800/internal9/default7. This supports prior bin167
  inference but is NOT a fuse read or license to use recovery-modified OPPs.
- 2026-11-07: user confirmed repeated0147 iOS loaded/recovery. Fresh read-only
  gmu-start-0147-retry.bin/.txt has225606 bytes, flush40, no wrap. Firmware
  check0, DDRhandoff0, prepare0/install0 root104700000; phases1..6. Actual
  CM3_CFG read52 passes known NMIbit9 check. Next exact-readback guard fails:
  off1303c SYS_BUS_CONFIG expected1 actual0, rc-7 phase6 held1 release0.
  SMMU global0 FSR400 FAR0 syndrome0. No CM3 execution; iOS userland runs.
  driverkitd SIG9 namespace1/code7 remains. Phone recovery.
- Prepared0148 narrow bus/cache readback correction: stock writes1 to
  SYS_BUS/ICACHE/DCACHE unchanged, explicit named cases only; barrier/read
  errors/allones still abort. Stores read_mask and all3values as diagnostics,
  not verified hardware state. Other comparisons, reset/power/NMI/fresh-init,
  fault checks, one-attempt latch and permanent mapping retention unchanged.
  Pinned stock writes without comparison; snapshot includes the2cache CSRs
  but skips SYS_BUS. Independently checked register-relative conversion.
  Reason read0 remains unknown; no write-only/self-clearing claim.
  Claude reviewed this new scope and agreed with diagnostics/strict other
  guards. Adopted adjacent-register negative tests and snapshot distinction.
  Rejected its erroneous statement that live CM3_CFG was4052 (actual52) and
  its overstatement that zero alone rules out unmapped access. Offset evidence
  is pinned source formula + captured bases, not the zero value.
  No0148 CI/device test yet. Generator make-bus-cache-readback-patch.py checks
  immutable0147 fixture against committed c3ab8cb before producing0148.
- 0148 local checks PASS: sequencer ASan/UBSan138callbackfailure points,
  measured CFG52/SYS_BUS0 plus synthetic three-register read variants,
  each allones rejection before release, strict neighboring config registers;
  persistent adapter27power guards/fault/latch/no-retry tests and diagnostic
  logging. Unchanged stock16-write trace passes all3initial RPMH variants.
  Target-header ARM64 engine/PERF/entry and C++adapter compilation passed.
  Full126-148 apply/reverse,33canonical source comparisons and YAML passed
  build/gpu-context-series-x648yk8k. 0147 reverse excludes only superseded
  engine/header/adapter;0148 full reverse and final-source checks retained.
- 2026-11-07: target found in recovery after user's status request. Read-only
  gmu-start-0147.bin/.txt capture: ring4194304, total4809444, flush3572;
  earliest615140 bytes overwritten. Raw SHA256
  ee8e593ccb23cd4f5cd7e78cb9733c273b96074a3bf41f8abc44f4cf2e763a51.
  Contains112289 touch lines, SpringBoard AKS calls and a backboardd FB call,
  but ZERO SWEET GMU BOOT / SWEET GPU / CM3_CFG markers. Thus the last log
  shows userspace activity but cannot establish the 0147 GMU result or even
  identify its boot kernel from the missing startup banner. Do not infer
  success/failure from the missing lines. Original capture preserved.
- Repeated the SAME0147 image after verifying recorded image SHA256 and the
  boot helper's exact payload/flags checks; no source change, rebuild or
  download. Temporary fastboot boot Sending16880KB0.394sOKAY,
  Booting0.153sOKAY,total0.558s. No partition flash. Asked user for1-2minute
  boot then recovery, without touching screen to limit touch log traffic;
  reminded CPU idle is disabled. Hardware result pending.
  NEXT capture under NEW name: pull-memory-probe-log.py gmu-start-0147-retry.
  Preserve old wrapped capture and require actual GMU markers before making
  startup claims. Existing logger has only sweetlog=0 disabling it, no boot
  prefix preservation; future bounded touch logging could reduce lost data,
  but no such change has been implemented or booted.
- 0147 full XNU CI42265225050 SUCCESS for runtime source
  9f462904e2017879fc5db4155568f0fab0a8bfd8. Build17:51:23-18:12:42UTC,
  mandatory source/kernel checks18:12:42-18:12:47UTC. Initial20minute local
  watcher deadline expired while CI was still building; resumed observation
  of the SAME run, without redispatch. Authenticated CI evidence saved in
  build/xnu-memory-probe-42265225050/ci-evidence.json.
  Selectively downloaded6513372 compressed kernel bytes; CRC/size/SHA passed.
  Kernel SHA256 da831602c74ae9c905a98a790e5967458734eece2671db3d8d8ef5d7d2ffe508.
  Independently verified new CM3_CFG/readback-mismatch, fresh-init, retention,
  BCM handoff and opt-in markers in actual kernel; kernel-verification.json
  records them. Built corrected first-start payload with sweetgpucheck1,
  sweetgmustart1, jtag1/wfi0 and no old SMMU/TCM probe flags.
  Image SHA256 0f8a46fdea87fe793876a32f50040fc8a223cedf4f38e735a4dd45b83143c287
  at build/xnu-memory-probe-42265225050/shim-boot-smmu-register.img.
  Boot helper verified flags and exact payload inclusion, confirmed targeted
  recovery, then temporary fastboot boot: Sending16880KB0.403sOKAY,
  Booting0.151sOKAY,total0.567s. No partition flash. Asked user to wait1-2min
  and return recovery/report iOS; CPU idle remains disabled. Device outcome
  is PENDING: fastboot success does not establish iOS or CM3/GPU execution.
  NEXT: python -u D:/ios-sweet/build/pull-memory-probe-log.py gmu-start-0147.
  Inspect CM3_CFG valid/value, mismatch offset/expected/actual, done rc/phase/
  held/release/init/IRQ, last_io/ok/value, SMMU faults and DDR handoff. Fresh
  BABEFACE would establish CM3 initialization only; GX OOB/HFI/rendering are
  not started by this image. Do not loosen other readbacks without evidence.
- Independent configuration trace added during0147CI:
  sweet_gmu_stock_config_test.py compiles unchanged pinned KGSL
  a6xx_gmu_fw_start/a6xx_gmu_power_config/a6xx_gmu_start against host stubs.
  Stops stock at the readiness poll, before GX/SPTPRAC/HFI; compares its16
  ordered retention/configuration/WFI/reset writes with the actual new engine.
  All match for initial RPMH_CTRL0/80000000/40000000. Trace/input hashes saved
  in build/gmu-stock-config-test. This checks values/order, not MMIO readback
  or firmware behavior. Initial harness build had a shadowed mock gmu name,
  then an omitted reset1 initialization; corrected harness, no runtime fix.
  CI source remains9f462904; no production changes after dispatch.
- Published0147: mainc3ab8cb / build9f462904e2017879fc5db4155568f0fab0a8bfd8,
  source push0 and workflow dispatch204. Intel XNU CI42265225050 created
  2026-11-06T17:50:03Z, initially queued. Authenticated watcher
  build/watch-cm3-readback-0147-build.py verifies source SHA and waits for full
  success before selective kernel download. Reuse corrected first-start image
  builder (includes sweetgpucheck1) and validated temporary boot script.
  Phone remains recovery after0146b. No0147hardware execution yet.
- 0146b device result: user confirmed iOS and recovery. Read-only capture
  gmu-start-0146b.bin/.txt: ring218104 bytes, flush9. Firmware copy/check0;
  DDRhandoff0; prepare0 stage5; install0 state1 retained1 root104740000.
  Phases1..6 reached, so exact32KiB TCM load/readback passed. Then rc=-2,
  phase6 held1 release0 init0, last region0/offset140b4 (CM3_CFG); SMMU
  global0 FSR400 FAR0 syndrome0. CM3 was NOT released; no firmware execution.
  Code deduction: valid boot_read/write always return0 and barrier returns0,
  so sync_write failed because CFG readback !=4052. Actual value was NOT
  logged; no bit-specific measured interpretation is possible.
- Prepared0147: keep stock CM3_CFG write4052, barrier and diagnostic read,
  require only known NMIbit9 clear and not allones. Pinned kgsl_gmu.c41/978-980
  names/uses bit9; adreno_a6xx_gmu.c1062-1067 writes4052 without fullcompare.
  Claude independently agreed, recommended NMI-only predicate and explicit
  mismatch values/error codes; adopted both. No other exact-readback guard
  removed. New rc=-7 records mismatch offset/expected/actual; rc=-8 NMIset.
  State records CFG and last callback kind/success/value; entry logs firmware
  getter and failed reset/idle guards. Bootflag validation now requires
  sweetgpucheck1 before power acquisition. Lifetime/oneattempt/TCM/freshready
  and all fault/power guards retained. Tests use synthetic CFG variants, not
  a claimed measurement. Full126-147 patch/reverse/33source/YAML check passed
  fixturegpu-context-series-76k1x66p. ASan/UBSan sequencer138failurepoints,
  CFGvariants/NMI/allones/exactmismatch diagnostics and composedadapter27power
  gates/fault/lifetime tests passed. Target-header ARM64 Cengine/PERF/entry/
  C++adapter assembly compiles passed. No0147CI or phone test yet.
  Private make-cm3-readback-patch.py builds against
  preserved0146 fixture, writes gpu-start-0147; never regenerate0146 in place.
- 0146a device result: user confirmed iOS and recovery; read-only capture
  research/sweet-k6a-live-capture-20261027/gmu-start-0146.bin/.txt contains
  210996 bytes, flush8. CX/memnoc/GMU clock and all three DDR requests passed.
  GMU entry logged its power/GX checks, then entry rc=-3 before prepare,
  install, any boot phase or CM3 release. GPU firmware did not execute here.
  Found a concrete image-packaging defect: actual payload omitted
  sweetgpucheck=1. Patched IOKitBSDInit.cpp783-786 invokes the only firmware
  store behind that flag; otherwise ready stays0 and getter must fail.
  Claude independently confirmed this path and that repacking suffices.
  Last reset/retention/busy/init reads are not logged at entry, so the missing
  flag is a sufficient cause, not proof that no other guard failed as well.
  Existing modeled getter assumed firmware ready and missed this integration
  dependency. driverkitd SIG9 namespace1/code7 persists; no clean-boot claim.
- Repacked SAME verified kernel as 0146b, with sweetgpucheck=1 and diagnostic
  sweetgpubundle=1. Fixed build/build-gmu-start-image.py, including command-line
  size/required-flag assertions. Extended build/boot-smmu-probe.py to verify
  all first-start flags (including firmware store) and exact payload presence
  in the actual boot image before any reboot. Bundle's four files/81920 bytes
  reverified against their captured inputs; no firmware/root download or XNU
  rebuild. Preserved 0146a image/payload/script as *.0146a-no-fw-check.
  New image SHA256
  5d52fd40e18f446bb69d07c4b43d8c9006dc5ac94530f6b5ada690abaab7a5c5.
  Target recovery confirmed; temporary boot Sending16880KB0.401sOKAY,
  Booting0.151sOKAY,total0.564s. No partition flash. Asked user to wait1-2min
  then return recovery and report iOS; CPU idle remains disabled.
  NEXT: capture gmu-start-0146b with pull-memory-probe-log.py. Require firmware
  copy/check0 and inspect GMU prepare/install/phases/done/release/init/IRQs
  and SMMU faults. If entry still returns-3, add precise entry diagnostics;
  do not assume the remaining silent reset guards passed. No GPU acceleration
  or GMU firmware execution established yet.
- 0146 fullXNU CI42259603028 SUCCESS for runtime source
  b3a15e3d68f5498fe767402f34cb01b150562f50. Build17:13:50-17:28:55UTC,
  mandatory source/kernel checks17:28:55-17:29:00UTC. Selectively downloaded
  6514567compressedkernelbytes; ZIPCRC/size/SHA256 passed. Independently checked
  five actualkernel first-CM3/retention/bootarg/DDR markers.
  KernelSHA256 c85df6bd27de1104527b61876d3e721d98b1a1f0cd662cb1be73f6259eb44673.
  Image D:/ios-sweet/build/xnu-memory-probe-42259603028/shim-boot-smmu-register.img
  SHA256 f23d4b2e4ead9b3040c91f2a6b0313934a677a4ce9b0eb14ac6c561aa0b8b0ea.
  Actualpayload flagschecked: sweetgmustart1 +samebootbw/power/clock/status,
  jtag1/wfi0, rd=ufsroot0; no inactiveSMMU/TCMprobe. Targetrecovery confirmed;
  temporary fastbootboot Sending16880KB0.397sOKAY/Booting0.153sOKAY,total0.561s.
  No partitionflash. This proves image delivery only: useriOS/CM3 resultpending.
  Askeduser towait1-2minutes andreturnrecovery, shorttestbecauseCPUidleoff and
  GMU/HFI notcompleted. NEXT: pull-memory-probe-log.py gmu-start-0146;
  inspect SWEET GMU BOOT begin/prepare/install/phases/done rc/held/release/init,
  IRQ/PDCbefore/lastoffset andSMMUglobal/FSR/FAR/syndrome plusBCMhandoffrc.
  FreshBABEFACE wouldproveCM3initializationonly, notHFI/DMA/GPUrendering.
  No reset/retry/teardown afterattemptedrelease; mappingsretaineduntilreboot.
- Added offline sweet_hfi_codec_stock_test.py while0146CIruns: extracts pinned
  stock INIT/version functions, ACKreceiver, messageIDs/header/sequence macros
  and A618 gpmu version. Host transport captures exact stock packets; ASan/UBSan
  passed all4096sequences, headerlength/ID combinations, ACKerror/mismatch,
  allmessage types/IDs, truncatedbuffers and invalidarguments. Local decoder
  intentionally adds ACK-ID/command-ID checks beyond stockreceiver; documented
  rather than claiming identical acceptance. InputfileSHA256 saved outsidegit
  in build/hfi-codec-stock-test/stock-inputs.json. No runtime changes or HFI
  deviceexchange;0146 still builds original sourceb3a15e3. At17:25UTC CI
  stillBuild/in_progress and targetedadb confirmsrecovery. Originalwatcher
  process disappeared afternewmessage; restarted authenticatedwatcher.
  Main9b6b8b9 / publish1e477f50b6b19509de80dab846ed4951fdf3a8ed, source-onlypush0,
  no extraCI. Negativecontrol substituted old GMU1.10 in outsidegit scratch;
  independentstockprofile test failed atversionassertion as expected. Canonical
  runtimecode unchanged; sourceb3a15e3 remains0146artifactidentity.
- Prepared0146 NEW first CM3 coldstart (sweetgmustart1); temporarybootabove,
  device CM3 resultpending.
  xnu/gpu/sweet_gmu_start.c/h/profile.h + sweet_gpu_gmu_start.cpp, separatefrom
  inactiveSMMUprobe. FullSID5map installed, memorylatchbeforeANYenginewrite,
  allocations/context/clocks retaineduntilreboot onalloutcomes; no remove,
  destroy, automaticreset, retry, GX OOB, SPTPRAC orHFIinitialization.
  Optinrequires k6a/gpuprobe/power/clocks/status/bw flags,jtag1/wfi0, rejects
  oldTCM/SMMUtestflags, requires samebootDDRrc0, returnsfromGPUprobeafterattempt.
  Namedprofile offsets frompinnedstock a6xx_reg.h;48PDCwrites matchunchanged
  _load_gmu_rpmh_ucode compiled inhostreference. ReadsPDCenable/RSCbusy/control
  beforewrites, requiresbusy/control0; intentionallyreplacesinheritedPDCprogram
  onfirstdriverboot. Claudeplanreview suggestedrejectenabledPDC, butactualstock
  adreno.c4159isresumehandling andfirstGMU_BOOT_INIT_DONEfalse reloadsprogram;
  enabledPDC alone doesnotprove liveCM3, so that claimwasnotadopted. AddedIRQ
  statuspolling fromreview: CM3bit15/AObits0,3,5; FSR/FAR/syndromedump.
  ACTIVEprofile usesreadRPMH|f11, rejectsinitialMINBW/NAP, noHYSTwrites,
  CFG4052,WFI0, exactTCMfile32768bytes nozeropadding. FreshFWinit0thenreset0,
  100msdeadline;BABEFACEmeansCM3initonly, notHFI/DMA/rendering. No dump/log
  patternfill (stockzero buffers kept). jtag/wfi areXNUCPUflags, notCM3debug.
  SourceengineASan/UBSan138failurepoints/stock48writes/offsets/TCM/readback/
  IRQ/stale/timeout/one-shot passed; persistentadapter+actualChelpers model
  passed27powergates/allnonFORMATfaults/latch/timeout/no-unpin-or-free/retry.
  ActualXNUheaderARM64compiles passed Cengine/PERF/entry/C++adapter. Full126-146
  apply/reverse/33canonicalfiles/YAML passed fixturegpu-context-series-i2gzj73u.
  Patch0146also links correctedPERF4/TEST5 codecs, noHFIcaller. Old0145probe
  reversecontext superseded, exactcanonicalprobe comparison retained. Moved
  buildlist entries andentryvalidation tokeepold0134/0142reversechecks intact.
  Mainc005cbb / publishb3a15e3d68f5498fe767402f34cb01b150562f50; push0/dispatch204.
  CI42259603028 created17:13:12UTC, completedSUCCESS asrecordedabove. Authenticatedwatcher
  watch-gmu-start-0146-build.py waitsfullSUCCESS thenselectivekerneldownload;
  build-gmu-start-image.py prepared adds sweetgmustart1 to0145flags.
  NEW implementationreview completed: Claude readactualnewfiles andfoundno
  blockingorder/offset/lifetime/stale/fault/integrationerror. Its suggestedWFI
  write removal was independently disproven: pinnedkgsl_device.h625-634
  kgsl_regwrite routesoutsideGPUrange to gmu_core_regwrite whenGMUrangevalid;
  kgsl_gmu_core.c191-197/223-244 acceptsword1f802, GMUrelative14008<31000.
  Savedbothpinnedfiles instockcache. KeptWFIwrite0. Optionaldiagnosticlimits:
  exactreadbackmaystopbeforestart onregisterswhosefullreadbackisunproven;
  heldflagcanbe0 afterimpossible/currentAPIinconsistentlatchoutputsbutmemory
  stillretained; postcheckfailureuses-3 distinguishedbyrelease/init fields;
  clocksfailbeforeentry lacks explicitnot-attemptedline butearliergatelogsremain.
  No runtimechangeafterCI dispatch. Phone temporarilybooted0146 asrecordedabove.
  Scripts make-gmu-start-profile.py/make-gmu-start-adapter.py aregenerators;
  do not rerun overlatermanualsourcefixes withoutreconciling them.
- 0144 result: user confirmed iOS loaded, targeted adb confirmed recovery.
  Pulled tcs-0144.bin/.txt: ring232709bytes flush11. tools/gpu-tcs-info.py
  decoded all8banks/128slots, stable1 inventoryrc0. Every bank hadcontrol0,
  enable0,wait0,status1. Disabled TCS0 history includes CN0/SN11/SN0, NOT
  MC0/SH0/ACV. This is no current-vote baseline or preservation proof.
  GMU200MHz clockrc0/stage3, reset1,busy0,init0,retention0. driverkitdSIG9
  namespace1/code7 repeats; no clean-no-crashes claim. GPU not executing.
- Completed0145 temporary boot: full CI42251468013 SUCCESS for runtime source
  1f00ab4f9ca9010d3143f5f4db6bba83cf8db3ff. Build16:21:39-16:40:08UTC;
  mandatory patch/source/kernel verification success16:40:08-16:40:15UTC.
  Anonymous API polling hit403 rate limit; switched watcher/download JSON
  requests to existing gh authentication held only in process memory.
  Downloaded6532892 compressed kernel bytes selectively; CRC/SHA verified.
  KernelSHA256 cc7742636a52fd419f941c0e04a85e3c20dd1d763df8dcb85d5fcb7d09df65b5.
  All4 actualkernel BCM begin/ACK/rc/bootarg markers independently checked.
  D:/ios-sweet/build/xnu-memory-probe-42251468013/shim-boot-smmu-register.img
  SHA2566a4126c8d97fcea92049f9d551b486ffb9a7e6a8e12f2cecbb8f540046fc3547.
  Target recovery confirmed; temporary fastboot boot Sending16880KB0.404sOKAY,
  Booting0.152sOKAY,total0.567s. No partition flash. Bootargs sweetgmubw1,
  jtag1,wfi0, existingclocks/status; NO SMMUinit/gmuload/snapshot.
  User confirmed iOSloaded and returnedrecovery. Read-only bcm-0145.bin/.txt
  captured ring226274bytes flush10. All3payloads exact; done1 IRQ0 idle1,
  statuses10101/10101/10101, ACKcomplete, endrc0 poisoned0 andhandoffrc0.
  This validates observed request completion and queue cleanup, not actual
  DDRfrequency, GMUexecution or rendering. CM3remainsreset. driverkitdSIG9
  namespace1/code7 repeats at645-648. Phone recovery, no pending0145capture.
  NEXT: NEW first CM3 coldstart path with persistent SID5 mappings/lifetime,
  PDC/RSC, IRQmask,TCMretention/load/verify/config andfreshBABEFACEpoll.
  Do not use inactive teardown after attemptedstart. Architecture review
  requested fromClaude; no0146runtimecode/patch/deviceexecution yet.
- Independent Claude review of NEW offline PERF/TEST found real PERF opcode
  bug:2 is LM_CFG, stock PERF is4. Confirmed kgsl_hfi.h/c; corrected encoder
  with namedconstants. Test now extracts actualstock messageIDs/typeenum and
  CREATE/CMD_MSG_HDR macros, rather than repeating the same wrongliteral.
  Revised test failed oldencoder (expected regression), then fixedencoder
  passed ASan/UBSan allcounts/seq/bounds/layout/alias andARM64compile.
  Captured cmdDB cx/mx/gfx startat0; all5capturedGPUbins endat0Hz, GMUtable
  starts0Hz then200MHz. Thus offentry contract holds fordeviceprofile; runtime
  stillmustchooseactualOPPs and verifyHFImajor<2 beforeusinglegacycodec.
  Other encoders INIT0/version1/BW3 matchpinnedIDs. Keptcount1 allowed as
  wirecodec, not claim ofusableactivepowerpolicy. Main0c6663a/publish7da90df;
  source-only push0. NO runtimepatch/CI and NOT in0145artifact.
  Addedsource-derived ACTIVE-vs-IFPC sequencingnote: A618 needsexplicitSPTPRAC
  enable afterGX/MXOOB if choosingACTIVE; futurestartupnotimplementedyet.
- Prepared0145 first APPS DDR floor handoff (no CM3 release). Decision:
  intentional replacement of UNKNOWN inherited APPS vote, possibly lower;
  not a read/raise/preserve operation. User authorized experimental tempboots.
  Claude source review agrees bounded stock-style handoff need not recover
  impossible baseline. Adopted stock-exact DDR-only first request: MC0/SH0/
  ACV addresses50000/5003c/5000c values60000fec/600006be/60000008, VCD0/1/11,
  WAIT/ENABLE7, all three needACK. Earlier5-command DDR+CNOC draft was tested
  offline but superseded BEFORE publication/CI/boot: stock only sends APPS
  DDR pcl beforeFW_START; CNOC ccl supplies HFI table. No CNOC APPS writes.
  Gate sweetgmubw=1 + existingk6a/gpuprobe/clocks/status gates, CM3reset1,
  busy/init/retention0, no TCM/SMMU test, jtag1+wfi0 and directidle_enableFALSE.
  Exact3unique cmdDB bindings/version/address/unit/width/VCD checked. Require
  all8normalTCS empty/idle before and after mask, and after successful cleanup.
  Dedicated absolute-address sender holdsrh_lock, masks onlyTCS0IRQ, syncs
  payload/wait/enable/control,100msdeadline/freshprogress, poisons on uncertain
  writes/timeouts, no retry/withdrawal thisboot. Votes held until reboot.
  Unknown inherited bandwidth may change; ACK does not prove frequency or
  GMU execution. No partition write. Actual CI/temporary boot recorded above.
  Canonical xnu/gpu/sweet_gpu_probe.c now checked exactly in CI;0134 reverse
  probe hunk superseded by0145, other hunks and all27finalsources verified.
  Final3command tests ASan/UBSan passed real/ambiguous/malformed bindings,
  all19 injected sync failures, lock/idle/geometry/busy guards, stale/allones/
  missing-issued/missing-complete timeouts, IRQ-clear and postcleanup failure,
  quarantine/no secondattempt. Payload/order/commit compared independently
  against bw-table-0142 DDR4 query. Actual XNU-header ARM64 C compiles passed
  both RPMh and probe. Full126-145/reverse/27sources/YAML fixtureaoka7pyj passed.
  Committed mainac97831 / publish1f00ab4f9ca9010d3143f5f4db6bba83cf8db3ff;
  push0/dispatch204. CI42251468013 created16:20:32UTC, completedSUCCESS. Prepared
  build-bcm-image.py sweetgmubw1+jtag1+wfi0, noSMMUinit/gmuload/snapshot.
  watch-bcm-0145-build.py waits fullCI success before selectivekernel fetch.
- During0145CI prepared offline sweet_hfi_perf.c/h/test.py: legacy43word
  PERF (16GX/4CX pairs, kHz, packedARC) and2word TEST withzero data for
  HFI_USE_REG. No runtime caller, no0146patch yet and NOT part of0145artifact.
  Exact pinned structs extracted inhosttest; ASan/UBSan allcountpairs,
  4096TESTsequences, kHz/ARC candidatepacking, bounds/unchangedoutput,
  ordering/selectorrange/overlap/zeropadding tests andARM64compile passed.
  This does not choose activeOPPs or validate actualvoltage/frequency.
- Completed0144 temporary boot from confirmed target recovery.
  CI42246627641/6b585c3 kernel downloaded6527658compressed bytes, ZIP CRC and
  SHA256ade62c9907a1b5ccd9583c5dd1f1fe908533db2b2899dd9727a785878e8490d3
  verified. Checked all four TCS begin/end/bootarg/rc markers in actual kernel.
  build-tcs-image.py imageSHA256
  21221676de9a7719534787346bf3bc4f2881836795e7e13c56274a48dcf0376a.
  fastboot Sending16880KB OKAY0.404s, BootingOKAY0.151s,total0.567s.
  No flash. CMDLINE includes sweettcssnapshot=1 with prior GMU clock/status
  flags, NO cmd-db recapture/SMMUinit/gmuload/firmware execution. Includes0143
  memory latch code but no execution caller. User subsequently confirmed iOS
  loaded and returned recovery. Capture and decoder completed; see0144 result
  above. No further0144 capture is pending.
  Do not confuse this snapshot with BCM vote readback. Test/decoder source
  follow-up published5d9f321; active artifact runtime source6b585c3.
- Prepared0144: full legacy160word HFI bandwidth encoder linked into XNU
  (no sender/caller) and opt-in sweettcssnapshot=1 before GPU probe votes.
  Inventory reuses rh_map/rh_lock; reads all8normal banks/16slots twice,
  globalIRQ/header/payload comparison,837 bounded reads. No writes/IRQ clear/
  trigger, one-shot, status stable is NOT vote readback or ownership proof.
  Existing TCS slots may be empty after votes persist inside BCM. Claude
  reviewed host-vote architecture: BCM read semantics not proven, stock is
  write-only; adopted exact-address/per-VCD completion requirements for future
  sender. Did NOT adopt suggestion to substitute maximum GPU vote for unknown
  shared baseline; snapshot alone cannot prove that preserves other consumers.
  New snapshot tests ASan/UBSan passed lock/map/geometry/unstable status,
  payload/IRQ, bounded reads/no writer and one-shot. HFI test compares against
  actual pinned hfi_bwtable_cmd, all14 captured rows,4096 sequences, bounds,
  unchanged output on error, zero unused and overlap rejection; ARM64 compile
  passed. Actual XNU-header C compiles passed probe and RPMh. Full126-144,
  all reverse checks/26source comparisons/YAML passed gpu-context-series-oiwe4z9o.
  Main dcc3608 / publish6b585c3237d683deabce207310da31085bda31df;
  CI42246627641 dispatched204, started15:49:30UTC, Build15:50:21UTC.
  Phone reconfirmed recovery via targeted adb. CI42246627641 SUCCESS:
  Build15:50:21-16:02:44UTC, mandatory patch/source/kernel verification
  success16:02:44-16:02:48; run completed16:03:12. Selective kernel fetch
  and device test completed as recorded above. Source remains6b585c3; later source-only
  5d9f321 is tests/decoder only, no changed runtime code and no second CI.
  Prepared build/build-tcs-image.py (sweettcssnapshot=1, no cmd-db recapture,
  no SMMUinit/gmuload). watch-tcs-0144-build.py waits full success then selective
  kernel fetch. Do not boot before mandatory verification passes.
  Additional host integration test passed160word message at all1024 ring
  write positions, publish/barrier/doorbell order and full-queue unchanged
  refusal. tools/gpu-tcs-info.py validated completeness/order/enable-mask
  using exact snapshot C fixture; it labels slot data as historical/pending,
  never as current votes. No runtime kernel change after CI dispatch.
  New pinned sources cached rpmh.c/qcom-rpmh-mailbox.c/rpmh.h/msm_bus_core.h/
  msm-bus-ids.h. Confirmed exact-address inflight matching, MSGID RESP_REQ
  from message-or-command complete, WAIT bits from command.complete and
  status ISSUED + conditionalCOMPLETE. Generic rpmh_read exists but does not
  document BCM response semantics. Stock dual==active vectors omit sleep/
  wake requests. Existing deep-idle assertion still needs direct SWEET path
  proof before ACTIVE-only BCM writes: generic cpu_machine_idle_init can set
  idle_enable=true; initial globalfalse alone is NOT proof. 0144 read-only
  inventory does not depend on that assertion.
  Offline extracted exact _load_gmu_rpmh_ucode with A618 predicates (mocked
  register sinks only) yields48 writes, all within captured3GMU/PDC resources,
  finalPDCenable80000001 and barrier. Trace at research/.../
  pdc-stock-a618-write-trace.json, generator build/trace-stock-pdc.py.
  This is address/order evidence only, no hardware access/ownership proof.
- 0142 fresh result: user confirmed iOS loaded and returned recovery. Pulled
  cmd-db-0142.bin/.txt: ring460944bytes/flush659, complete4216byte database,
  FNV1a53b20305, snapshot rc0. Saved verified raw/decoded/derived data under
  research/sweet-k6a-live-capture-20261027 only. Phone remains recovery.
  Generic decoder fixed to preserve valid address-zero .mol metadata,
  duplicate IDs and alias addresses; hardware consumers must still select
  unique targets. All8 selected ARC/BCM targets are unique, aux version1000.
  MX=[0,16,192,320,384], CX=[0,16,64,128,192,256,384],
  GFX=[0,16,64,128,192,256,320,384,416], padded16 entries. Offline C helpers
  verified both proposed MIN_SVS+1 start requests yield00400202/MX192;
  this does not establish actual voltage or enable firmware execution.
  BCM unit/width/VCD: MC0=1770000/16/0, SH0=2090000/32/1,
  ACV=1/0/11, SH2=2090000/8/1, SN15=530000/8/3. Regular scaler correctly
  rejects width-zero ACV; stock query needs its own ordered calculation.
  Log includes driverkitd SIG9 namespace1/code7; not investigated, not a
  clean-no-crashes claim. No acceleration/GMU execution evidence.
- Offline tools/gpu-bw-table.py reconstructs12 DDR +2 CNOC query rows from
  verified log + original FDT, preserves BCM binding order and stock BIT(i)
  wait-mask behavior. Critical finding: max_query_ab/ib are initialized once
  per node, NOT per BCM; MC0's scaled value carries into ACV. Therefore ACV
  width0 still gives60000008 on nonzero DDR rows,40000000 only at row0.
  Claude initially missed this; direct source review caught it and a second
  review agreed. Do NOT encode ACV as always-off. KBTOB=*1000ULL verified
  in pinned msm_bus_core.h; ACV7038/APPS8000 verified in msm-bus-ids.h.
  No active-only property or KGSL override: both clients are dual-context.
  Query tables are isolated ACTIVE queries; they are not live aggregated
  host votes or authorization to replace shared wake/sleep state.
  DDR order MC0/SH0/ACV; CNOC SH2/SN15 (not upstream's single SN15).
  Both wait masks1. Source-derived bin167/180MHz row4 is
  MC0=60000fec,SH0=600006be,ACV=60000008. No hardware request sent.
  Differential C harness extracts the unchanged pinned bcm_query_bus_req
  and bcm_update_acv_req into a host model: all14 captured rows and12
  average/peak boundary cases match under ASan/UBSan. Reversed BCM order,
  repeated BCM membership, same-VCD completion, saturation, overflow and
  malformed resource/vector/blacklist tests passed. Snapshot host regression
  also passed. Output bw-table-0142.json stays outside git. No new kernel
  patch/CI/boot in this milestone; full startup remains unimplemented.
  Completed main809a072, published source-only22b44d2 successfully to
  nonrootus/ios-sweet codex/gpu-k6a-macos15. No captured files published;
  user tools/mkiosroot.sh left untouched. Remaining first-start dependency:
  current bsd/dev/sweet_rpmh.c transport handles at most3 address+offset
  commands but conflict checks assume VRM16byte windows, and implements
  ACTIVE only with deep idle disabled. Do not pass BCM addresses through it
  unchanged or mistake isolated HFI rows for aggregate live host requests.
  Establish BCM ownership/inherited state and dual-context policy before
  adding a bounded request; then PDC/RSC, ARC/HFI table encoding and CM3
  release with0143 retained memory. Phone is still recovery; no user action
  is currently needed for offline implementation work.
- Corrected0141/0142 CI42222741874 SUCCESS: Build13:06:22-13:16:27UTC,
  required patch/source/kernel checks passed13:16:27-13:16:31. Selective
  download6532932 compressed bytes passed ZIP CRC and kernel SHA256:
  afe14df5daa55c366366cb962e1ddf0a07f5af21e32302ae3ab740c8bcabfdd9.
  Verified begin/end cmd-db, bootarg and rc kernel markers. Source is00c57b8;
  later offline BCM/e2f93df and0143/b5201c6 are NOT in this image. Built and BOOTED
  build/xnu-memory-probe-42222741874/shim-boot-smmu-register.img using
  build-cmd-db-image.py: sweetcmdsnapshot=1, no sweetgpusmmuinit/gmuload.
  Image SHA25668d148b616baf4700a4b061beee0f06b8ef1e40f6428d039a3cbe65f6a6b077d.
  From confirmed target recovery, fastboot Sending16880KB OKAY0.398s,
  Booting OKAY0.151s, total0.560s. No partition flash. Fresh0142 result above
  confirms iOS boot and complete snapshot. GPU firmware execution remains
  unimplemented. Next: finish verified offline BW table construction, then
  establish host BCM vote lifecycle and PDC/RSC ownership before CM3 release.
- Prepared0143 execution-memory latch (NOT in current0142 CI/image).
  New begin_execution exposes canonical HFI0x5000 bytes only after ready and
  caller-held mapping ref. Independent monotonic latch blocks retain/release;
  destroy marks pending without freeing even if refs later become zero. No
  unlatch, hardware action, or new SMMU caller. All allocations deliberately
  stay resident until reboot after any latched attempt, including aborted ones.
  No ownership/translation/power/drain proof is inferred from refs. Updated
  header lifetime contract and cached HFI base during successful construction.
  Claude completed NEW allocator-only API design review; adopted independent
  destroy guard, pre-decrement release refusal, logical-size-only exposure and
  no error path after latch. This was not a retry of prior teardown review.
  ASan/UBSan allocator suite passed original7/137/137 failures plus null/no-ref/
  deferred-destroy/repeated-latch/refusal/permanent-pin/fullHFI-range tests;
  LSan remains enabled with deliberate pin rooted globally. Actual target-header
  ARM64 compiles passed. Full126-143/24finalsources/YAML checks passed corrected
  baseline with0106, fixturegpu-context-series-vij77e6l. 0139 header reverse
  hunk superseded by0143+exact final header compare. Prepared main0077643/publishb5201c6 (source-only push), no full XNU
  CI0143 yet; composed adapter regression also passed. Full CI pending
  future batch; do not restart0142 CI just for this preparation-only API.
- Added offline BCM format/scaling helpers sweet_gmu_bcm.c/h/test.c while
  corrected CI runs: exact eight-byte little-endian aux decode, stock floor
  with positive-subunit minimum1, overflow rejection,14-bit saturating X/Y,
  valid and caller-supplied commit encoding. Unit tests cover decoded bounds,
  33widths*4port counts*1031 bandwidth cases, zero/subunit values, overflow,
  all14-bit packing boundaries and ARM64 compile. No resource selection,
  shared-client aggregation, ACV/ALC calculation or hardware caller added.
- 0142 first CI42219638542 FAILED verification after successful compile
  (Build12:42:18-12:55:17UTC). Root cause: local gpu-patch-clean-check baseline
  omitted0106 HFI startup encoder; generated0141 added duplicate functions
  rather than changing existing ones, so real build skipped0141. Verification
  caught all four unapplied HFI changes. DO NOT BOOT that artifact. Phone stays
  recovery. Fixed0141 in main8f30cc0/publish00c57b86dd5e26ebdc80d7c33c12aaeaa4f9d539;
  workflow now traces checks. Corrected CI42222741874 started13:05:54UTC and completed SUCCESS;
  selectively downloading6532932 compressed kernel bytes to D. No boot yet.
  New corrected baseline build/gpu-patch-baseline-0125-complete includes0106;
  check-context-series.py now requires reverse0106 before126..142. Full chain,
  reverse checks and24source comparisons passed gpu-context-series-hgvceioe.
  Old ecchaegt/fy55meop fixtures do NOT establish correct HFI baseline.
  Full CI logs are streamed ZIP without Range/Content-Length; gh/urllib both
  suffered truncation. Saved9306112byte partial0142-full-ci-logs.zip; first
  complete0_build.txt was extracted with local ZIP/deflate and verified against
  its data-descriptor CRC and size. Extracted verification failure in
  build/0142-ci-verify-failure.txt. Avoid re-downloading full logs unnecessarily.
  Offline ARC helper/docs published b960e3e, separate from kernel integration.
- Read-only recovery KGSL discovery during0142CI: kernel4.14.340-openela~
  positron/5a56b680 exposes /sys/class/kgsl/kgsl-3d0. gpu_model Adreno618v1,
  frequencies800/650/565/430/355/267/180MHz, num_pwrlevels7, default6.
  Saved recovery-kgsl-profile-20261106.json and606123byte recovery FDT SHA
  6378a14e6e3e18c04975c9516e5f482f763d6e3e7d062ce467d1130ef5821c02.
  GPU/GMU/SMMU resource registers unchanged; resolved supplies/bus phandles
  target the same nodes. Recovery changed bin167: removed140MHz and made
  default180MHz; its frequency list uniquely matches recovery bin167. This
  supports bin167 inference, NOT direct fuse verification. Original FDT bin167
  still includes140MHz; don't overwrite it with recovery defaults silently.
  recovery-gpu-dt-diff-20261106.json records62 raw property differences,
  mostly phandle numbers. No GPU sysfs writes or recovery state changes.
- Static captured bus graph gives unique directed paths26->770->129->512
  (SH0/MC0/ACV) and26->10071->161->10036 (SH2/SN15), no path blacklists.
  Saved gpu-bus-candidate-routes.json. Pinned msm_bus_fabric_rpmh.c defines
  BCM aux as LE32 unit, LE16 width, u8 VCD/reserved; command bits commit30,
  valid29, X[27:14],Y[13:0],14-bit saturation. Actual five resource aux values
  await0142 snapshot; no bus vote/HFI BW table implemented. Exact stock
  regulator MIN_SVS is48+1 (not16); GMU200MHz/GPU180MHz use VDD_MIN,
  with primary ARC ceiling from actual tables (captured CX/GFX ceiling64).
- While0142CI runs, added offline sweet_gmu_arc.c/h/test.c: stock HFI
  ARC packing from raw primary/MX tables and level+1 OPP. Conservative policy
  rejects missing MX ceiling instead of stock highest-MX fallback. ASan/UBSan
  exhaustive65536 requested levels, malformed tables, boundaries/output and
  ARM64 compile passed. NO hardware caller/newpatch/power vote; actual MX
  remains unknown. Fetched pinned adreno.c/gpucc-sdmmagpie.c/vdd-level header:
  mask-all then clear-all IRQ helper verified; stock coldboot explicitly requests
  DDR bandwidth before firmware. GMU200MHz maps VDD_MIN in stock GPUCC;
  do not infer an actual voltage or active GPU speed bin from this source.
- Prepared 0141/0142, main0573e31, publish ac1fdf0: HFI requested firmware
  version corrected from1.10 to exact Xiaomi A6181.8; empty polled RX rearms
  rx_req (no IRQ lost-wake claim). Bounded cmd-db snapshot shares existing RPMh
  mapping/lock, exact observed size0x1078, aligned reads/FNV/log decoder; no
  TCS request or new resource vote. Opt-in sweetcmdsnapshot=1 also requires
  sweetk6a=1 sweetgpuprobe=1. Do not repeat inactive SMMU test for this capture.
  Local HFI ASan/UBSan/ARM64 passed; snapshot ASan/UBSan1054 exact reads,
  lock/map/size/retry failures and parser checksum/bounds/missing-row tests
  passed. Full126-142 apply/reverse/24 finalsources/YAML passed fixture
  gpu-context-series-fy55meop. Actual XNU-header ARM64 C assembly passed for
  both modified rpmh/probe files. Published ac1fdf059ca8ce28c8744956fd3b3f0b7c56c8d1, CI42219638542
  started2026-11-06T12:41:47Z. Full build pending. Use build-cmd-db-image.py
  for this run: sweetcmdsnapshot=1, NO sweetgpusmmuinit or sweetgmuload.
  Device still recovery; no0142 boot yet. tools/mkiosroot.sh untouched.
- Cold-start source review: exact stock10c33d40 requires TCM_BOOT=2,
  FW_INIT=BABEFACE, HFI_USE_REG path with GX/MX votes before HFI init. Claude
  new cold-start review completed; agreed version separation/retain mappings
  after any attempted reset release. Its CB5 wording is wrong: bank0/SID5.
  Never use inactive teardown after CM3 release; firmware/BW/IRQ setup remains.
  Live DT PDC cfg0b290000/seq0b490000, GMU0506a000; derived register table at
  research/sweet-k6a-live-capture-20261027/gmu-start-resources.json.
  Recovery no debugfs/devmem, but exact cmd-db already mapped by XNU RPMh:
  0140 log pa85f20000 size1078 version1 magic0c0330db. Earlier combined log
  already has cx.lvl30000/gfx.lvl30050 tables; MX and BCM aux still missing.
  Do not invent a second raw-RAM mapper: use existing RPMh mapping as0142.
- Latest phone test 0140: user confirmed iOS loaded and recovery. Fresh log
  research/sweet-k6a-live-capture-20261027/smmu-0140.txt:223298bytes, flush9.
  New SID5/131 data/six table marker present. prepare0/install0,
  root104708000, SMR80000005, GFSR0/CB_FSR400 FORMAT2 faults0 unknown0;
  remove0 RETIRED state2 retained0, finaldone0. No NC validation failure,
  SpringBoard CRASH or panic lines matched. Phone later tempbooted0142 as above.
  This validates inactive allocation + register lifecycle, NOT translated DMA,
  firmware execution or rendering. Next work: GMU cold-start dependencies and
  HFI1.8 request / empty-RX request rearm; do not repeat0140 unchanged.
- Previous phone test 0138: user confirmed iOS loaded and recovery. Fresh log
  research/sweet-k6a-live-capture-20261027/smmu-0138.txt (382268 bytes, flush395):
  prepare=0, install=0, GFSR=0, CB_FSR=0x400 / FORMAT2 / faults0 / unknown0;
  inactive unmatched teardown remove=0, state=RETIRED(2), retained=0, done=0.
  This passes register installation/removal and releases owned memory; it does
  NOT establish translated DMA, GMU firmware execution or acceleration.
- ACTIVE 0140 supersedes 0139 before any device test. Found exact Xiaomi
  sweet_k6a-r-oss source in existing partial clone, HEAD
  10c33d40a11ecdc75cc1dadb5bd07894bab05815. Read six GPU source blobs into
  research/sweet-k6a-stock-gmu-10c33d40 with read-stock-gmu-source.py.
  Its HFI RX/TX watermarks and RX request are ONE (0125 was right), unlike
  newer Qualcomm b6410c3f. Its allocate_gmu_kmem uses 1MiB slots:
  dummy60000000, HFI60100000, dump60200000, log60300000. Cache ranges,
  sizes and privileges remain unchanged. Therefore SIX table pages, 131 data.
  Corrected in main9923369, publish978645f7ac142a34542818b164792ad1c1874ccc.
  Full CI42213964573 SUCCESS, started2026-11-06T11:56:56Z,
  completed2026-11-06T12:12:18Z. Kernel downloaded to
  build/xnu-memory-probe-42213964573 (6530054 compressed bytes), CRC/SHA
  verified, new SIX-table marker present and old five-table marker absent.
  Kernel SHA2565e956d0a4a0cbd76707562b60667690b8f810321ecb023fde9f45bcb07c73c49.
  Temporary image SHA256b0164509a81b79e6ec70c481023caa88c65f5e2ef6dcde6b083fb12720416b90.
  BOOTED0140 from confirmed target recovery: Sending16880KB OKAY0.447s,
  Booting OKAY0.152s, total0.609s. No partition flash.
  User confirmed iOS loaded and returned recovery; fresh0140 passed as above.
  Required kernel marker: "legacy GMU memory SID5, 131 data pages, 6 tables".
  Repeated sanitizer/layout/PTE/HFI/old-HFI checks passed; allocator now
  covers137 page-query/137 clean failures. Both target-header ARM64 compiles
  passed. Full126-140 series/20finalsources/YAML passed fixture
  build/gpu-context-series-ecchaegt. Phone now testing0140 as above.
  0139 CI42212859558 CANCELLED (gh TLS timeout, API cancel202 succeeded).
  NEVER boot/use its superseded profile. Claude allocator review found no
  blocker but warned exact stock ABI needed confirmation; independent Xiaomi
  source verification overrode the earlier Qualcomm profile conclusion.
- Historical prepared/published 0139 full legacy GMU memory test: main e7f5a0c,
  publish 74903fa40b109a3bd68f27b94e2ce9448b08dedf. Full CI 42212859558
  started 2026-11-06T11:47:40Z, CANCELLED/SUPERSEDED as above. Never booted.
  Superseded instructions (do not execute): selectively download kernel, verify marker
  "legacy GMU memory SID5, 131 data pages, 5 tables", build and tempboot via
  usual scripts. Phone remains recovery. Do not run firmware yet.
  0139 creates six isolated NC data regions and five cached table pages,
  privileged AP support, pinned-KGSL unused HFI words zero, and uses SID5
  for the unchanged inactive-only context lifecycle. SID4 unmatched/faulting.
  gmu_user empty-domain equivalence and firmware ABI compatibility must be
  resolved before execution. Source-derived layout does not prove actual DMA.
  New allocator passed ASan/UBSan allocation7/page136/clean136 failures,
  alias rejection/deferred lifetime/all 32-bit holes. check-gmu-layout.py
  passed PTE/table/HFI/layout suites, old HFI regression and ARM64 C compile.
  sweet_gmu_memory_test.py and sweet_gpu_smmu_probe_test.py passed using
  /mnt/d/ios-sweet/build/gmu-legacy-layout-check. check-gmu-target.py compiled
  allocator and adapter to ARM64 assembly with real target headers.
  check-context-series.py passed126-139/20finalsources/YAML at
  build/gpu-context-series-bcldu45_. These host tests are manual, not CI jobs.
  Claude separately reviewed the NEW layout and allocator (not teardown),
  found no blocking allocator issues. Independently verified A618 no ECP
  in pinned adreno-gpulist.h and captured flat firmware dword1=9, size32768,
  SHA2569ef10b2b179054fb57af25008e29feb24300c2eaaeabf907bd741786bbacbf2e.
  Adopted HFI zero-field correction; retained explicit unsupported-profile
  rejection and separate native-page allocations. Firmware's exact stock KGSL
  revision/incoming privilege and actual hardware visibility remain unverified.
- Previous phone test 0137: user confirmed iOS loaded and recovery. Fresh log
  research/sweet-k6a-live-capture-20261027/smmu-0137.txt (231899 bytes, flush32):
  prepare=0, install=0, GFSR=0, CB_FSR=0x400 / FORMAT2 / faults0 / unknown0.
  Removal FAILED: rc=-5, state=POISONED, retained=1, S2CR0 readback0x300
  after requesting TYPE=FAULT (0x20000). This is an ignored TYPE change,
  not just reserved-field readback. No panic string; SpringBoard/backboardd ran.
  Keep memory on failure. No DMA/GMU execution or GPU acceleration established.
- Source fixes 0136 and 0137 are committed locally as 461da4d and d892239.
  They distinguish FSR FORMAT from faults and validate S2CR FAULT by TYPE,
  not reserved fields. Failure retention remains. Local sanitizer models,
  ARM64 compiles and patch-series/final-source checks passed. Claude reviewed
  these two fixes; earlier runtime-adapter review was not completed.
- Published 0138 head: 777f02f26dde3f940da3e9a3b35ffbd99e78ed8b on
  nonrootus/ios-sweet, codex/gpu-k6a-macos15; local commit 23130e9.
  Full XNU CI run 42199702714 succeeded, including required checks.
  Kernel downloaded with CRC/SHA256 and new inactive-teardown marker verified.
  Kernel SHA256: 669c33807a4c9b749519683052c26cfe4282ddda46cf801e9983fe1bc24cb626.
  Temporary image: build/xnu-memory-probe-42199702714/shim-boot-smmu-register.img;
  SHA256: 64de8040be31365f1a5af7bfc9a17f22ee325250ae8d63bf84f501307044f9da.
- Phone was rebooted from recovery and temporarily booted with 0138,
  target serial <TARGET_SERIAL>: Sending 16860 KB OKAY 0.396s, Booting OKAY 0.153s.
  Phone is now back in recovery; fresh 0138 result is recorded above.
  Next: prepare full legacy GMU memory layout and distinguish kernel SID5
  from diagnostic user SID4 before any firmware execution.
  Implemented a separate inactive-only remove_unmatched API: verify sole SMR
  ownership and default unmatched-fault policy, invalidate SMR with readback,
  synchronize, disable/invalidate/clear context, then recheck before unpin.
  No retry of an existing POISONED context and no BYPASS/security calls.
  0138 passed local validation and full CI; Claude review was stopped by its
  service classifier, so no verdict is available. Device register test passed.
- Separately, 32 staged apps were promoted in an OFFLINE overlay of the original
  working mg-nowait image. Artifact: build/apps-overlay-mz0jpra4/
  apps-nowait-base-prototype.qcow2, 2,424,832 bytes. Metadata/Info.plist checks,
  HFS checks before/after and QCOW check passed. No phone deployment or
  LaunchServices registration is validated; wallpapers remain unfixed.
  Its backing file is a virtual read-only sparse view. See the tail entries
  for required scripts; do not apply an offline-base delta to mutated userdata.
- Separate 0137 SpringBoard crash: three SIG11 pc=0 failures; unslid LR
  0x194b3858c maps to CoreImage (image+0x19c58c), callers 0x1949e1884 and
  0x1949a3114 also CoreImage; 0x19ef03760 is CoreUI, 0x18db98780 libdispatch.
  Verified using ipsw dyld a2o on local 20H392 repair image mounted read-only.
  Resembles reference hakios-alioth's missing EAGL table / Bold Text crash,
  but exact function/cause remains unconfirmed. User CONFIRMED enabling Bold
  Text before those crashes. Do not copy the reference's hardcoded 20F66 address.
  Full ipsw a2s hit out-of-memory then timed out; bounded a2o succeeded.
  Both analysis scripts unmounted the local image. No UI fix deployed.
  Additional bounded local disassembly succeeded: CoreImage0x194b38588 is
  blr x8, returning to logged LR194b3858c; x8 loaded from sp+e8, x1=b71.
  Confirms null indirect call, not yet exact Objective-C method identification.
  research/.../coreimage-0137-callsite.txt; disassemble-coreimage-0137.py
  cleaned up its read-only local mount. No CRASH SpringBoard lines in0138;
  this does not prove a fix (no UI changes were made).
  inspect-coreimage-objc.py used bounded ipsw dyld macho --objc --verbose
  on ONLY CoreImage (no full symbol scan) and unmounted successfully.
  Saved coreimage-20H392-objc.txt: method
  +[CIContext internalContextWithEAGLContext:options:] has return void*,
  unslid IMP0x1949e1640 (comment preceding method declaration, line4675).
  Reference20F66 address0x1949bd640 MUST NOT be used for this build.
  This enables a future build-checked guard; no guard code/deployment yet.
  Additional LC_UUID from bounded local --loads: CoreImage20H392
  CF8D2341-91CA-31C0-9FEE-11721D31D710. Saved coreimage-20H392-loads.txt;
  inspect-coreimage-identity.py unmounted cleanly. Future guard should verify
  both image identity and method IMP before replacement, not just OS version.
- Work and artifacts stay on D. Do not clean C or touch the user's dirty
  tools/mkiosroot.sh. Local branch: codex/sweet-k6a-local. Build worktree:
  D:/ios-sweet/build/gpu-k6a-probe-worktree. Source pushes and temporary boots
  are authorized; preserve recovery/modem/persist and backups. No destructive
  userdata operation is part of this test.

## Local build setup handoff (2026-10-26)

- User wants the source, IPSW/DMGs, build cache, and rebuilt root images on D:\ so edits can be rebuilt locally without downloading the remote 12 GB image again. Workspace: `D:\ios-sweet`; source checkout: `src\ios-sweet`, branch `codex/sweet-k6a-local` tracking public `main` (commit `45263be`).
- WSL Ubuntu 24.04.5 is installed as WSL2 at `D:\ios-sweet\wsl\Ubuntu\ext4.vhdx`; the official `.wsl` archive is on D: and its SHA-256 matched the official Ubuntu list (`bb415d824822c4b878125729af451a5d18fb13d1cf5cbed9a7393ad64ac6039e`).
- Stock WSL 6.18.40.1 had HFS+ disabled. Built Microsoft kernel tag `linux-msft-wsl-6.18.40.1` with `CONFIG_HFSPLUS_FS=y`; `D:\ios-sweet\wsl\bzImage` is selected by `%USERPROFILE%\.wslconfig`. `/proc/filesystems` reports `hfsplus`; a 64 MB image on D: passed format, mount, write, unmount and fsck (`D:\ios-sweet\tools\hfsplus-smoke.sh`).
- Installed root-image tools in the D-backed Ubuntu VHDX: `hfsprogs`, `rsync`, `img2simg`, CMake/FUSE3 and compiler dependencies. Built APFS-FUSE from `sgan81/apfs-fuse`; executable is `/usr/local/bin/apfs-fuse`. Kernel and tool source/build artifacts stay inside the VHDX on D:.
- Apple 20H392 IPSW download is in progress directly to `D:\ios-sweet\inputs\ipsw\iPhone10,3,iPhone10,6_16.7.16_20H392_Restore.ipsw` (6,171,035,648 bytes; expected SHA-256 `ece1194f7e233e9109c5790a8d23a4564a10a254e15ec5b09978a343265568fb`). It is resumable; after completion extract OS/SystemOS/AppOS DMGs into `inputs\dmgs` and reuse them for every local rootfs rebuild.
- Public checkout lacks the prior local commit/patch `0082-sweet-k6a-touch.patch`; preserved settings from the prior handoff are `sweetmodel=sweet_k6a`, Goodix coordinate scale `/8`, touch rail `ldoc7`/L7C. Exact patch needs restoration from source/context. XNU workflow documented upstream uses GitHub Actions/macOS; do not claim a local full XNU build is ready.

## Agent handoff / active work (2026-10-15, latest)

### >>> UPDATE 2026-10-18 (read first, then the 10-17 handoff below) <<<

**STATE at end of 2026-10-18 (evening):**
- On the phone: userdata = **image v15** (`/run/media/dipa/android/ios-sweet-ipsw/ios16-root-20H392-v15.img/.simg`; = v14 + `/private/var/preferences/SystemConfiguration/preferences.plist` with one network service "USB Ethernet": Interface DeviceName ue0 Type Ethernet, IPv4 Manual 192.168.7.2/24 router 192.168.7.1, DNS 1.1.1.1 8.8.8.8, set "Automatic" as CurrentSet). Fallback image v14 (v12/v13 deleted).
- Kernels: **0078** = all 8 cores (`cpus=8`, cpu6/7 = A76, homogeneous SMP; mkadt now emits 8 CPU nodes; ADT `shim/out/sweet-0078hi.adt`); **0079** = display off/on via IOMFB selector 12 kern_RequestPowerChange(state) (fade over 6 vsyncs, then black; verified: power button gives "SWEET FB: display off/on"); **0080** = `SWEET NET: <proc> route add/delete/change ...` and `... add/delete address ...` trace (built, `shim/out/shim-boot-0080s.img`, NOT booted yet).
- **Internet over USB: not working yet.** Host side is ready (temporary iptables: FORWARD accept for 192.168.7.0/24 + MASQUERADE, comment "ios-sweet"; lost on host reboot). With v15 the phone sent no DNS and no outbound traffic (only mDNS/ARP) -> configd probably did not apply the service (or did, without default route/DNS). Next: boot 0080s on v15, watch `SWEET NET` lines (does configd add 192.168.7.2 / default route on ue0?). If configd ignores ue0 (not an IOKit IONetworkInterface; configd 1241.140.6 source in `research/configd-1241`, SCNetworkInterface createInterface needs IONetworkInterface -> controller (IOMACAddress, SelfNamed) -> bus), add IOKit stand-ins and/or rename the ifnet to en*.
- Live log listener (`nc -ukl 5140`) may still be running, writing `logs/live-0078s.txt`.

**LIVE LOG over USB (0077, boot 0077s): no more recovery round-trips.** Boot an image with `sweetusb=2`, run `tools/sweet-usbnet.sh logs/live-NAME.txt` on the PC: it waits for the phone's CDC-ECM interface, sets 192.168.7.1/24 (sudo) and prints/saves the kernel console the phone streams every 100 ms as UDP to 192.168.7.1:5140 (starts with the last 64 KiB). `ping 192.168.7.2` checks the link. Current image: `shim/out/shim-boot-0077s.img` (kernel 0077, ADT sweet-0069hi, cpus=6, sweetfb_noconsole=1, sweetfb_hz=30, sweetusb=2). The recovery pull (`tools/sweet-log-pull.sh`) is still the way after a panic/hang before USB comes up.

**Р В Р’В Р вЂ™Р’В Р В Р’В Р В РІР‚в„–Р В Р’В Р вЂ™Р’В Р В Р вЂ Р В РІР‚С™Р РЋРІвЂћСћР В Р’В Р вЂ™Р’В Р В Р’В Р В РІР‚в„–Р В Р’В Р В Р вЂ№Р В Р Р‹Р РЋРЎСџР В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р В РІР‚В Р В Р’В Р Р†Р вЂљРЎв„ўР В Р вЂ Р Р†Р вЂљРЎвЂєР Р†Р вЂљРІР‚СљР В Р’В Р вЂ™Р’В Р В Р’В Р Р†Р вЂљР’В Р В Р’В Р вЂ™Р’В Р В Р вЂ Р В РІР‚С™Р РЋРІвЂћСћР В Р’В Р Р†Р вЂљРІвЂћСћР В РІР‚в„ўР вЂ™Р’В° USB networking works (boot 0076s, 18:24 local): `ping 192.168.7.2` from the PC answers in ~1 ms, 0 % loss (200-packet burst, 1500-byte frames, 512/1024-byte frames).** 0075: CDC-ECM function (bulk 0x81/0x01, interrupt 0x82 NETWORK_CONNECTION; host MAC 02:00:5e:77:ee:01) + kernel ethernet ifnet `ue0` (legacy output, header strip like if_fake) with 192.168.7.2/24 set from the kernel (proto_plumb + SIOCAIFADDR on an in-kernel socket). 0076: received frames into one cluster mbuf (mbuf_allocpacket gave a first mbuf of length 0 -> panic "Failed mbuf validity check: len -14"). Host side (Linux cdc_ether, interface `enp0s20f0u3u1`): `nmcli dev set IF managed no; sudo ip addr add 192.168.7.1/24 dev IF; sudo ip link set IF up`. Boot image `shim/out/shim-boot-0076s.img` (`sweetusb=2`). iOS itself does not see ue0 yet (configd needs an IONetworkInterface in IOKit).

**USB device mode works (boot 0074s, 17:45 local): the host enumerates the phone at high speed as `1209:0001 ios-sweet "Sweet iOS (USB bring-up)"`.** 0072 read-only probe: ABL leaves the USB30_PRIM GDSC and all 7 USB clocks on, DWC3 v3.20a (GSNPSID 0x5533320a) in device mode (GCTL 0x00112000), halted (DCTL RUN_STOP 0, DSTS 0x00d3de04), event buffer still at ABL's 0xfdfc8000, QUSB2 PHY alive. 0073 (`sweetusb=2`): DCTL soft reset, own event buffer (polled, interrupt masked), ep0 DEPSTARTCFG/SETEPCONFIG/SETTRANSFRESOURCE, setup TRB, RUN_STOP; control-transfer state machine as Linux ep0.c; descriptors: vendor class, no data endpoints. It ran but no event came: **0074** forces the VBUS session in the Qualcomm wrapper (QSCRATCH 0xa6f8800: HS_PHY_CTRL |= UTMI_OTG_VBUS_VALID(20)|SW_SESSVLD_SEL(28), SS_PHY_CTRL |= LANE0_PWR_PRESENT(24), as Linux dwc3_qcom_vbus_override_enable) -> connect + enumeration. Image `shim/out/shim-boot-0074s.img`. Black Phone app: main thread waits in -[VMVoicemailManager fetchAccounts] (sync XPC; voicemail needs the modem).

**Navigation works (boot 0071s on v14, log `logs/boot-0071s.txt`):** swipe up from the bottom edge returns to the home screen; app switcher works. Two fixes: **0070** pid_hibernate (syscall 435 was nosys on the macOS config -> SIGSYS killed SpringBoard in -[SBToAppsWorkspaceTransaction _didComplete] when an app left the foreground; the only CONFIG_EMBEDDED-only entry in syscalls.master); **0071** touches starting within 48 px of an edge carry kIOHIDDigitizerEventFromEdgeTip (UIKit `_UIEventHIDTouchEdgeTypeForHIDEvent` reads the digitizer EventMask 0xb0007 bits 0x800/0x1000/0x2000/0x40000). Diagnosed, not fixed: Settings (Preferences) SIGTRAP in PodcastsUI func_1cdc47c58: force-unwrap of `URL.volumeTotalCapacity` (nil on our HFS+ root). Phone/Photos/Messages show black (MobilePhone launches, no crash) - next: stack samples via boot-arg `sweetsample=MobilePhone,MobileSlideShow,MobileSMS,SpringBoard` (image `shim/out/shim-boot-0071s.img`).

**Р В Р’В Р вЂ™Р’В Р В Р’В Р В РІР‚в„–Р В Р’В Р вЂ™Р’В Р В Р вЂ Р В РІР‚С™Р РЋРІвЂћСћР В Р’В Р вЂ™Р’В Р В Р’В Р В РІР‚в„–Р В Р’В Р В Р вЂ№Р В Р Р‹Р РЋРЎСџР В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р В РІР‚В Р В Р’В Р Р†Р вЂљРЎв„ўР В Р вЂ Р Р†Р вЂљРЎвЂєР Р†Р вЂљРІР‚СљР В Р’В Р вЂ™Р’В Р В Р’В Р Р†Р вЂљР’В Р В Р’В Р вЂ™Р’В Р В Р вЂ Р В РІР‚С™Р РЋРІвЂћСћР В Р’В Р Р†Р вЂљРІвЂћСћР В РІР‚в„ўР вЂ™Р’В°Р В Р’В Р вЂ™Р’В Р В Р’В Р В РІР‚в„–Р В Р’В Р вЂ™Р’В Р В Р вЂ Р В РІР‚С™Р РЋРІвЂћСћР В Р’В Р вЂ™Р’В Р В Р’В Р В РІР‚в„–Р В Р’В Р В Р вЂ№Р В Р Р‹Р РЋРЎСџР В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р В РІР‚В Р В Р’В Р Р†Р вЂљРЎв„ўР В Р вЂ Р Р†Р вЂљРЎвЂєР Р†Р вЂљРІР‚СљР В Р’В Р вЂ™Р’В Р В Р’В Р Р†Р вЂљР’В Р В Р’В Р вЂ™Р’В Р В Р вЂ Р В РІР‚С™Р РЋРІвЂћСћР В Р’В Р Р†Р вЂљРІвЂћСћР В РІР‚в„ўР вЂ™Р’В° MILESTONE 2026-10-18 ~15:30 local: iOS 16.7 SPRINGBOARD HOME SCREEN ON THE PHONE** (boot `shim/out/shim-boot-0069s.img` = kernel 0069 + ADT `shim/out/sweet-0069hi.adt`, image **v14**; log `logs/boot-0069s-v14-HOMESCREEN.txt`). Home screen with a few apps, Settings opens, Control Center / lock screen / notification center work, touch + buttons work, 6 A55 cores (`cpus=6`), `sweetfb_noconsole=1 sweetfb_hz=30`. Known issue: cannot leave Settings (home gesture / AssistiveTouch home do nothing) - to investigate.
What it took today (in order): 0058 HID services (Apple IOHIDFamily-1915 user client), 0059 iPhone X identity (hw.product etc.), 0060 SPMI keys + GENI touch, 0061 1125x2436 presented display, 0062 RPMh L11C touch power + IOPMPowerSource battery, 0063 GENI FIFO packing (Goodix GT9896), 0064 PRIV_WORK_INTERVAL grant (SpringBoard "Failed to create work interval"), 0065 SMP via PSCI (6 A55), 0066 crash map regions, 0067 console mute without cons_ops write, 0068 IOSurface lookup of an already-mapped surface returns base -1 (backboardd snapshot crash), 0069 UFS log flush 10 s. Image v13: CommCenter removed from launchd.plist, BKNoWatchdogs. **Image v14** = v13 + Setup skipped (`/var/mobile/Library/Preferences/com.apple.purplebuddy.plist` SetupDone/SetupFinishedAllSteps true, SetupVersion 11, daemonizeNeedsToRun false; purplebuddy.notbackedup mini-buddy flags false; managedconfiguration.notbackedup LockdownActivationIndicatesCloudConfigurationAvailable false; springboard MCForceShowCloudConfigurationUI false) + mobileactivationd data ark seeded (`/private/var/containers/Data/System/D90C94C4-F94E-4FCF-8A28-A93BE3846D8E/Library/internal/data_ark.plist`, -ActivationState Activated etc.) + MediaToolbox D22/D221/Default SubServerConfiguration StartRecorderServer=false (mediaserverd crash loop: portrait-filter prewarm called NULL GL). **Activation:** ADT /chosen certificate-production-status 0, effective-production-status-ap 0, certificate-security-mode 1, effective-security-mode-sep 1 -> mobileactivationd's native Hactivation branch (Codex `codex/activation/report.md`; alternative 4-byte daemon patch documented there). Fallback image v13; v12 deleted.

**Р В Р’В Р вЂ™Р’В Р В Р’В Р В РІР‚в„–Р В Р’В Р вЂ™Р’В Р В Р вЂ Р В РІР‚С™Р РЋРІвЂћСћР В Р’В Р вЂ™Р’В Р В Р’В Р В РІР‚в„–Р В Р’В Р В Р вЂ№Р В Р Р‹Р РЋРЎСџР В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р В РІР‚В Р В Р’В Р Р†Р вЂљРЎв„ўР В Р вЂ Р Р†Р вЂљРЎвЂєР Р†Р вЂљРІР‚СљР В Р’В Р вЂ™Р’В Р В Р’В Р Р†Р вЂљР’В Р В Р’В Р вЂ™Р’В Р В Р вЂ Р В РІР‚С™Р РЋРІвЂћСћР В Р’В Р Р†Р вЂљРІвЂћСћР В РІР‚в„ўР вЂ™Р’В° TOUCH WORKS (boot 0063u on image v13, 2026-10-18 ~13:15 local):** tapping (i) on Setup's Hello opens the device-info sheet; swipe-up is recognised (spinner, then back to Hello - under investigation). Chain: RPMh L11C vote (0062, `bsd/dev/sweet_rpmh.c`) -> GT9896 @0x5d on GENI SE7 (0063 fixed FIFO packing: register address went out byte-swapped) -> sweet_hid_touch -> SweetHIDTouch -> backboardd. Battery icon OK (0062 SweetBattery IOPMPowerSource, static 100 %). **Image v13** (= v12 + CommCenter jobs removed from launchd.plist + `BKNoWatchdogs`=true and `FBLaunchWatchdogExceptions{com.apple.purplebuddy:100}` in /var/mobile/Library/Preferences/com.apple.springboard.plist): Setup no longer killed by the scene-create watchdog (it blocked in CoreTelephony getSubscriptionInfo -> CommCenter, Codex `codex/setup/report.md`; that report also lists how to skip Setup: SetupDone/SetupFinishedAllSteps/SetupVersion=11 in com.apple.purplebuddy.plist + activation check). v9 deleted, fallback = v12. Input latency ~1 min with 1 CPU -> Codex task 11 = SMP via PSCI (`codex/smp/`).

**INPUT WORKS (boot 0060u on a freshly flashed v12, log `logs/boot-0060u.txt`):** power, volume up, volume down reach iOS (PMIC -> sweet_keys.c -> SweetHIDButtons -> backboardd). Power locks/unlocks (screen "off" shows the kernel console because the panel never really turns off). **Device identity fixed: iPhone X** (home indicator, Face-ID-style Setup). Earlier test (0059u, `sweethidtest=15` fake Home presses) advanced Setup from Hello to the language list.
- **0058** HID: `iokit/Kernel/arm/hid/`: IOHIDEventServiceUserClient + IOHIDEventServiceQueue + IOHIDEvent compiled UNCHANGED from Apple IOHIDFamily-1915.140.3 (= exact version of the iOS 16.7 IOHIDLib, clone in `research/iohid-1915`) over our minimal IOHIDEventService (SweetHID.cpp: SweetHIDButtons consumer page 0x0C power 0x30 / vol 0xE9/0xEA / menu 0x40; SweetHIDTouch digitizer collections). C hooks `sweet_hid_key(key, down)` (0 power, 1 vol+, 2 vol-, 3 home) and `sweet_hid_touch(finger, down, x, y)`. HID logs go to IOLog. Boot-arg `sweethidtest=N` = fake Home press every N s.
- **0059** identity: hw.machine/hw.model/hw.target/hw.product from the ADT (macOS-config kernel used to answer "iPad8,6"/"Redmi Note 10 Pro"). mkadt: root compatible `D22AP|iPhone10,3|xiaomi,sweet|...`, model iPhone10,3, target-type D22, `/product` copied from the real D22AP device tree (`research/ipsw-x/d22ap.adt`, extracted from the IPSW, NOT in git), `/buttons home-button-type 2`. Codex report `codex/mg/report.md`: MG ProductType = sysctl **hw.product** (unrecognized -> iPod), HWModelStr = hw.target, HomeButtonType = `/buttons/home-button-type`; disk cache `/private/var/containers/Shared/SystemGroup/systemgroup.com.apple.mobilegestaltcache/Library/Caches/com.apple.MobileGestalt.plist` (keyed by build + UUID only -> stale iPod answers survived; reflashed clean v12 to clear it).
- **0060** drivers by Codex (`codex/input/hw-report.md`): `bsd/dev/sweet_keys.c` (SPMI arbiter v5 observer reads, PON 0x810 bits KPDPWR/RESIN SID0, PM6150L GPIO2 SID4 0xc110; works), `bsd/dev/sweet_touch.c` (GENI SE7 I2C @0xa84000, starts 45 s after boot). Touch result: SE7 fw ok (proto 3) but **0x5d and 0x38 both time out -> touch IC unpowered** (L11C LDO needs an RPMh vote). Codex task 8 = RPMh client (`codex/rpmh/`), task 7 = battery (`codex/battery/`).
- **0061** (CI 39117078444): red status bar "rdar:45025538" = UIKit "No status bar visual provider for screen" (360x800 pt is no real iPhone). AppleCLCD now presents **1125x2436** (iPhone X) and shows the centered 1080x2400; touch mapped the same; ADT canvas 1125x2436. `sweetfb_native=1` reverts.
- Images: `shim/out/shim-boot-0060b.img` (0060 + /buttons ADT `sweet-0060hi.adt`). Next: 0061 image with ADT from current mkadt.

### >>> HANDOFF 2026-10-17 late (read this first) <<<

**STATE: iOS 16.7 Setup.app "Hello" screen is ON THE PHONE** (boot `shim/out/shim-boot-0057u.img` on image v12). Photo `/run/media/dipa/android/ios-sweet-work/MILESTONE-setup-hello-2026-10-17.jpg`. SpringBoard + backboardd + Setup run; nothing crashes in the GUI path. Remaining crash/relaunch loops: installcoordinationd (should be fixed by 0057, unverified), mediaserverd (VirtualAudio removed in v12, unverified), mobileactivationd (~100/boot, not analysed), bluetoothd + fairplayd.H2 relaunch constantly (no hardware).

**What is on the phone now:** userdata = image **v12** (`/run/media/dipa/android/ios-sweet-ipsw/ios16-root-20H392-v12.img` + `.simg` + `.sha256`; v9 kept as fallback, v8/v10/v11 deleted or superseded). Kernel **0057** (`xnu/out-0057`, CI `39067532732`). ADT **`shim/out/sweet-0057hi.adt`** (QEMU twin `research/q0057-hi.adt`). Boot image **`shim/out/shim-boot-0057u.img`**. Boot args: `debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam -noprogress rd=ufsroot0 unentitled_ios_sim_launch=1 ignition_level=1 wdt_test=no_user_checkin ufsrw=1 rootrw=1 launchd_unsecure_cache=1 wdt=-1`.

**Build a phone image** (kernel K, ADT A): `python3 tools/mkpayload.py $K $A shim/out/payload-X.bin --cmdline "$B" && (cd shim && ./build.sh ../shim/out/payload-X.bin && cp out/shim-boot.img out/shim-boot-X.img)` then check `python3 tools/unpack_bootv2.py shim/out/shim-boot-X.img shim/out/check-X && cmp shim/out/check-X/ramdisk shim/out/payload-X.bin`. QEMU smoke test: `python3 tools/mkpayload.py $K research/q0057-hi.adt $S/csq/payloadX.bin --ramdisk $S/csq/root-fork.img --cmdline "debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam -noprogress rd=md0"` + `PATH=~/swift/usr/bin:$PATH python3 tools/qemu-sweet.py ... --secs 40 --kernel $K --fail-on-panic` (S = scratchpad; root-fork.img lives in the session scratchpad csq/ dir and may be gone in a new session).

**Kernel workflow:** edit `research/bt28/xnu/...` (keep the pre-edit copy in `research/preNNNN/`), syntax check `python3 tools/xnu-cc.py research/run28.log research/bt28 <file>`, make `xnu/patches/NNNN-*.patch` with `diff -u pre bt28 | sed` path rewrite, add new/changed files to `research/check-patch-order.py` list, run it (must say applied + MATCH), commit + push -> GitHub Actions `xnu` builds (~8 min) -> `gh run download <id> -R dipa-studio/ios-sweet -n xnu-kernel -D xnu/out-NNNN`. **Repo is PUBLIC since 2026-10-17** (private macOS runner minutes ran out: "recent account payments have failed"); public = free runners. Commit trailer: only `Co-Authored-By: dipa-studio <183933817+dipa-studio@users.noreply.github.com>`.

**Phone workflow (user does buttons, Claude runs commands):**
- Boot test kernel: phone in fastboot -> `fastboot boot shim/out/shim-boot-X.img`. NEVER `fastboot getvar`.
- **Read logs WITHOUT filming:** after a test the user holds Power+VolDown -> fastboot -> `fastboot boot recovery/recovery.img` (OrangeFox, temp) -> wait for `adb shell true` -> `tools/sweet-log-pull.sh /run/media/dipa/android/ios-sweet-work/logs/<name>.txt` (reads the 4 MiB console ring the kernel keeps in the last 1025 blocks of userdata; patch 0047). Then `adb reboot bootloader` brings the phone back to fastboot without the user.
- **Flash a root image:** `fastboot flash -S 512M userdata <img>.simg` (7 min, 25 chunks). After a big flash the Xiaomi ABL fastboot hangs: next `fastboot boot` stalls at "Sending" -> the USER must re-enter fastboot by hand (Power+VolDown). Do not retry commands against the hung ABL. A flash right after `adb reboot bootloader` once failed on chunk 1 (USB protocol error): just retry. User must NOT unplug during flash (once interrupted at 25/25 -> reflash).
- **Edit the phone root without reflashing (same-length only):** find the file's raw offset in the local image (it is one extent; search the image for its first 4 KiB), compare with `adb exec-out dd if=/dev/block/sda34 ...`, then `adb push` changed 4 KiB blocks and `dd of=/dev/block/sda34 seek=... conv=notrunc,fsync`, read back. Recovery kernel has no hfsplus.
- **Pull the whole phone root** (12 min): `adb exec-out "dd if=/dev/block/sda34 bs=1048576 count=16384" > img`; mount ro with udisksctl or `sudo mount -t hfsplus -o loop,ro`. To write into a pulled image: `sudo fsck.hfsplus -fy` first (volume is never cleanly unmounted -> Linux mounts ro even with -o force), then `sudo mount -t hfsplus -o loop,force`.
- Making images: copy latest img with `cp --sparse=always`, mount rw with force, change, `sync; umount`, `sha256sum`, `img2simg`. Keep only the latest image + one fallback on the SSD (/home is ~98% full; big work files live in `/run/media/dipa/android/ios-sweet-work/`, old kernels/images archived in `.../ios-sweet-work/archive/`).

**Diagnostics built into the kernel (all SWEET-only):** persistent console log (0047, boot-arg sweetlog=0 off; flush every ~1 s); `|name| text` copies of /dev/null writes for processes in `sweetnull` (default backboardd,SpringBoard; 0048); `IOK name:` IOKit lookup/open trace for `sweetiolog` (default backboardd,SpringBoard; 0049/0054, 400 lines max); `SWEET Sandbox: proc op N` (0050); `STR ...` heap text dump on SIGABRT/SIGTRAP for `sweetscan` (default backboardd,SpringBoard; 0051/0053) - this is how NSException/BSAssert reasons were found; `SMP name tN pc .. bt ..` user stack sampler for `sweetsample` (default SpringBoard,backboardd; first at 90 s then every 120 s, 40 samples, 16 frames; 0054/0055); `SWEET FB: N swaps` every 1000 swaps; `CRASH name ...` crash reports (0043/0044). Symbolicate cache addresses with `ipsw dyld a2s research/dsc/dyld_shared_cache_arm64 <addr - slide>`; main-binary addresses: addr - mh + 0x100000000.

**Patches added today (0046-0057, all CI-built):** 0046 IOSurface (IOCoreSurfaceRoot) + IOMobileFramebuffer (AppleCLCD on /arm-io/disp0) + arm-io nubs; 0047 persistent log; 0048 /dev/null tee; 0049 IOKit trace; 0050 permissive "Sandbox" MAC policy; 0051/0053 heap text on crash; 0052 RENAME_SWAP via exchangedata on HFS; 0054/0055 sampler, swap counter, AKS selectors 35 (extended device state = 17) and 101; 0056 panel copy from the vsync timer at 10 Hz (sweetfb_hz) instead of every swap; 0057 no config_ext_resolver (ACL group entries resolve without memberd). ADT (tools/mkadt.py): /arm-io/disp0, /chosen/display-scale 3, /chosen/unique-chip-id (synthetic 0x5357454554000001) + chip-id 0x8015 -> IOPlatformUUID A9683613-3704-53F2-95D0-98A8FB574E78. Image v9-v12: /private/var/containers/{Bundle,Data/System,Shared/SystemGroup,Temp}; launchd.plist StandardOut/ErrorPath renamed to ...PatX (pointing jobs at /dev/console stops them launching: EACCES); v12: LastSystemVersion=20H392 in plain /var/mobile/Library/Preferences/com.apple.migration.plist (stops the 1-hour data migration that ran every boot), VirtualAudio.plugin moved to /Library/Audio/Plug-Ins/HAL.disabled/.

**Codex helper** (`codex exec --skip-git-repo-check -m gpt-6.1-sol -c model_reasoning_effort=high -s workspace-write -C /run/media/dipa/android/ios-sweet-work/codex -o OUT "$(cat task.md)" < /dev/null`, run detached with setsid nohup; config already defaults to gpt-6.1-sol high). Reports in `/run/media/dipa/android/ios-sweet-work/codex/`: mediaserverd-report.md, installcoordinationd-report.md (-> 0057), ufs-performance.md (ranked UFS speed plan), **ufs/0058-sweet-ufs-faster.patch** (READY, not yet applied: ufslogsecs default 10 s log flush batching, optional ufscache=1 directional cache ops, optional ufswait=1 spin-then-sleep; syntax-checked, host-stub verified; see ufs/README.md). Apply it as patch 0058 after review.

**Claude safety-classifier note:** several messages about QuartzCore renderer selection / writing an HFS reader tool were cut off by an automatic classifier (false positives, user agrees). Keep those topics short or let them be; they are not blockers now (rendering already works).

**NEXT STEPS (in order):**
1. **Input** (Setup stuck on Hello): touch + power + volume as IOHIDEventService/IOHIDDevice services backboardd matches (log shows backboardd matching IOHIDDevice with DeviceUsagePairs and IOService with HIDServiceSupport=true). Phone hardware: Goodix/Focaltech touch over I2C/SPI (check live DT `dtb/`), buttons via PMIC (pon) and GPIO keys. Start with a fake HID service (e.g. power button via a timer or boot-arg) to learn the ABI, then real drivers.
2. **Device identity**: MobileGestalt reports iPod + Home button. Add /product node / product-type (iPhone10,3, D22AP), device class iPhone, home-button-less (Face ID) properties in mkadt; find exact MG keys (MGIOMFBSupport.c, `IODeviceTree:/product` lookups seen in backboardd trace).
3. **Battery**: AppleSmartBattery/IOPMPowerSource style service (status bar shows empty red battery).
4. Apply Codex 0058 (UFS speed), consider cpus>1, check whether installcoordinationd/mediaserverd loops are gone, analyse mobileactivationd.
5. Hide kernel console over the GUI when not debugging: boot-arg sweetfb_noconsole=1 (but then panics are not on screen).

- **Р В Р’В Р вЂ™Р’В Р В Р’В Р В РІР‚в„–Р В Р’В Р вЂ™Р’В Р В Р вЂ Р В РІР‚С™Р РЋРІвЂћСћР В Р’В Р вЂ™Р’В Р В Р’В Р В РІР‚в„–Р В Р’В Р В Р вЂ№Р В Р Р‹Р РЋРЎСџР В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р В РІР‚В Р В Р’В Р Р†Р вЂљРЎв„ўР В Р вЂ Р Р†Р вЂљРЎвЂєР Р†Р вЂљРІР‚СљР В Р’В Р вЂ™Р’В Р В Р’В Р Р†Р вЂљР’В Р В Р’В Р вЂ™Р’В Р В Р вЂ Р В РІР‚С™Р РЋРІвЂћСћР В Р’В Р Р†Р вЂљРІвЂћСћР В РІР‚в„ўР вЂ™Р’В° MILESTONE: iOS GUI ON THE PHONE - Setup.app "Hello" screen (2026-10-17 ~21:30 UTC, boot 0057u on image v12).** Photo: `/run/media/dipa/android/ios-sweet-work/MILESTONE-setup-hello-2026-10-17.jpg` (animated "dobar d(an)" hello lettering, status bar "iPod" + battery icon, bottom "Pritisnite Home za otvaranje" = "Press Home to open" (locale hr), (i) button). Rendered by iOS 16.7 SpringBoard/Setup through CoreAnimation -> backboardd -> kernel IOSurface (IOCoreSurfaceRoot) -> kernel AppleCLCD swaps -> ABL panel memory. What made it: data migration finally skipped (v12: `LastSystemVersion` 20H392 in the plain `/var/mobile/Library/Preferences/com.apple.migration.plist`; ADT `/chosen/unique-chip-id` + `chip-id` for IOPlatformUUID), 0057 (no ext resolver -> ACL containers work), plus everything before (0046 display/IOSurface, 0050 Sandbox policy, display-scale 3, containers dirs, RENAME_SWAP, AKS 35/101, 10 Hz present).
  **Missing (next work, in rough order):**
  - **Input: no touch, no power button, no volume buttons** (no HID drivers; backboardd looks for IOHIDDevice / HIDServiceSupport services). Setup is stuck on "Hello".
  - **Device identity: it thinks it is an iPod with a Home button** (status bar "iPod", "Press Home to open"): MobileGestalt has no product/model identity (no /product node, product-type, etc.) - give it iPhone10,3 / home-button-less (Face ID class) identity.
  - **No battery detection** (no battery/charger/PMIC service; status bar battery shows empty/red).
  - Locale came up Croatian (hr) - harmless.
  - Performance: cpus=1, polled UFS (Codex UFS patch in progress: `codex/ufs/`), backboardd presents at 60 Hz.
- **README refreshed (2026-10-17):** read the full notes and updated the public overview through patch 0045, v7 hardware observations and prepared v8 diagnostics. Documents real Apple userspace, the missing display/IOSurface GUI work, limited security services, highmem, persistent userdata root, current tooling and build examples. Documentation only; no kernel build, tests, flashing or phone boot performed.

- **v11 still migrated (boot 0056u, 20:32 UTC, `logs/boot-0056u-v11.txt`).** On iOS kCFPreferencesCurrentHost lands in the plain plist: all DMEnvironment setters (setLastBuildVersionPref, setUserDataDispositionPref, ...) use CurrentHost and the phone's `/var/mobile/Library/Preferences/com.apple.migration.plist` holds DMUserDataDisposition; datamigrator's XPC service runs with `_RoleAccount: mobile`. **Image v12** = v11 + `LastSystemVersion` = 20H392 added to that plain `com.apple.migration.plist` (keeps DMUserDataDisposition, 501:501 0600) + `/Library/Audio/Plug-Ins/HAL/VirtualAudio.plugin` moved to `/Library/Audio/Plug-Ins/HAL.disabled/` (Codex: stops the mediaserverd SIGSEGV loop; untested). **installcoordinationd loop explained (Codex `codex/installcoordinationd-report.md`):** os_crash "Failed to create data directory" EACCES for `/private/var/containers/Shared/SystemGroup/systemgroup.com.apple.installcoordinationd/Library/InstallCoordination`: `Library`/`Library/Caches` in the container are ACL-only (uid/gid 0xfffffffe, mode 0000, ACE for group GUID ...012B = gid 299 systemusers); with `config_ext_resolver` the kernel asks an identity resolver (memberd/opendirectoryd) that iOS does not run -> EWOULDBLOCK -> ACE skipped -> EACCES. **Patch 0057**: drop config_ext_resolver from FILESYS_BASE (compatibility UID/GID<->GUID mapping is used instead), likely fixes other ACL-protected containers too. Codex task 3: UFS driver performance design (`codex/ufs-performance.md`).
- **mediaserverd SIGSEGV loop explained (Codex report `/run/media/dipa/android/ios-sweet-work/codex/mediaserverd-report.md`):** the fault (FAR 0x390) is in the HAL plug-in `/Library/Audio/Plug-Ins/HAL/VirtualAudio.plugin/VirtualAudio` (ApplyBeamFormerPreference <- VirtualAudio_PlugIn::SetPropertyData <- HALS_AHPPlugIn::ObjectSetPropertyData <- AudioObjectSetPropertyData <- MediaExperience vaemVADSerializationListener): the default virtual audio device ('vdef', VirtualAudioDevice_Default) does not exist (no audio hardware/driver, no /product/audio). Proposed workaround for GUI bring-up: move VirtualAudio.plugin out of /Library/Audio/Plug-Ins/HAL/ in the next root image (untested). v11 reflashed OK after an interrupted flash (USB unplugged at chunk 25/25). Codex task 2: installcoordinationd crash loop.
- **ROOT CAUSE of the endless migration: no IOPlatformUUID (2026-10-17).** datamigrator's `-[DMMigrator isMigrationNeededWithBuildVersion:lastBuildVersion:clientPID:]` gets lastBuildVersion from `-[DMEnvironment lastBuildVersionPref]` = `CFPreferencesCopyValue("LastSystemVersion", "com.apple.migration", kCFPreferencesCurrentUser, kCFPreferencesCurrentHost)` -> a ByHost file. The phone had `/var/mobile/Library/Preferences/com.apple.migration.plist` (only DMUserDataDisposition) and NO `Preferences/ByHost` directory at all. On arm XNU publishes IOPlatformUUID (gethostuuid) only from `/chosen/unique-chip-id` (8 bytes) + `/chosen/chip-id` (4 bytes) (IOPlatformExpertDevice::generatePlatformUUID, called from IOPlatformExpert::start); the SWEET ADT had neither, so every CurrentHost preference write failed. Fix: mkadt adds `unique-chip-id` = 0x5357454554000001 (synthetic) and `chip-id` = 0x8015 -> UUID `A9683613-3704-53F2-95D0-98A8FB574E78` (same SHA1 namespace computation as the kernel). ADT `shim/out/sweet-0057hi.adt`, boot image `shim/out/shim-boot-0056u.img` (0056 kernel + 0057hi ADT, QEMU OK). **Image v11** = v10 + `Preferences/ByHost/com.apple.migration.<UUID upper and lower>.plist` {LastSystemVersion: 20H392} (501:501, dir 0755 files 0600). Flashing v11 2026-10-17 ~20:10 UTC. Codex (gpt-6.1-sol high) analysing the mediaserverd SIGSEGV loop in `/run/media/dipa/android/ios-sweet-work/codex/` (report `mediaserverd-report.md`).
- **v10 did NOT stop the migration (boot 0056n on v10, 19:18 UTC, `logs/boot-0056n-v10.txt`):** datamigrator + migrationpluginwrapper ran again, backboardd drew the progress UI (13000+ swaps in ~5 min). So `com.apple.DataMigration.plist`/LastSystemVersion is not the deciding input. What is known about the decision (datamigrator XPC service `DataMigration.framework/XPCServices/com.apple.datamigrator.xpc/com.apple.datamigrator`, strings): `Migration sentinel present. Migration necessary.` (sentinel `/private/var/datamigrator/migrate`, created and removed by datamigrator itself; absent in v10), `System build version changed from %@ to %@. Migration necessary.` / `...unchanged... not necessary`, `Disposition dictionary with build version %@ is out of date relative to current build version %@`, `SyntheticDidUpgrade`, DMUserDataDispositionManager; previous build source not found yet (not in the binary's plain strings; likely in DataMigration.framework's DMUserDataDispositionManager / preferences domain `com.apple.migration`). backboardd calls `DMPerformMigrationIfNeeded` and holds SpringBoard in `checkInAndWaitForDataMigration` until it returns. NEXT: find where the previous build version / disposition dictionary is stored (disassemble DataMigration.framework DMUserDataDispositionManager + datamigrator's isMigrationNeeded path), write it into the image; or get datamigrator's os_log out (OS_ACTIVITY_DT_MODE needs a launchd env change).
- **Data migration never records completion -> skip it (image v10, 2026-10-17).** Boot 0056n (18:16 UTC, `logs/boot-0056n.txt`, 30 min): 10 Hz panel copies, backboardd still presents at ~60 Hz (107k swaps), SpringBoard still in `BKSSystemShellService _checkIn` at sample 14. Every migration run takes 1+ hour on cpus=1 and repeats each boot. DataMigration decides from `/var/mobile/Library/Preferences/com.apple.DataMigration.plist` key `LastSystemVersion` (vs ProductBuildVersion 20H392); the pulled phone root (21:01 local) had NO such file. **v10** = that pulled phone state + fsck.hfsplus -fy (volume was marked not cleanly unmounted -> Linux mounts it read-only even with -o force; fsck found only hard-link counts + minor volume header, repaired) + `com.apple.DataMigration.plist` {LastSystemVersion: 20H392} (501:501 0600). `/run/media/dipa/android/ios-sweet-ipsw/ios16-root-20H392-v10.img` (+ .sha256, .simg); v8 files deleted, v9 kept as fallback.
- **Repo made PUBLIC (2026-10-17, user request) so GitHub-hosted macOS runners are free:** the 0056 CI run was refused ("recent account payments have failed or your spending limit needs to be increased"). Checked before: no device dumps, serials, IMEI or Apple binaries in the history (.gitignore keeps backup/, dtb/, recovery/, research/ out); commit author emails are public now. 0056 rerun `39056660104` passed -> `xnu/out-0056`, QEMU OK, image `shim/out/shim-boot-0056n.img` booted 18:16 UTC.
- **Boot 0055n (17:16 UTC, ~65 min, `logs/boot-0055n.txt`): migration bar reached 99% in ~30 min (was ~60), then crawled.** Root cause of the slowness: backboardd presents the progress UI at ~58 Hz (**167,000 swaps in ~48 min**) and AppleCLCD copied the full 10 MB frame into the panel on every swap -> ~600 MB/s memcpy on the single CPU (cpus=1), starving everything (polled UFS I/O too). Sampler (16 frames): **SpringBoard waits in `-[BKSSystemShellService _checkIn]`** (synchronous BSXPC call to backboardd, from FBSystemShellInitialize <- SBSystemAppMain) - backboardd holds the system shell check-in until the data migration ends, so the migration is the gate to SpringBoard UI. **Patch 0056**: swap only records the latest swap record; the vsync timer copies it to the panel every 60/sweetfb_hz ticks (default 10 Hz); `SWEET FB: N swaps` every 1000.
- **Boot 0054n (16:53 UTC, ~12 min, `logs/boot-0054n.txt`, patch 0054 sampler):** the data migration runs AGAIN on every boot (it completed once in the 0053s run) - completion is not being recorded. backboardd keeps swapping the progress UI (3700+ swaps in ~10 min, `SWEET FB: N swaps`). Sample during migration: SpringBoard main thread blocked in a synchronous XPC call (`mach_msg2_trap <- dispatch_mach_send_and_wait_for_reply <- xpc_connection_send_message_with_reply_sync <- -[BSXPCServiceConnectionMessage _sendSynchronously:] <- BSXPCServiceConnectionProxy ...`). Unsupported AKS selectors seen: 101 `aks_assert_consume`, 93 `aks_get_internal_info`, 34 `_aks_stash_load` (datamigrator), **35 `aks_get_extended_device_state`** (SpringBoard, chronod, remindd, searchd, symptomsd...). **Patch 0055**: AKS 35 answered like 17 (same DER device state), 101 succeeds; sampler backtraces 16 frames, 40 samples (~80 min).
- **MILESTONE: FIRST iOS PIXELS ON THE PANEL (boot 0053s long run, 15:33 UTC, ~60 min; photos IMG_20261017_183029/183222/183419; log `/run/media/dipa/android/ios-sweet-work/logs/boot-0053s-long.txt`, 407 KB, 1428 flushes).** The iOS data-migration boot screen (Apple logo + progress bar) was shown and the bar advanced to full in ~60 minutes. It is drawn by **backboardd through our kernel display path**: `SWEET SURF: backboardd create id 2/3 1080x2400 fmt 0x42475241 (BGRA) bpe 4 bpr 4352 size 10452992 keys 11`, IOSurface sels 9, 27, 5, 34 and traps 2/3 (lock/unlock), IOMFB SwapBegin (4) / SwapEnd (5, 1132-byte struct) / GetLayerDefaultSurface (3) / 68 / 55, then `SWEET FB: swap N layer 0 surface 2|3 1080x2400 ... a 0,0 1080x2400 b 0,0 1080x2400` alternating (double buffering; only the first 16 swaps are logged). Triggered by `com.apple.datamigrator` (AKS sels 101/93/34 return unsupported) and `com.apple.migrationpluginwrapper`. Probably ProgressUI-style CoreGraphics drawing into IOSurfaces (no GPU used). After the migration: SpringBoard and backboardd stay up (exec once each, no crash), nothing new drawn; crash loops only for mediaserverd, installcoordinationd, mobileactivationd (~108 each in the hour); bluetoothd and fairplayd.H2 relaunch constantly (no hardware). Kernel console text overlays the image (sweetfb_noconsole=1 would hide it).
- **MILESTONE: SpringBoard and backboardd both stay up (boot 0053s on v9, 15:29 UTC, `logs/boot-0053s.txt`).** With /chosen/display-scale = 3: `exec SpringBoard` once, `exec backboardd` once, no CRASH for either; MobileGestaltHelper reads IOMFB size/dot pitch; backboardd opens AppleCLCD (sels 57,15,22,29,33,79,74 as before). No IOSurface creates and no swaps: backboardd keeps polling `IOProviderClass IOAcceleratorES` (-> 0 found) and AGXAccelerator/IOAcceleratorESLegacy - no GPU, so no CoreAnimation renderer yet. Log goes quiet after ~47 s (only 47 flushes): the system idles. NEXT WALL: CoreAnimation rendering without a GPU (CPU path) so the window server produces frames.
- **SpringBoard's invalid mode = scale 0 (boot 0053n, 15:19 UTC, `logs/boot-0053n.txt`, heap scan):** `FBSDisplayMode cannot be configured as requested : <FBSDisplayMode: ...; infxinf@0x (1080x2400/0) 60Hz sRGB SDR>` - pixel size and 60 Hz are fine, scale is 0. libMobileGestalt (MGIOMFBSupport.c, sub_19c560a54) reads `display-scale` (u32, default 0) and `display-rotation` from **IODeviceTree:/chosen**, pixel size via IOMobileFramebufferGetDisplaySize (MobileGestaltHelper sel 8/28 in the log). mkadt now adds `/chosen/display-scale` = 3 (1080x2400 @3x = 360x800 pt). ADT `shim/out/sweet-0054hi.adt` (QEMU `research/q0054-hi.adt`), image `shim/out/shim-boot-0053s.img` = 0053 kernel + 0054hi ADT. Possible catch: MobileGestalt may have cached scale 0 in `/private/var/containers/Shared/SystemGroup/systemgroup.com.apple.mobilegestaltcache/...`.
- **MILESTONE: backboardd survives and opens the display (boot 0052n on v9, 15:07 UTC, `logs/boot-0052n.txt`).** No `CRASH backboardd`. It walks `IODeviceTree:/arm-io` children, matches IOMobileFramebuffer, `open AppleCLCD type 0 -> 0x0`, calls IOMFB selectors 57, 15, 22, 29, 33, 79 (GetBlock, out 1580/40), 74 (SupportedFrameInfo), 12, 6, 27, 17, 84, 50; opens IOCoreSurfaceRoot (sel 13); looks for AGXAccelerator / IOAcceleratorES / IOAcceleratorESLegacy (none, repeatedly), `IODeviceTree:/product` (none, repeatedly), `/buttons`, aop-smart-cover, IOPMrootDomain. No swaps yet. **SpringBoard now gets past display discovery** and dies (sig 5) in `-[FBSDisplayMode _initWithWidth:height:preferredScale:scaleOverride:refreshRate:gamut:hdr:rotation:virtual:validityCheck:]+580` <- `_initWithCADisplayMode:scale:rotation:` <- `FBSDisplayConfiguration _initWithImmutableDisplay:` <- `FBSDisplaySource initWithDisplay:` <- `FBSDisplayMonitor` (slide 0x14504000): "FBSDisplayMode cannot be configured as requested". Checks: width/height >= 2, preferredScale > 0, scaleOverride >= 0, refreshRate non-zero, valid gamut/HDR/rotation. Suspects: refresh rate 0 (IOMFB timing blocks answered with zeros) and/or scale 0 (MobileGestalt main-screen-scale; no /product node in the ADT). **Patch 0053**: heap text scan also on SIGTRAP and for SpringBoard (default sweetscan list backboardd,SpringBoard) to read the exact mode description.
- **Image v9 (2026-10-17) = v8 + `/private/var/containers/{Bundle,Data/System,Shared/SystemGroup,Temp}` (root:wheel 0755; on iOS these live on the data volume, absent from the rootfs) + launchd.plist with StandardOutPath/StandardErrorPath renamed to ...PatX (the in-place phone fix; daemons' stdout reaches the log via the 0048 /dev/null tee).** `/run/media/dipa/android/ios-sweet-ipsw/ios16-root-20H392-v9.img` SHA256 aa9f9139...6e67, `.simg` 12,145,303,864 bytes; written through `sudo mount -t hfsplus -o loop,force`. **Patch 0052** (`xnu/patches/0052-sweet-hfs-rename-swap.patch`, CI `39042761826` -> `xnu/out-0052`, QEMU OK, image `shim/out/shim-boot-0052n.img`): vn_rename falls back to VNOP_EXCHANGE when VNOP_RENAMEX(RENAME_SWAP) returns ENOTSUP for two regular files on one volume (HFS exchange swaps data and cnode descriptors = swap semantics). Flashing v9 started 2026-10-17 ~15:00 UTC.
- **backboardd EXCEPTION FOUND (boot 0051n, 14:41 UTC, `logs/boot-0051n.txt`, patch 0051 heap scan):** `*** Terminating app due to uncaught exception 'NSInvalidArgumentException', reason: '*** -[NSURL initFileURLWithPath:]: nil string parameter'`. First-throw stack (slide 0x337f0000): `+[NSURL fileURLWithPath:]` <- `-[BSSystemContainerForCurrentProcessPathProvider libraryPath]` <- `cachesPath` <- backboardd main+0x1d858 (StartWindowServer, shader cache path). BaseBoard: libraryPath = `BSSystemSharedResourcesDirectoryForIdentifier` = `BSSystemSharedDirectoryForIdentifier(id)` + "/Library"; that calls `container_system_path_for_identifier` (libsystem_containermanager -> `_container_legacy_lookup` -> containermanagerd XPC), which returned NULL (BaseBoard logs "Error getting shared system container ..."). With 0050 the sandbox denials are gone. containermanagerd.log.0 in the pulled (pre-0050) image: "Did not receive any persona attributes", "Expected to find at least one persona", notify_register_dispatch failed 9; `/private/var/containers` does NOT exist in the root image (on iOS it lives on the data volume). usermanagerd does create kernel personas 99/199/1000, but fails to save `/private/var/keybags/usersession.kb` and `persona.kb`: "Failed to atomically swap writing file: Operation not supported (45)" (HFS has no RENAME_SWAP). NEXT: create `/private/var/containers` (and check what containermanagerd needs for system group containers), fix or emulate RENAME_SWAP on HFS, then re-check backboardd.
- **Disk housekeeping (2026-10-17):** /home was at 4 GiB free. Moved (not deleted) `xnu/out-0010..0044` and old `shim/out/*.img`/`payload-*.bin` (everything before 0046) to `/run/media/dipa/android/ios-sweet-work/archive/{xnu,shim-out}` (6.3 GiB); /home now 8.7 GiB free. Large work files (phone-root.img 16 GiB, logs, tracev3 dumps) live in `/run/media/dipa/android/ios-sweet-work/`. **Patch 0051** (`xnu/patches/0051-sweet-crash-heap-strings.patch`, CI `39041440935`): on SIGABRT of a process in boot-arg `sweetscan` (default backboardd) the crash log prints heap text runs as `STR ...` (to find the NSException reason). Boot 0051n 14:41 UTC.
- **Boot 0049n (14:11 UTC, `logs/boot-0049n.txt`, patch 0049 trace): backboardd's IOKit lookups before it dies** (each run): `IODeviceTree:/arm-io/pearl-sep` -> none, matching ApplePearlSEPDriver -> none, `IOService:/IOResources/AppleKeyStore` open OK, matching IOHIDDevice (DeviceUsagePairs) / `HIDServiceSupport` notifications, `usb-drd,t8027` notification; **never any IOMobileFramebuffer / display lookup** - the exception happens before display detection. launchd (tracev3) shows backboardd's mach lookups denied with `error = 159: Sandbox restriction`: com.apple.mobilegestalt.xpc, com.apple.iohideventsystem, com.apple.system.notification_center, com.apple.logd, containermanagerd, ACCHWComponentAuthService, oscard. libsystem_sandbox uses `__mac_syscall("Sandbox", op, arg)` (ops: 1 init, 2 check, 3 note, 4 container path, 5/6/7/8 extensions, 0x15 check_bulk, ...); with no policy named "Sandbox" every call gets ENOPOLICY. **Patch 0050** (`xnu/patches/0050-sweet-sandbox-policy.patch`): built-in permissive MAC policy "Sandbox" in sweet_amfi.c (mpo_policy_syscall returns 0, container/extension ops ENOENT; logs first use of each op as `SWEET Sandbox: proc op N`).
- **Phone root pulled (16 GiB, 12 min, `adb exec-out dd if=/dev/block/sda34`) to `/run/media/dipa/android/ios-sweet-work/phone-root.img` (loop-mounted ro at /run/media/dipa/iOSRoot).** No .ips crash reports. logd tracev3 (Persist, LZ4 `bv41` blocks, decompressed strings in `ios-sweet-work/tracev3/all.txt`): /private/var/db/uuidtext is EMPTY so only launchd's own messages are readable. Findings: v8 launch failure = `Service could not initialize: posix_spawn(/usr/libexec/backboardd), error 0xd - Permission denied` (xpcproxy exit 78) - /dev/console not openable for the mobile user; backboardd[98] spawned `com.apple.MTLCompilerService` before SIGABRT; **launchd denies many mach lookups with `error = 159: Sandbox restriction`** (mediaserverd -> com.apple.backboard.display.services, remoted, mobiletimerd -> sleepd, identityservicesd -> apsd) and **tccd exits OS_REASON_SANDBOX "profile not found"** - no Sandbox kext/profiles on SWEET; likely cause of many daemon crash loops (next wall after the display). CF's uncaught-exception text never reaches stderr for daemons (no CF handler; libc++abi prints only the type). **Patch 0049** (`xnu/patches/0049-sweet-iokit-trace.patch`): `IOK name: ...` console lines for registry path lookups, child iterators, matching (with result count/class), matching notifications and IOServiceOpen of the processes in boot-arg `sweetiolog` (default backboardd), max 400 lines.
- **CONFIRMED: launchd StandardOut/ErrorPath=/dev/console stops backboardd from launching.** After the in-place rename (boot 0047n-b, log `logs/boot-0047n-b.txt`) backboardd launches again and dies as on v7: sig 6, `___pthread_kill <- abort <- demangling_terminate_handler <- _objc_terminate <- std::terminate <- _dispatch_client_callout <- _dispatch_once_callout <- main+0x9334` (window-server dispatch_once). It never opened AppleCLCD or IOCoreSurfaceRoot (no `SWEET FB/SURF: backboardd` lines) -> throws before/at display detection. **Patch 0048** (`xnu/patches/0048-sweet-devnull-tee.patch`, CI `39037749668` -> `xnu/out-0048`, image `shim/out/shim-boot-0048n.img`): writes to /dev/null by processes named in boot-arg `sweetnull` (default `backboardd,SpringBoard`) are printed as `|name| text`. Boot 0048n (13:48 UTC, log `logs/boot-0048n.txt`): only `|backboardd| libc++abi: terminating due to uncaught exception of type NSException` (CF's reason line goes to os_log, not stderr, despite CFLOG_FORCE_STDERR/OS_ACTIVITY_DT_MODE). Next: pull the whole 16 GiB root from recovery (`adb exec-out dd if=/dev/block/sda34`) to `/run/media/dipa/android/ios-sweet-work/phone-root.img` and read ReportCrash .ips files / logd tracev3 for the exception reason.
- **Persistent log WORKS (boot 0047n on v8, 13:31 UTC; pulled from OrangeFox: 70 KB, 111 flushes, `/run/media/dipa/android/ios-sweet-work/logs/boot-0047n.txt`).** In 3 min **backboardd was never exec'd** (v7 ran it), ~70 bare `exec xpcproxy`, SpringBoard loops on FBSDisplayMonitor (no display), mediaserverd sig 11 loop, locationd, lockdownd sig 5. Suspect the v8 plist (StandardOut/ErrorPath=/dev/console on backboardd). **In-place plist edit from recovery (no reflash):** launchd.plist is one extent at image/partition byte offset 0x1e025f000 (195 blocks; verified bytes identical on phone vs local v8 mount); renamed StandardOutPath->StandardOutPatX and StandardErrorPath->StandardErrorPatX (same length, both jobs) in blocks 68 and 105 via `adb push` + `dd of=/dev/block/sda34 seek=... conv=notrunc,fsync`, read back VERIFIED. Phone now differs from local v8 image in those 2 blocks (files in `/run/media/dipa/android/ios-sweet-work/`). Test boot 0047n 13:38:42 UTC. Recovery kernel has no hfsplus (raw block edits only).
- **Patch 0047: persistent console log (CI `39036478663` -> `xnu/out-0047`, QEMU no panic; phone image `shim/out/shim-boot-0047n.img` = 0047 + sweet-0046hi.adt + 0045n cmdline).** `_cnputs` (all console output: kernel printf + daemons' /dev/console) also appends to a 4 MiB ring in sweet_ufs.c; after the UFS partition is ready and writable (ufsrw=1) a thread writes new ring blocks + header to the LAST 1025 blocks (4 KiB) of userdata every ~1 s and SYNCHRONIZE CACHE (prints `SWEET LOG: console log to the last 4100 KiB ...`). Read: phone to fastboot -> `fastboot boot recovery/recovery.img` (OrangeFox) -> `tools/sweet-log-pull.sh OUT.txt` (adb dd of that area + `tools/sweet-log.py`). Not yet verified on the phone. Panics after the last flush are not in it (screen still shows them). 2x font attempt reverted: XNU's v_scale only scales the progress icon.
- **Boot 0046n on v8 (13:05 UTC, VID_20261017_150522_HSR_120):** phone prints `SWEET SURF: IOCoreSurfaceRoot registered` and `SWEET FB: AppleCLCD 1080x2400 stride 4320 at 0x9c000000, default surface 1` (nubs + match work on hardware). Visible userspace: early boot tasks, launchd_cache_loader, `exec SpringBoard`; no `exec backboardd` / `SWEET FB: backboardd` line seen in the readable frames (video blurry). Frame 00:47: lower half of the screen shows OLDER console text (16:01:12) below newer lines -> unconfirmed hint that a swap copied an old snapshot of the panel (CA reads the default/displayed surface = panel memory). SpringBoard still dies in `-[FBSDisplayMonitor _initWithBookendObserver:transformer:]+1160` (sig 5, slide 0x30960000). **Shim: 2x console font** (`shim/loader.c` Video.v_depth scale field = 1) so phone videos are readable; image `shim/out/shim-boot-0046b.img` = 0046n + 2x font.
- **Patch 0046: built-in IOSurface + IOMobileFramebuffer (2026-10-17, offline, NOT phone-tested).** `xnu/patches/0046-sweet-iosurface-iomfb.patch`: new `iokit/Kernel/arm/SweetSurface.{h,cpp}` (IOCoreSurfaceRoot + IOSurfaceRootUserClient: sel 13/0/4/34/35, traps 0-5, wired buffers mapped into the caller, per-client refs) and `SweetFramebuffer.cpp` (AppleCLCD : IOMobileFramebuffer on /arm-io/disp0: sizes, swap = CPU copy of enabled layers into the ABL panel memory, 60 Hz vsync via sendAsyncResult64WithOptions(CanDrop), panel memory published as the default IOSurface, kernel text console paused on the first swap only with `sweetfb_noconsole=1` (default keeps the console: pausing switches it to serial and would hide panics)); SweetPlatformExpert creates nubs for /arm-io children (not gic) attached to the platform expert (IOPlatformDevice::compareName casts its provider to IOPlatformExpert, so nubs under the arm-io nub never matched - first CI build showed that in QEMU). mkadt: /arm-io/disp0 {device_type display-subsystem, compatible sweet,display, canvas-width 1080, canvas-height 2400}. CI `39021572169` -> `xnu/out-0046`. **QEMU** (`research/q0046-hi.adt`, RAM disk init, msgbuf): `SWEET SURF: IOCoreSurfaceRoot registered`, `SWEET FB: AppleCLCD 1080x2400 stride 4320 at 0x9c000000, default surface 1`, init alive, no panic. Phone image **`shim/out/shim-boot-0046n.img`** (SHA256 9c4d2fe9..., CI `39024108588` with the review fixes: swap bounds check, zeroed 64-bit async ref, port release, 1.5 GiB wired budget, ref leak/race fixes; QEMU re-checked) = 0046 kernel + `shim/out/sweet-0046hi.adt` + the 0045n cmdline; boot it on image v8 (backboardd/SpringBoard log to console) and film. Expected new console lines: `SWEET SURF: <proc> create id ...`, `SWEET FB: backboardd sel N ...`, `SWEET FB: swap ...`. Open question for the next wall: QuartzCore's IOMFB server builds its renderer from Metal first (`CAMetalContextCreate`), GLES only when enabled; how the CPU renderer gets selected on a device without a GPU is not yet established.
- **IOSurface values ABI (offline RE, `/run/media/dipa/android/ios-sweet-work/iosurface-values.md`) - TODO in SweetSurface (0046 only accepts and drops values, so IOSurfaceCopyValue always returns NULL):** sel 9 SetValue in = {u32 id, u32 pad, IOCFSerialize([value, key]) or ([dict] = merge)}, sel 0xb RemoveValue in = {u32 id, u32 pad, key\0} (empty key = remove all); both out 4 bytes = new generation, client accepts only (gen+2)|1. Kernel after each change: gen = (gen+2)|1 (odd, never 0) -> state+0x20, serialized size (>=1) -> state+0x28. sel 0xa in {u32 id, u32 0, u8 0}, out {u32 ?, u32 gen, serialized non-bulk dict}; too small -> 0xe00002db + needed size (client retries x16). sel 0x1b in 0x88: bulk struct 0x70 @0, u64 valid size @0x70, u64 changed mask @0x78, u32 id @0x80 -> copy masked fields into state+0x30 (bit0 32B @0, bit1 16B @0x20, bit2 8B @0x30, bits3-10 1B @0x38..0x3f, bits11-14 24B @0x40/4B @0x58/8B @0x5c/1B @0x64).
- **IOMFB display matching confirmed (offline RE, `/run/media/dipa/android/ios-sweet-work/iomfb-match.md`):** the framework never matches on "AppleCLCD"; any registered IOMobileFramebuffer subclass works. `iomfb_match_callback` reads only `dfr`/`AppleTV`/`external` (CFBoolean, service itself, no parents); internal main display = all absent/false (type 0, name "primary"). Display count = /arm-io children whose device_type starts with "display-subsystem" (count 0 -> CreateDisplayList returns NULL; more nodes than services -> 30 s wait). IOMobileFramebufferOpen fails only on IOServiceOpen failure; canvas-width/height read as 4-byte CFData from the IOService-plane parent (optional). CopyProperty = IORegistryEntrySearchCFProperty on the service only. Patch 0046 (disp0 node, `external`=false, AppleCLCD : IOMobileFramebuffer) fits all of this.
- **IOMobileFramebuffer swap + notification ABI (2026-10-17, offline).** Swap record = fb+0x18, **0x46c bytes**, zeroed by SwapBegin and sent whole by `kern_SwapEnd` = IOConnectCallStructMethod(sel 5, rec, 0x46c, no output). **SwapBegin** = sel 4, no input, 1 scalar out = swap id (stored at rec+0x50). `kern_SwapSetLayer(fb, layer<4, IOSurfaceRef, CGRect a, CGRect b, flags)`: rec+0x54+4*layer = **IOSurface id**; rec+0x104 bit layer = layer enabled (rec+0x108 bit cleared); rect a (int x,y,w,h, scaled) at rec+0x64+16*layer, rect b at rec+0xc4+16*layer; rec+0x114+4*layer = transform from flags&0xf; flag bits 5/31/6/7/8/9 set bytes rec+0x2ca/0x2cc/0x2e3/0x2e5/0x2e6/0x467+layer. A NULL surface only sets the enable bit with zero id. SwapWait = sel 6 scalars [swap id, timeout, 0].
  - **Notifications**: `IOMobileFramebufferScheduleWithDispatchQueue`/`GetRunLoopSource` create an IONotificationPort and `IOConnectSetNotificationPort(conn, type, port, 0)` (kernel `registerNotificationPort`). `kern_EnableNotifications(fb, type, cb, ctx)` = **sel 72 scalars [NotifyCallbackFuncs[type], fb, type, 0]** -> the kernel keeps an async reference {port, func, refcon=fb} per type and fires it with `sendAsyncResult64`. Types: 0 HotPlug, 1 Power, 3 FrameInfo (args[0] = mask of 31-bit keys, args[1] u32, then values), 4 CRC, **5 Vsync**: 6 args, each a 32-bit half in a u64 slot: (ts lo, ts hi), (t2 lo, hi) passed through the time-ingest helper, (t3 lo, hi); the framework then calls the client's vsync callback(fb, ts, t2', t3, ctx). Vsync callbacks are dropped while the notification port has queued messages.

- **IOSurface.framework user-client ABI reversed (2026-10-17, offline, step 2 of the GUI plan).** `ipsw dyld disass research/dsc/dyld_shared_cache_arm64 --image IOSurface` (selector scan script: scratchpad `selscan.py`).
  - Connect (`_iosConnectInitalize`, pthread_once): `IOServiceGetMatchingService(IOServiceNameMatching("IOCoreSurfaceRoot"))`, retried with sleep(1) up to 241 times (a missing service stalls every client ~4 min, no crash); `IOServiceOpen(type 0)`; then **sel 13** (no inputs, struct out 0x18 bytes = `_ioSurfaceLimits`) and requires u16 at out+0x16 == 1 (ABI version); out+0 = offset/plane-base alignment mask, out+4 = bytes-per-row alignment mask (used as (x+m)&~m), +0..+0x14 also copied into IOSurface remote-method init, otherwise logs and closes the connection.
  - **Create = sel 0**: scalar in [parent id or 0], struct in = `IOCFSerialize(props, kIOCFSerializeToBinary)` (OSUnserializeBinary format; keys IOSurfaceWidth/Height/BytesPerRow/BytesPerElement/PixelFormat/AllocSize/PlaneInfo/CacheMode/IsGlobal/...), struct out **0xa68 bytes** ("lock result"). **Lookup = sel 4**: scalar in [id], same struct out. LookupFromMachPort = sel 0x22 (scalar in [port name]); CreateMachPort = sel 0x23 (scalar in [id, options], scalar out [port name]).
  - Lock result (copied to client+0x68, size 0x68 + planes*0x80, min 0xe8): 0x00 u64 base address **mapped in the caller's task**; 0x08 u64 task VA of a per-surface shared state page (+0 u64 registry id, +8/+0xa u16 bound accel ids, +0xc u32 seed, +0x14 u8 tiled, +0x20 u32 value generation, +0x24 YCbCr matrix, +0x28 u32 non-bulk values size, +0x2d u8 displayable, +0x2e u8 sysmem-only, +0x30 0x70 bytes bulk attachments); 0x10 u64 task VA of timestamp page (4 u64 indexed timestamps, +0x20 detach code); 0x18 u32 surface id; 0x1c u32 alloc size; 0x20 width; 0x24 height; 0x28 bytes per row; 0x2c buffer offset; 0x30 pixel format; 0x34 u32 (dcache flush length); 0x38 plane count; 0x40 u16 bytes/element; 0x42 u8 element width; 0x43 u8 element height; 0x44 cache mode; 0x4c u8 subsampling; 0x4d u8 prohibit-use count; 0x50 parent id; 0x54 slice count; 0x58 u64 trace id; 0x60 u64 protection options; planes[n] at 0x68+n*0x80 (+0 width, +4 height, +8 bytes/row, +0xc offset, +0x14 size, +0x18 u16 bpe, +0x1a/+0x1b u8 element w/h, +0x1c u8 component count, +0x1d address format, +0x54 u8 compression type (non-zero -> no CPU base address)).
  - **Traps** (IOConnectTrapN -> `IOUserClient::getTargetAndTrapForIndex`): 0 IncrementUseCount(id, category), 1 DecrementUseCount(id, category), 2 **Lock**(id, options, &seed_out), 3 **Unlock**(id, options, &seed_out), 4 Release(id), 5 Release after a failed create/lookup setup (id).
  - Other selectors: 5 SetYCbCrMatrix, 6 WrapClientImage, 7 WrapClientMemory, 9 SetValue (serialized), 0xa UpdateNonBulkValueCache (struct in 9), 0xb RemoveValue, 0xc BindAccel, 0x11 SetSurfaceNotify (async), 0x12 RemoveSurfaceNotify, 0x13 Log, 0x14 SetPurgeable, 0x15 SetOwnership, 0x16 SetTiled, 0x18 SetTimestamp, 0x19 GetTileFormat, 0x1a CopyDataValueBytes, 0x1b SetBulkAttachments (struct 0x88), 0x1e/0x2e-0x31 (via outlined helpers), 0x1f SetCompressedTileDataRegionMemoryUsed, 0x20 GetGraphicsCommPageAddress, 0x21 SetIndexedTimestamp, 0x24-0x26/0x2d IOSurfaceAccelerator, 0x27-0x29 shared events, 0x2a SignalEvent, 0x2b Set/InitDetachModeCode, 0x2c SetOwnershipIdentity, 0x32-0x34 data properties.
  - => SWEET kernel service: class/name **IOCoreSurfaceRoot** + IOSurfaceRootUserClient; minimum = sel 13, 0, 4, 9/0xa/0xb (values), traps 0-5, 0x22/0x23 later for cross-process surfaces (CA sends surfaces to backboardd by mach port). Memory: IOBufferMemoryDescriptor per surface, mapped into each task with createMappingInTask; ids from a global table.

- **Image v8: daemon logs on the console.** `tools/patch-launchd-plist.py IN OUT LABEL...` rewrites launchd.plist (binary, plistlib): renames every `_PanicOnCrash` to `_PanicOnCrasX` and gives the listed jobs `StandardOutPath`/`StandardErrorPath` `/dev/console` (devfs console is 0622, writable by mobile) plus `OS_ACTIVITY_DT_MODE=YES` (os_log mirrored to stderr) and `CFLOG_FORCE_STDERR=1`. v8 = v7 + that plist for com.apple.backboardd and com.apple.SpringBoard, written through the mount (796310 bytes, root:80 0644), SHA256 in `ios16-root-20H392-v8.img.sha256`, `.simg` ready; boot with `shim/out/shim-boot-0045n.img`. Goal: see backboardd's uncaught exception text and the window server's display probing. ODDITY (unresolved): the v5 raw-image rename at offset 0x1e025f000 is present in the v5-v7 image bytes, but the plist read through a Linux mount of v7 still had the original `_PanicOnCrash` keys; filefrag shows the file as one extent. Never patch file contents through raw offsets again; write through the mount.
- **IOMobileFramebuffer.framework reversed (step 1 of the GUI plan).** `ipsw dyld disass research/dsc/dyld_shared_cache_arm64 --image IOMobileFramebuffer`.
  - Display discovery (`IOMobileFramebufferCreateDisplayList` -> `getDisplayListNumber`): iterates children of `IODeviceTree:/arm-io`, counts nodes whose `device_type` is "display-subsystem" or "ext-display-subsystem" (or `compatible` "paravirtualizedgraphics,gpu"); then `iomfb_populate_display_infos` adds an IOServiceAddMatchingNotification(IOServiceFirstMatch, **IOServiceMatching("IOMobileFramebuffer")**) and runs the run loop up to 30 s until that many services matched. `iomfb_match_callback` reads service properties `dfr`, `AppleTV`, `external` (CFBoolean) and names displays (external ones "%s-%d").
  - `IOMobileFramebufferOpen(service, task, type, &fb)`: `__ioMobileFramebufferAlloc` (CFPreferences com.apple.iokit.IOMobileGraphicsFamily: canvas_width/height, override_display_width/height, override_panel_width/height, benchmark, enable_ktrace), `IOServiceOpen(service, task, type)` (GetMainDisplay passes type 0), `getEDTProperty` reads `canvas-width`/`canvas-height` from the service's IODeviceTree parent, then fills a table of `kern_*` function pointers.
  - User client selectors (`kern_*` -> IOConnectCall*): 3 _kern_GetLayerDefaultSurface[ScalarMethod_stub]; 4 _kern_SwapBegin[ScalarMethod_stub]; 5 _kern_SwapEnd[StructMethod_stub]; 6 _kern_SwapWaitWithTimeout[ScalarMethod_stub] _kern_SwapWait[ScalarMethod_stub]; 7 _kern_GetID[ScalarMethod_stub]; 8 _kern_GetDisplaySize[ScalarMethod_stub]; 10 _kern_SetTVOutMode[ScalarMethod_stub]; 11 _kern_SetWSSInfo[ScalarMethod_stub]; 12 _kern_RequestPowerChange[ScalarMethod_stub]; 13 _kern_EnableStatistics[ScalarMethod_stub]; 14 _kern_SetFlags[ScalarMethod_stub]; 15 _kern_SetDebugFlags[ScalarMethod_stub]; 16 _kern_SetTVOutSignalType[ScalarMethod_stub]; 17 _kern_SetGammaTable[StructMethod_stub]; 18 _IOMobileFramebufferIsMainDisplay[ScalarMethod_stub]; 19 _kern_SetWhiteOnBlackMode[ScalarMethod_stub]; 20 _kern_SwapSignal[ScalarMethod_stub]; 22 _kern_SetDisplayDevice[ScalarMethod_stub]; 23 _kern_SetDigitalOutMode[ScalarMethod_stub]; 24 _kern_GetHDCPDownstreamState[StructMethod_stub]; 25 _kern_GetDigitalOutState[ScalarMethod_stub]; 26 _kern_printDisplayRegs[ScalarMethod_stub]; 27 _kern_GetGammaTable[StructMethod_stub]; 28 _kern_GetDotPitch[ScalarMethod_stub]; 29 _kern_GetDisplayArea[StructMethod_stub]; 30 _kern_EnableDisableDithering[ScalarMethod_stub]; 31 _kern_SetUnderrunColor[ScalarMethod_stub]; 33 _kern_EnableDisableVideoPowerSavings[ScalarMethod_stub]; 34 _kern_SetVideoDACGain[ScalarMethod_stub]; 35 _kern_SetLine21Data[ScalarMethod_stub]; 41 _IOMobileFramebufferEnableMirroring[ScalarMethod_stub]; 42 _IOMobileFrameBufferGetMirroringCapability[StructMethod_stub]; 43 _IOMobileFramebufferSetRenderingAngle[StructMethod_stub]; 44 _IOMobileFramebufferSetMirrorContentRegion[StructMethod_stub]; 47 _kern_HDCPSendRequest[ScalarMethod_stub]; 48 _kern_HDCPGetReply[ScalarMethod_stub]; 49 _kern_SurfaceIsReplaceable[ScalarMethod_stub]; 50 _kern_SetBrightnessCorrection[ScalarMethod_stub]; 51 _kern_SetColorRemapMode[ScalarMethod_stub]; 52 _kern_SwapCancel[ScalarMethod_stub]; 53 _IOMobileFramebufferSetCanvasSize[ScalarMethod_stub]; 54 _IOMobileFramebufferGetMatrix[Method_stub]; 55 _IOMobileFramebufferSetMatrix[Method_stub]; 56 _IOMobileFramebufferKernelTests[StructMethod_stub]; 57 _kern_GetColorRemapMode[ScalarMethod_stub]; 66 _kern_SPLCSetBrightness[ScalarMethod_stub]; 67 _kern_SPLCGetBrightness[ScalarMethod_stub]; 68 _kern_SetParameter[Method_stub]; 69 _kern_SwapSetColorMatrix[StructMethod_stub]; 72 _kern_DisableNotifications[ScalarMethod_stub] _kern_EnableNotifications[ScalarMethod_stub]; 73 _kern_ChangeFrameInfo[ScalarMethod_stub]; 74 _kern_SupportedFrameInfo[Method_stub]; 75 _kern_FactoryPortal[StructMethod_stub]; 77 _kern_GetCurrentAbsoluteTime[ScalarMethod_stub]; 78 _kern_SetBlock[Method_stub]; 79 _kern_GetBlock[Method_stub]; 80 _kern_GetLinkQuality[ScalarMethod_stub]; 81 _kern_SwapCancelAll[ScalarMethod_stub]; 82 _kern_GetProtectionOptions[ScalarMethod_stub]; 83 _kern_CopyLayerDisplayedSurface[ScalarMethod_stub]; 84 _kern_SetContrast[StructMethod_stub]; 85 _kern_GetBufBlock[Method_stub]; 86 _IOMFBGainEncoderFinishEncoding[Method_stub]; UNKNOWN {}
  - => Kernel needs: an `/arm-io` child node with device_type "display-subsystem" (+ canvas-width/height) and an IOService of class **IOMobileFramebuffer** (subclass name match) attached under it, opened with type 0, implementing at least GetDisplaySize(8), IsMainDisplay(18), GetID(7), GetLayerDefaultSurface(3), SwapBegin(4)/SwapEnd(5 struct)/SwapWait(6), Enable/DisableNotifications(72), frame info(73/74), CopyLayerDisplayedSurface(83), plus IOSurface for the swapped buffers. NEXT: CoreAnimation's AppleDisplay/IOMFBDisplay usage of these (constructor, first swap, vsync), then IOSurface.framework's IOSurfaceRoot selectors.
- **GUI PLAN (decided 2026-10-16): CPU rendering + kernel IOMobileFramebuffer.** User: CPU rendering is fine for now (goal = prove the GUI runs), may later research an Apple-style GPU driver for the Adreno 618 -> keep display output and renderer separable. QuartzCore findings (symbols from the cache's .symbols subcache: `ipsw dyld symaddr research/dsc/dyld_shared_cache_arm64 --image QuartzCore`; strings: `ipsw dyld macho ... QuartzCore --strings`):
  - Renderers: `sw_new_context` (CA::OGL::SWContext, full CPU renderer incl. blur, images, IOSurface-backed surfaces, make_buffer_current(WindowServer::Surface)), `gles_new_context`, `metal_new_context`, `new_null_context`. Env knobs include CA_ENABLE_OGL, CA_DISPLAY_TYPE, CA_FORCE_LOCAL_SERVER, CA_FORCE_TIMER, CA_CANVAS_WIDTH/HEIGHT, CA_MAIN_DISPLAY_SCALE/ORIENTATION, CA_DISABLE_RENDER, CA_ALWAYS_RENDER (selection logic not traced yet).
  - `-[CAWindowServer _detectDisplays]` (0x1884e3150) iterates static tables `open_funcs`/`count_funcs` = AppleCLCDDisplay, AppleRGBOutDisplay, AppleWirelessDisplay only; each `count()` = `display_count_of_type(IOMFBDisplayType)` over **`IOMobileFramebufferCreateDisplayList()`**, `open(i)` = `create_display_of_type` -> `CA::WindowServer::AppleDisplay(CFString name, ..., IOMFBDisplayType)` (an IOMFBDisplay driven by IOMFBServer: vsync_callback, frame_info_callback, swaps). `CA::WindowServer::VirtualDisplay` exists but is never auto-detected (explicit API only). => the main display MUST come from an IOMobileFramebuffer kernel service.
  - NEXT: reverse IOMobileFramebuffer.framework: IOMobileFramebufferCreateDisplayList / IOMobileFramebufferOpen (service matching, display type property), the user-client selectors used by IOMFBServer (display size/modes, swap begin/set-layer/end with IOSurface ids, vsync notifications), then the IOSurface kernel side (IOSurfaceRoot user client: create/lookup/lock, memory mapping) that both IOMFB swaps and CA surfaces need. Kernel: SWEET IOMobileFramebuffer service that copies the swapped IOSurface to the 1080x2400 framebuffer at 0x9c000000.
- **logd fixed; backboardd = DISPLAY WALL (boot 0045n on v7, 21:08:57 UTC, frames VID_20261016_230850 00:55-01:28, slide 0x4c3ec000, `research/crash-0045n-v7.txt`).** No `CRASH logd` any more; new daemons run (runningboardd, WirelessRadioManagerd, networkserviceproxy, dasd, cloudpaird, magicswitchd, atc, askpermissiond, ManagedSettingsAgent, containermanagerd uses AKS 0/17). New: locationd sig 11 at CFRunLoopAddSource+132 (NULL source) from its main+0x2af138 in a dispatch_once. **backboardd** sig 6: abort <- std::terminate <- _objc_terminate <- dispatch_once <- main+0x9334 = the "start %{public}@..." wrapper (0x100009264) for **"window server"** (block 0x10000a770 -> dispatch_once body 0x10001d7f0 = StartWindowServer): MTLSetShaderCachePath, `[CAWindowServer serverWithOptions:@{kCAWindowServerDisableUpdatesOnMainDisplay: @YES}]`, `setRendererFlags:`, **`mainDisplay`** -> `displayId` -> `[CADisplay displayWithDisplayId:]`, setWindowServerDisplay:, bounds, pointScale, currentMode, preferredScale, nativeOrientation, touchScales... With no display, mainDisplay is nil and it throws. (HID system and GS start fine before it.) SpringBoard dies on the same missing display (FBSDisplayMonitor). QuartzCore display backends (from the cache's .symbols subcache, `ipsw dyld str`): `CA::WindowServer::AppleCLCDDisplay` (IOMobileFramebuffer hardware) and **`CA::WindowServer::VirtualDisplay`** (open(), new_server, clone_update). `CA_DISPLAY_TYPE` and `CA_FORCE_LOCAL_SERVER` strings exist in QuartzCore but have no direct xref (likely read via a table of CA_* env names). NEXT: find how CA::WindowServer::Server enumerates displays (IOMobileFramebuffer services vs VirtualDisplay / CA_DISPLAY_TYPE) and choose: (a) kernel IOMobileFramebuffer service + IOSurface, or (b) a VirtualDisplay rendered by CA's CPU path (CA::OGL::SW) and copied to the framebuffer.
- **watchdogd + CommCenter + identityservicesd fixed (boot 0045n on v6, 20:41:30 UTC, frames VID_20261016_224133 00:39-01:13, slide 0x20fec000).** `SWEET WDT: watchdogd sel 0 in 0/0 out 1/0 -> ok`, no watchdogd/CommCenter/identityservicesd crashes (CommCenter/identityservicesd now call AKS 0/17/7). usermanagerd boot task runs (UMD_INIT creates primary session uid 501 "mobile", personas 99 System and 199 Default registered with the kernel); `Failed to atomically swap writing file /private/var//keybags/usersession.kb: Operation not supported (45)` (HFS lacks the atomic swap rename; non-fatal so far). Remaining: SpringBoard (FBSDisplayMonitor, no display), backboardd (uncaught exception), mediaserverd, lockdownd (crash inside obfuscated code, main+0x4c1b4?), logd. **logd**: main+0x18160 = `BUG IN LIBTRACE: Failed to migrate directory` from 0x10001801c(dir 0): 0x100016538 requires the dir to exist with uid/gid/mode from the table at 0x10002df14 (0: /private/var/db/diagnostics 272:272 0751, 1: /private/var/db/uuidtext 272:272 0755, 2: /private/var/db/diagnostics/timesync 272:272 0755) plus a `.migrated` file, else XPC "operation 6" to a helper and crash. **Image v7** = v6 + those dirs/markers (also in mkiosroot.sh), SHA256 in `ios16-root-20H392-v7.img.sha256`, `.simg` ready. Boot with `shim/out/shim-boot-0045n.img`.
- **Exit-reason text works (boot 0044n, frames VID_20261016_221726 00:32-00:53, slide 0x22d5c000).** CommCenter/identityservicesd: `couldn't dlopen libobjc-trampolines.dylib: dlopen(/usr/lib/libobjc-trampolines.dylib, 0x0106): tried: '/usr/lib/libobjc-trampolines.dylib' (no such file, not in dyld cache)`: the file only exists in the OS cryptex and dyld does not search cryptexes at ignition_level=1. 19 cryptex files have no root counterpart (OS: DriverKit dyld cache + .symbols, VisualTestKit, libffi-trampolines, libobjc-trampolines, libstdc++ 6.0.9 + 2 symlinks; App: SafariSupport.bundle, AuthenticationServicesAgent, com.apple.Safari.History, passwordbreachd, safarifetcherd, webbookmarksd, webinspectord, webpushd) -> hard-linked (symlinks copied: Linux hfsplus cannot hard-link symlinks); `tools/mkiosroot.sh` does it generically. watchdogd still crashed: the `-wdt_no_pmu` / `/arm-io/wdt no-pmu` check (0x10000a01c) only runs when os_variant_has_internal_diagnostics; otherwise 0x100009b18 looks up IOServiceMatching("IOService") + IOPropertyMatch {IOPMUPrimary: 1} (NSConstantDictionary) and crashes if absent, then IORegistryEntrySetCFProperty(boot stage 0xff) (failure only logged). Patch **0045**: IOWatchdog sets IOPMUPrimary = 1 and accepts setProperties; CI `38961814194` -> `xnu/out-0045`. **Image v6** = v5 + the 19 cryptex links, SHA256 7c610c6a...297a, `ios16-root-20H392-v6.simg` (full flash needed). Boot image `shim/out/shim-boot-0045n.img` (0045 + sweet-0044hi.adt). Still open: SpringBoard (no display), backboardd (uncaught exception, reason none), mediaserverd (Fig NULL dict), logd (main+0x18160), lockdownd (main+0x4c1b4).
- **System survives daemon crashes (boot 0043p, video frames VID_20261016_215006 00:25/00:42/00:54).** With the v5 plist patch no panic: launchd keeps launching (runningboardd, powerd, tccd, healthd, peopled, cryptexd, routined, aksd, mediaremoted, familynotificationd, nanoprefsyncd, navd, cloudpaird, passd, amsaccountsd, accessoryupdaterd, wcd ...). Shared cache slide that boot 0x406b4000 (`research/crash-0043p.txt`). watchdogd still crashed at main+0xb82c from the PMU step: `-wdt_no_pmu` is only honored when os_variant_has_internal_diagnostics; customer builds read `no-pmu` from IODeviceTree:/arm-io/wdt (IORegistryEntrySearchCFProperty) -> mkadt adds /arm-io/wdt {no-pmu}. **cryptexd** sig 6: abort_with_payload <- os_crash_fmt <- `__darwin_arm_secure_boot_chip.cold.7` ("panic: failed to get crypto algorithm") <- `_img4_chip_select_personalized_ap`: reads /chosen use-ddi-secure-boot, allow-ecid-mismatch, crypto-hash-method ("sha1" | "sha2-384"), /chosen/asmb lp-smb0/1 -> mkadt adds crypto-hash-method "sha2-384". **identityservicesd** sig 6 = same `_objc_fatal` in imp_implementationWithBlock as CommCenter (block trampolines; message needed). lockdownd sig 5 at main+0x4c1b4. Patch **0044**: crash report adds `CRASH name reason ns N code X: text` (exit reason description = abort_with_payload text). CI `38959096811` -> `xnu/out-0044`, QEMU OK. Image `shim/out/shim-boot-0044n.img` = 0044 + `shim/out/sweet-0044hi.adt` (wdt no-pmu, crypto-hash-method) + cmdline (wdt=-1, no -wdt_no_pmu).
- **First symbolicated daemon crashes (boot 0043u on journaled v4, 19:38:53 UTC; video frame chat image 36; transcribed in `research/crash-0043u.txt`; shared cache slide 0x40d60000 for every process).** (Gemini's video transcription invented values, use frames only.) `tools/sweet-crash.py research/dsc/dyld_shared_cache_arm64 x research/crash-0043u.txt`:
  - **watchdogd** pc main+0xb82c (`_os_crash` trap helper) from 0x100009bb0 = set PMU boot stage via IORegistry (no PMU) -> fix: boot-args `wdt=-1 -wdt_no_pmu` (Apple's own test mode writes "%s wdt=-1 -wdt_no_pmu"; watchdogd logs "skipping setting PMU boot stage because -wdt_no_pmu found in boot-args or no-pmu found in EDT"). Kernel effect of wdt=-1: sched hygiene debug off, zone_exhausted_timeout -1 (harmless).
  - **SpringBoard** sig 5 in `-[FBSDisplayMonitor _initWithBookendObserver:transformer:]+1160` <- `+[FBDisplayManager sharedInstance]` <- `FBSystemShellInitialize` <- `SBSystemAppMain`: no main display. GUI WALL: display service (IOMobileFramebuffer / CoreAnimation display).
  - **backboardd** sig 6: abort <- std::terminate <- _objc_terminate (uncaught exception; message not shown).
  - **CommCenter** sig 6: `_objc_fatal` in `imp_implementationWithBlock` (from `+[_PFRoutines initialize]`, CoreData): objc block trampolines cannot be allocated -> likely kernel gap (trampoline page remap); will hit many processes.
  - **mediaserverd** sig 11: CFDictionaryGetValue(NULL) in FigNotificationListenerStartNotifications (routing session manager).
  - **logd** sig 5 at its main+0x18160 (bt main+0x9dfc); lockdownd sig 5 (not yet symbolicated).
  - Image v5 = v4 + launchd.plist (`/System/Library/xpc/launchd.plist`, contiguous at image offset 0x1e025f000, 1456980 bytes) with the 7 `_PanicOnCrash` keys renamed `_PanicOnCrasX` in place (raw image patch, no metadata change) -> `diff-v4-v5.simg` = 7 blocks; v5 SHA256 78f96974...185a. Boot image `shim/out/shim-boot-0043p.img` = 0043 + `wdt=-1 -wdt_no_pmu`.
- **0043 console crash reports (QEMU verified); image `shim/out/shim-boot-0043u.img`; NEXT: flash v4 + boot 0043u.** Boot 0042u (video photo IMG_20261016_211646): short exec lines work; watchdogd crashes with NO `SWEET WDT:` line (fails before its first IOWatchdog call: lookup or IOServiceOpen, or elsewhere); lockdownd, SpringBoard, mediaserverd, CommCenter, identityservicesd, backboardd, watchdogd all crash repeatedly ("Too many corpses being created" = corpse limit, no crash reports). AKS callers: lockdownd (0, 7), imagent/sleepd (0, 17, 7), backboardd (0, 17), UserEventAgent (0, 7, 102, 103 -> unsupported). Patch **0043**: `sweet_crash_log` (osfmk/kern/exception.c, called from proc_prepareexit for crash exits on the current proc) prints `CRASH name[pid] sig S code (exc<<32|code) sub X slide SR mh MH`, `CRASH name pc lr sp fp far`, `CRASH name bt` (10 fp frames); AKS sel 103 notify_state_is_set -> 0. CI `38954520419` -> `xnu/out-0043`. QEMU test: init forks, child `brk #1`: `CRASH launchd[2] sig 5 code 0x600000001 sub 0x1000004f0 slide 0x0`, pc correct, parent keeps running (pid 1 crashes panic before proc_prepareexit, so test with a child). `tools/sweet-crash.py CACHE ROOT [report]` symbolicates typed-in CRASH lines (`ipsw dyld a2s` with addr - slide; main binary offsets = addr - mh + 0x100000000).
- **v3 reflashed 18:50-18:55 UTC (`research/flash-userdata-v3b.log`, 24/24 OKAY); 0042u booted 19:01:17 UTC on the clean disk (`research/boot0042u-2.log`), SLOW MO VID pending (watchdogd failure reason).** ABL hangs on the first `fastboot boot` after every big flash; user re-enters fastboot. User gave standing approval to reflash/boot without asking (memory standing-flash-approval). Commits now end with `Co-Authored-By: dipa-studio <183933817+dipa-studio@users.noreply.github.com>` (user request; never a Claude trailer).
  - watchdogd flow: connect_to_kext (0x100005408): IOServiceGetMatchingService("IOWatchdog") fails -> "failed to discover" + _os_crash; IOServiceOpen(type 1) fails -> "IOServiceOpen failed with error : 0x%x" + _os_crash. Then sel 0 (out 1 scalar): 0 -> "userspace monitoring disabled", 0x100009bb0, sleep 2, exit(0); nonzero -> "userspace monitoring enabled", normal operation.
  - **Image v4 (JOURNALED):** `tools/mkiosroot.sh` now does `mkfs.hfsplus -J`, mounts with `-o loop,force`, adds the /System/Library/Caches/com.apple.dyld hard links (44) and /private/var/keybags/systembag.kb (0700/0600 root). Built from the IPSW dmgs (OS 087-86698-044, SystemOS 087-86593-047, AppOS 087-86715-047) -> `/run/media/dipa/android/ios-sweet-ipsw/ios16-root-20H392-v4.img` SHA256 fba4aeae...ec0f9 + `.simg`. Header: attr 0x80002100 (unmounted, journaled), journal info block 129, journal 8 MiB at 532480 flagged need-init. Linux `fsck.hfsplus -n` reports "Volume header needs minor repair" on any fresh journaled volume even after -y (quirk). QEMU: 64 MB journaled test root (`rd=md0 rootrw=1`, 0042 kernel): `hfs: Initializing the journal (joffset 0x3000 sz 0x80000)` -> mounted -> init runs, no panic. NEXT: flash v4 (full), boot 0042u.
- **SPRINGBOARD STARTS (boot 0041u 18:39:53 UTC, photo IMG_20261016_204142).** backboardd, bluetoothd, fairplayd.H2, SpringBoard (pid 111, crashed: "Too many corpses"), xpcproxy run; `SWEET AKS: backboardd sel 0 -> 0`, `sel 17 in 1/0 out 0/4096 -> 0`. Panic: watchdogd[113] exited, namespace 2 subcode 5 (SIGTRAP = its _os_crash): watchdogd crashes on purpose when IOServiceGetMatchingService("IOWatchdog") fails ("connect_to_kext() unexpectedly failed") or IOServiceOpen(type 1) fails ("IOServiceOpen failed with error"); IOWatchdog DOES register (QEMU msgbuf: `SWEET WDT: IOWatchdog registered`), cause not on screen yet -> need video. Note `wdt_test=no_user_checkin` makes watchdogd log "detected testing boot-args to not run, exiting" (path not reached here?). **HFS CORRUPTION:** `hfs_swap_BTNode: offset #0 invalid (0xBC1D) (blockSize 0x2000 numRecords 81)`, `node=19677 fileID=4` (catalog), `hfs_mark_inconsistent` repeated. Likely cause: non-journaled HFS + unclean panics while writing (0038e wrote a 2.7 GB core then panicked; every boot since ends in panic). Plan: reflash v3 (clean), longer term HFS journaling. Patch **0042**: one short `exec NAME` console line instead of the 3-line "Allowing spawn of iOS binary" notice; CI `38949451276` -> `xnu/out-0042`; image `shim/out/shim-boot-0042u.img` (same cmdline as 0041u).
- **LAUNCHD DAEMONS RUN (boot 0039u, 18:29:13 UTC, photo IMG_20261016_203052).** With `launchd_unsecure_cache=1` all boot tasks pass and launchd starts LaunchDaemons (pids > 100: identityservicesd 114 and lockdownd 106 crash, "Too many corpses being created"). Fatal: `watchdogd: ERROR: failed to discover watchdog KEXT service` -> exit (namespace 2 = signal, subcode 5) -> `_PanicOnCrash` panic. watchdogd: IOServiceMatching("IOWatchdog"), IOServiceOpen type 1, IOConnectCallScalarMethod sel 0/1 (check in)/3/4 (disable/enable userspace monitoring)/5, IOConnectCallStructMethod sel 2 (1 KiB in) and 9 (small out); VM path ("detected virtual machine environment and no watchdog KEXT found, exiting...") only when it detects a VM. Console also flooded with `hfs: set hardlink bit on vol=iOSRoot cnid=321318` (Linux-made hard links lack kHFSHasLinkChainBit; repaired only in memory on each lookup). Patches **0040** (`iokit/Kernel/arm/SweetWatchdog.cpp`: IOWatchdog + IOWatchdogUserClient, all selectors succeed with zeroed outputs, each logged once as `SWEET WDT: ...`) and **0041** (sweet_hfs hfs_catalog.c: the three link-repair printfs limited to 8 per boot); CI `38948245372` PASSED -> `xnu/out-0041` (QEMU regression OK). Image `shim/out/shim-boot-0041u.img` (0041 + sweet-0038hi.adt + ufsrw rootrw + launchd_unsecure_cache=1) booted 18:39:53 UTC (`research/boot0041u.log`), photo pending.
- **v3 FLASHED + keybag passes; next wall AMFI (launchd_cache_loader).** User said "flash, nothing to lose": `fastboot -S 512M flash userdata ios16-root-20H392-v3.simg` 17:51:52-17:57:01 UTC, 24/24 chunks OKAY (`research/flash-userdata-v3.log`). userdata = v3 (SHA256 fa84274c...22df) until the next rw boot. ABL fastboot then hung ("Sending" forever, `reboot bootloader` timed out) until the user re-entered fastboot by hand (common Xiaomi ABL crash). Boot 0038e 18:06:15 UTC (`research/boot0038e-3.log`), photos IMG_20261016_200812/200838: keybag OK, then boot tasks tzinit (`Bad zoneinfo link`, resets to system partition, OK), finish-restore, finish-demo-restore, sysstatuscheck, prng_seedctl (`failed to load kernel prng seed`, `failed to load virtual random (-147)`, AllowCrash), auearlyboot, then **launchd_cache_loader: `abort: Unable to find AMFI`** -> 2.7 GB core written to /cores in 91 s -> launchd panic `launchd_cache_loader[22] exited -- exit reason namespace 7 subcode 0x1`. launchd_cache_loader: SecStaticCodeCheckValidity of /System/Library/xpc/launchd.plist with detached .sig, then IOServiceMatching("AppleMobileFileIntegrity") + IOServiceOpen type 0 + IOConnectCallMethod sel 6 (1 scalar = 1, struct in = cdhash) = trust the cdhash, then sends the cache to launchd. Boot-arg `launchd_unsecure_cache=1` skips signature + AMFI ("Using unsecure cache"); the value is parsed with strtoul base 10 (helper 0x100002da8), so a path = 0 = off: boot 0039w (18:17:13 UTC, `=/System/Library/xpc/launchd.plist`, photo IMG_20261016_202008) still aborted `Unable to find AMFI` (core dump now skipped: `Failed to generate core file ... error 14`, so 0039 works). Image `shim/out/shim-boot-0039u.img` uses `launchd_unsecure_cache=1`. Patch **0039**: do_coredump = 0 on SWEET (kern.coredump sysctl still works); CI `38945267341` -> `xnu/out-0039` (_do_coredump now in __common). Image `shim/out/shim-boot-0039w.img` = 0039 + sweet-0038hi.adt + ufsrw rootrw + `launchd_unsecure_cache=/System/Library/xpc/launchd.plist`. TODO later: real AppleMobileFileIntegrity IOService (sel 6 trust cdhash etc.).
- **Image v3 ready, awaiting user "flash".** Boot 0038w 17:38:10 UTC, photo (chat image 30): `SWEET AKS: keybagd sel 0 -> 0x0`, `sel 14 out 1/0 -> 0x0` (x2), `MKB_INIT: mount is with NO CPROTECT ... does not support Data Protection`, `System Keybag loaded`; then keybagd still opens /private/var/keybags/systembag.kb (0x100012d3c, for BackupKeyBagKeys) -> ENOENT, `no-effaceable-storage` not set -> `Can't load the keybag. tears in rain... Time to die` -> `FATAL KEYBAG ERROR: kb_load` -> reboot -> Halt/Restart Timed Out panic. Fix: ADT `/defaults/no-effaceable-storage` (mkadt.py; `shim/out/sweet-0038hi.adt`, `research/q0038-hi.adt`, QEMU OK) + file `/private/var/keybags/systembag.kb` (0600 root, dir 0700; XML plist {KeyBagKeys: data}). **v3 image** `/run/media/dipa/android/ios-sweet-ipsw/ios16-root-20H392-v3.img` = v2 + that file, fsck OK, SHA256 fa84274c...22df; `ios16-root-20H392-v3.simg` (img2simg: zero blocks become FILL chunks, so a full flash overwrites every block the rw boots changed). Flash: `fastboot -S 512M flash userdata ios16-root-20H392-v3.simg`, then boot `shim/out/shim-boot-0038e.img` (0038 + sweet-0038hi.adt + ufsrw=1 rootrw=1).
- **0038 AppleKeyStore (CI 38938744130 PASSED -> `xnu/out-0038`; QEMU msgbuf: `SWEET AKS: AppleKeyStore registered (no passcode, unlocked)`; phone image `shim/out/shim-boot-0038w.img` booted 17:38:10 UTC, `research/boot0038w.log`, photo pending).** QEMU full kernel log trick (fb.txt is only the last screen): `llvm-nm KERNEL | grep _msgbufp` -> `--hmp "x /1gx ADDR"` gives struct msgbuf address (static, 0xfffffe0007b56678 on 0038) -> `--hmp "x /3gx STRUCT"` gives bufc (3rd quad) -> `--hmp "memsave BUFC 0x20000 \"FILE\""` (quote the file name), `tr -d "\0" < FILE`. Same inputs give the same addresses. Boot 0037w 17:08:35 UTC, photo IMG_20261016_191052: bindfs fixed mount; mount-phase-1/2 pass; `cc_fips_test` boot task: all corecrypto FIPS POST tests PASSED in userspace; then keybag boot task `keybagd --init`: `MKB_INIT: FATAL KEYBAG ERROR: failed to load system bag`, `Could not get options entry from the device tree` (x2, IODeviceTree:/options = NVRAM, non-fatal), `REBOOTING INTO RECOVERY MODE` -> reboot -> panic `Halt/Restart Timed Out @IOPlatformExpert.cpp:884` (no restart path on SWEET).
  - keybagd (static libaks): load_devicebag (0x100012c30) calls aks_get_system (sel 14, 0-1 scalar in, 1 out) and loads /private/var/keybags/systembag.kb only if the result is 0xe00002f0 (NotFound); any other error -> fatal; SUCCESS -> skip the file (userspace-reboot path). systembag.kb is a plist {KeyBagKeys}; decrypted with effaceable storage unless IODeviceTree:/defaults has `no-effaceable-storage`. Image has no /private/var/keybags. has_data_protection: statfs of /private/var; no cprotect on our HFS -> device-bag volume mapping skipped.
  - libaks connection: IORegistryEntryFromPath / IOServiceMatching("AppleKeyStore"), IOServiceOpen type 0, then selector 0 (no args) must succeed.
  - **AppleKeyStore selector map (iOS 16.7 AppleKeyStore.framework, via `ipsw dyld disass`):** 0 open, 2 create_bag, 3 save_bag, 4 unload_bag, 5 set_system_with_passcode, 6 load_bag, 7 get_lock_state (1 in, 1 out; bit 2 = unlocked since boot), 9 unlock_device, 10 wrap_key, 11 unwrap_key, 12 unlock_bag/test_stashed_kek, 13 lock_bag, 14 get_system, 15 change_secret_se, 16 internal_state, 17 get_device_state (1 in, struct out <=4K: DER SET of SEQUENCE{UTF8 key, INTEGER}: ss state, sls lock_state (MKBGetDeviceLockState returns it), sb backoff, sbo, sfa failed attempts, sfao, sgs generation, sas assertions, sgpe grace, srcd countdown, sr reserved), 18 recover_with_escrow_bag, 19 obliterate_class_d, 20 drain_backup_keys, 21/22 set/clear_backup_bag, 23 get_bag_uuid, 24 rewrap_key_for_backup, 26/27 assert_hold/drop, 30/31 set/get_configuration, 33-37 stash, 38 auth_token_create, 40 generation, 41 fdr_hmac_data, 42 verify_password, 43 _aks_operation, 44 remote_session, 49/50 signing keys, 51/53/54 stash enable/persist/escrow, 55 unload_session_bags, 57/58 remote peer, 59-62 smartcard, 63 migrate_s_key, 65 set_keybag_for_volume_with_cookie_persona, 66/67 sync bags, 68 copy_volume_cookie_persona, 69-73 se_*, 74-79/84/85/99 fv_* (FileVault/VEK), 80/81 absinthe, 82 make_public_backup_bag, 83 drop_auxiliary_auth, 86 kext get/set options, 87 invalidate_bag, 88-91/94/95/106/107 se_*, 92 lower_iteration_count, 93 get_internal_info, 96-98/117 keybag_persona create/list/delete, 100/101 assert promote/consume, 102/103 notify_state set/is_set, 104 fairplay, 105 change_secret_epilogue, 108 delete_xart_leak, 110-113 backup volume, 114 sealed_hashes_set, 115 prewarm_sps, 118-128 AKSIdentity*/AKSGetLastUser.
  - Patch **0038**: `iokit/Kernel/arm/SweetKeyStore.cpp` (class AppleKeyStore on IOResources, IOUserClientClass AppleKeyStoreUserClient; personality in KernelConfigTables.cpp): 0/4/5/9/12/13/26/27/55/102 success, 14 -> handle 0, 7 -> 0x4, 17 -> DER state (ss 4, sls 0), others kIOReturnUnsupported; logs `SWEET AKS: <proc> sel N arg0 in a/b out c/d -> ret` for every call.
  - Tools: shared cache copied to `research/dsc/` (git-ignored; ipsw needs a writable dir for its .a2s symbol cache); `ipsw dyld disass research/dsc/dyld_shared_cache_arm64 --image AppleKeyStore|MobileKeyBag`; scratchpad `annot2.py BIN DIS FIXUPS` annotates llvm-objdump output with strings and import names (`ipsw macho info --fixups`).
- **0037 bindfs (phone boot 0037w pending photo).** Boot 0036mw 16:57:47 UTC, photo IMG_20261016_190102: WRITABLE ROOT WORKS: `/dev/ufsroot0 on / (hfs, local, noatime)` after mount_hfs update (GetMasterBlock EBUSY harmless), coredump of mount written to /cores (rw). Then `mount: failed to mount /private/preboot/5CBE3601.../usr/standalone/firmware -> ...: Operation not supported by device (19)` -> exit 74 -> launchd panic `mount[2] exited`. Cause: the macOS-derived config had nullfs but no bindfs (ENODEV = unknown fs type). Caller passes env 0 -> bind not required, ENOENT (missing source dir) tolerated. Patch **0037** adds `bindfs` to FILESYS_BASE in MASTER.arm64.sweet; CI `38936550483` -> `xnu/out-0037` (bindfs_vfsops present; QEMU probe regression OK). Image `shim/out/shim-boot-0037w.img` (0037 + sweet-0036hi.adt + ufsrw=1 rootrw=1) booted 17:08:35 UTC (`research/boot0037w.log`). NOTE: userdata has now been modified by rw boots; it no longer equals the v2 image, so sparsediff with v2 as OLD is not safe any more (full reflash or a new baseline needed).
- **0036 phone: launchd boot tasks run; mount -P 1 needs /chosen/boot-manifest-hash.** Boot 0036hr 16:15:32 UTC, photo IMG_20261016_185236: platform check passes; fsck boot task runs (`fsck: not booting main or diagnostic OS. Skipping fsck on OS container`); mount-phase-1: `failed to get filesystem info` x2 (no IODeviceTree:/filesystems/fstab, non-fatal), `mount: data volume missing, but not required in env: 0`, mount_hfs update of /: `GetMasterBlock: Error 16 opening /dev/ufsroot0` (EBUSY, mounted block dev, non-fatal) then mount() EROFS (read-only boot) -> `mount: / failed with 1`; then `failed to get boot-manifest-hash` -> errx exit 66 -> launchd panic `mount[3] exited`. /sbin/mount: fn 0x100005f90 reads IODeviceTree:/chosen boot-manifest-hash (hex), bindfs-mounts /private/preboot/<HEX>/usr/standalone/firmware (ENOENT tolerated unless required). `tools/mkadt.py` now adds `boot-manifest-hash` = SHA-384("sweet boot manifest") (5CBE3601...5205). ADTs `shim/out/sweet-0036hi.adt`, `research/q0036-hi.adt` (QEMU probe OK, csops 0x26000001). Image `shim/out/shim-boot-0036mw.img` (0036 + new ADT + ufsrw=1 rootrw=1), booted 16:57:47 UTC (`research/boot0036mw.log`): FIRST WRITABLE BOOT of userdata (restore source: v2 image on SSD).
- **0036 CS_SIGNED (phone boot 0036hr pending photo).** Phone boot 0035hr 2026-10-16 15:57:02 UTC (`research/boot0035hr.log`, photo IMG_20261016_180249): highmem works on hardware; shared cache maps (trust-cache warnings only), Apple launchd runs (`Darwin Bootstrapper Version 7.0.0`, `entering ondemand mode`), starts boot task fsck, then userspace panic `boot task is not a platform binary (fsck, /sbin/fsck)`. launchd+0x3fea0: `csops(pid, CS_OPS_STATUS)` must have bit 0x04000000. Cause: nothing set CS_SIGNED (AMFI does it in vnode_check_signature), so csproc_get_blob() returns NULL for every process and csops never reports CS_PLATFORM_BINARY (also breaks per-process cdhash/entitlement queries). QEMU probe init (`csops` status printer, scratchpad csq/) on 0035: `0x02000001`; patch **0036** (`*cs_flags |= CS_SIGNED` in the SWEET AMFI hook), CI `38929635791` -> `xnu/out-0036`: `0x26000001`. Images `shim/out/shim-boot-0036hr.img` / `-0036hw.img` (same cmdlines as 0035). 0036hr booted 16:15:32 UTC (`research/boot0036hr.log`). Next launchd boot tasks (embedded __config plist): fsck -qL and mount -P 1/2 (RequireSuccess); no /etc/fstab on the image.
- **0035 ENTITLEMENTS + PLATFORM BINARIES (QEMU verified).** `xnu/patches/0035-sweet-amfi-entitlements-platform-binaries.patch`: new `iokit/Kernel/arm/SweetEntitlements.cpp` (OSObject subclass: OSDictionary from OSUnserializeXML of the signature's XML entitlements + original XML for CS_OPS_ENTITLEMENTS_BLOB); `bsd/kern/sweet_amfi.c` answers queryEntitlementBoolean/String(+WithProc, string also matches array members), copyEntitlementAsOSObject(+WithProc, retained), asdict (retained), get_xml (kalloc_data copy); built-in MAC policy "SWEET AMFI" (registered from bsd_init before vfs/exec) with mpo_vnode_check_signature: every signed binary on the MNT_ROOTFS mount gets CS_PLATFORM_BINARY (stand-in for AMFI's static trust cache: iOS system binaries are ad-hoc, cd_flags 0x2, platform byte 0), and attaches entitlements ONLY for the writable copy (cs_blob != csb_ro_addr; revalidation passes the RO blob). LESSON: first version attached in adjustContextWithoutMonitor -> QEMU `unable to adjust OSEntitlements context without monitor: 53` because ubc_cs_convert_to_multilevel_hash (4K-page signatures on 16K kernel) sets csb_entitlements_blob = NULL; ALL iOS 16 binaries (launchd, backboardd, SpringBoard) use 4K code pages, so this would have broken launchd on the phone. Boot-arg `sweet_amfi_debug=1` logs `SWEET AMFI: <ident>: N entitlements (test: ...)`. `tools/mkinit.py OBJ OUT [ENTS.plist]` adds an XML entitlements blob (special slot -5; default output byte-identical). QEMU `research/q0035-ent` (RAM disk `research/root-hfs-ent.img`, init with 3 test entitlements, highmem): `org.sweet.init: 3 entitlements (test: bool 1 string 1 array 1)` then init PID 1. MAC policies loaded: 0034 = 1, 0035 = 2 (QMP `mac_policy_list`). CI `38909807230` -> `xnu/out-0035`. Phone images: `shim/out/shim-boot-0035hr.img` (highmem, ro), `-0035hw.img` (highmem, +ufsrw=1 rootrw=1), `-0035r.img` (low mem fallback).
- **PHONE TEST ORDER (updated):** 0035hr -> if instant reset, 0035r -> then 0035hw.

- **HIGHMEM: XNU in the upper DDR bank, ~3.95 GiB (was 1.2 GiB).** Live FDT memory = <0x80000000 2G> + <0x1_00000000 0xfcc00000>; all fixed reserved-memory carve-outs are in the low bank (highest: ramdump_fb 0xaf000000, rmtfs ~0xfde01000), dynamic pools have alloc-ranges <= 0xffffffff, UFS node has no `iommus` (Linux DMAs anywhere). `tools/mkadt.py --highmem` sets /chosen dram-base 0x100000000 dram-size 0xfcc00000; `tools/mkpayload.py` now takes phys_base/mem_size from the ADT (default payloads byte-identical, verified); `tools/qemu-sweet.py` sizes -m from the payload (8G for highmem). Patch **0034** (`0034-sweet-ufs-dma-above-4g.patch`): UFS refuses DMA memory above 4G without UFSHCI CAP.64AS (bit 24), logs `DMA at 0x...`. CI `38905889883` success -> `xnu/out-0034`. **QEMU verified** (`research/q0034-hi`, ADT `research/q0034-hi.adt` --qemu --highmem, HFS RAM disk): phys_base 0x100000000, init PID 1 heartbeat, no panic; `max_mem` = `mem_size` = 0xfcc00000 read via QMP (`research/q0034-hi-mem`). Phone images: `shim/out/shim-boot-0034hr.img` (read-only) / `-0034hw.img` (+ufsrw=1 rootrw=1), ADT `shim/out/sweet-0034hi.adt` (asmb SIP + sweet-ufs + highmem). PHONE RISK: unknown runtime TZ/XPU protection in the upper bank would show as an instant reset; fall back to 0033r/w. Watchdog ruled out for the overnight reset: msm-watchdog bark is 20 s (qcom,bark-time 0x4e20) yet panic screens stay up for many minutes.

- **Offline research 2026-10-16 (user away, phone unavailable). Images rebuilt** `shim/out/shim-boot-0033r.img` / `-0033w.img` now also carry `wdt_test=no_user_checkin`. NEXT ON PHONE: boot 0033r (expect past in6_nigroup), then 0033w (first writes: rw root fixes HFS link-chain bits itself and gives /var for launchd sockets /var/run/syslog, /var/run/lockdown.sock).
- **launchd.plist** (`/System/Library/xpc/launchd.plist`, compiled; 532 daemons, 66 RunAtLoad/KeepAlive, list in scratchpad `early-daemons.txt`). `_PanicOnCrash` daemons: containermanagerd/usermanagerd (InternalOnly), lockdownd/remoted/trustd/remotepairingdeviced (AutomationOnly), **watchdogd unconditional** (KeepAlive SuccessfulExit=false). watchdogd needs IOKit `IOWatchdog` kext service; if absent it exits only when `kern.hv_vmm_present` (ADT `/defaults/vmm-present`, hvg_sysctl.c) or with boot-arg `wdt_test=no_user_checkin` ("detected testing boot-args to not run, exiting"; reads kern.bootargs). Using the boot-arg (vmm-present would change many daemons; keep as an option).
- **GUI path research (QuartzCore in the shared cache, `ipsw dyld str CACHE STR`, ~10 s/search):** CA::WindowServer has IOMFBServer/IOMFBDisplay (Apple DCP/IOMobileFramebuffer), AppleCLCDDisplay, AppleRGBOutDisplay, **VirtualServer/VirtualDisplay** and **MemorySurface**, EAGLServer. Renderers: CA::OGL::MetalContext, GLContext and a **CPU software rasterizer CA::OGL::SW** (samplers/blend modes; "image is too large for software renderer"). Env knobs: `CA_ENABLE_OGL`, `CA_DISPLAY_TYPE`, `CA_FORCE_LOCAL_SERVER` (249 CA_* vars). Hypothesis (unverified): backboardd's render server could run a VirtualServer/MemorySurface with the SW renderer and we copy the surface to the ABL framebuffer -> needs disassembly of CA::WindowServer server creation. Expected other GUI walls: IOSurface (closed-source kext; needs a reimplementation), IOMobileFramebuffer user client, IOHID touch events, AppleKeyStore/keybag (SEP) for lock state, MobileGestalt answers (AppleCLCD etc.).

- **0032r RESULT (boot 05:07:50 UTC, `research/boot0032r.log`, photo IMG_20261016_071200): SHARED CACHE MAPPED, LAUNCHD RUNS.** With SIP relaxed (ADT asmb) the `not in trust cache` lines are only warnings for every subcache (.31 ... .42.dyldlinkedit); no SIP rejection; libSystem loads; launchd configures networking (`skip attaching fsw to lo0 using legacy TX model`) -> kernel data abort far 0x28 in `SHA1Init` (symbolized as sha1_init) from `in6_nigroup` (IPv6 on lo0): g_crypto_funcs NULL. Kernel addresses are unslid: `~/swift/usr/bin/llvm-symbolizer --obj=KERNEL ADDR` works directly.
- **0032** BearSSL SHA-1 (`0032-sweet-bearssl-sha1.patch`), **0033** BearSSL SHA-384/512 (`0033-sweet-bearssl-sha384-sha512.patch`, BearSSL ctx stored in SHA512_CTX, static-asserted to fit; ubc_subr.c uses SHA-384 for code directories). `0020-stage-bearssl.sh` now also stages hash/sha1.c, hash/sha2big.c, codec/{dec,enc}{32,64}be.c. CI `38854909053` success (0032-only run `38854802073` superseded). Kernel `xnu/out-0033` (SHA1Init -> _br_sha1_init verified by disassembly; nm symbols have a leading underscore). Images (ADT sweet-0032): `shim/out/shim-boot-0033r.img` (read-only), `shim-boot-0033w.img` (+ufsrw=1 rootrw=1). Still NULL g_crypto_funcs users: des, chacha20poly1305, rsa, aesxts, rand, flow_divert.
- `research/check-patch-order.py` now skips patches touching CI-staged sweet_hfs sources (0031) instead of stopping.

- **0031r RESULT (boot 05:03:52 UTC 2026-10-16, `research/boot0031r.log`, photo IMG_20261016_070508): SHARED CACHE FOUND.** dyld now opens `dyld_shared_cache_arm64` (v2 image hard links), kernel refuses to map it: `shared_region: ... map(...'dyld_shared_cache_arm64'): not in trust cache` -> `vnode is not SIP-protected` (vm_unix.c: macOS arm64 path needs trust cache, else root-owned + SF_RESTRICTED unless CSR_ALLOW_UNRESTRICTED_FS) -> `dyld cache '(null)' not loaded: syscall to map cache into shared region failed` -> libSystem not loaded -> coredump to /cores fails error 30 (EROFS) -> panic initproc failed -> "MACH Reboot" (spins; screen kept). Lots of `hfs: set hardlink bit on vol=iOSRoot cnid=... linkid=...` spam (Linux-made hard links lack the link-chain bit; read-only mount cannot persist the fix). FIX: ADT `/chosen/asmb` with `lp-sip0`=0x6f (u64; incl. CSR_ALLOW_UNRESTRICTED_FS) and `lp-sip1`=1 (unauthenticated root), `tools/mkadt.py` -> `shim/out/sweet-0032.adt`. Images with kernel 0031: `shim/out/shim-boot-0032r.img` (read-only) and `shim-boot-0032w.img` (+ufsrw=1 rootrw=1).

- **2026-10-16 morning:** userdata now = **v2** image (`diff-v1-v2.simg` flashed 21:06:50 UTC 2026-10-15, OKAY, `research/flash-userdata-diff-v2.log`); future diffs use `ios16-root-20H392-v2.img` as OLD. Booted `shim-boot-0029k.img` (ignition_level=1) right after (`research/boot0029k-v2.log`); **no photo** (user asleep). Next morning the phone was in PixelOS recovery = some hardware reset (ABL then booted Android, which cannot use userdata). OBSERVATION: our kernel cannot reset the SoC itself (`PE_halt_restart` is never set; reboot/halt print "MACH Reboot"/"CPU halted" and spin), so the reset came from outside XNU: Qualcomm watchdog or a TZ/XPU violation. Unknown which; re-boot 0029k and watch/video until the reset. Do NOT tap factory reset/format data in recovery (would wipe the iOS image).
- **0030** (`xnu/patches/0030-sweet-ufs-writes.patch`, CI `38852655542`): UFS WRITE(10) + read-modify-write for partial 4 KiB blocks + SYNCHRONIZE CACHE (DKIOCSYNCHRONIZE), only with boot-arg `ufsrw=1`; `ufs_write_blocks` re-checks partition bounds before every write (only place data goes out).
- **0031** (`xnu/patches/0031-sweet-read-write-root.patch`, CI `38852837176`): boot-arg `rootrw=1` clears MNT_RDONLY before the root mount (no data volume on sweet: /private/var is on the root; image has no /etc/fstab); Apple HFS accepts a dirty non-journaled ROOT read-write on SWEET (logs "mounting dirty non-journaled root read-write"). Later: journaled HFS for crash safety. Kernel `xnu/out-0031` (CI `38852837176` success, 5m31s; 0030 run cancelled by the newer push). Boot images (phone ADT `sweet-0028.adt`, ramdisk byte-matched): `shim/out/shim-boot-0031r.img` = 0029k args (read-only, ignition_level=1) and `shim/out/shim-boot-0031w.img` = same + `ufsrw=1 rootrw=1`. PLAN: boot 0031r first and film until the reset (diagnose overnight reset), then 0031w (first ever writes to userdata; v2 image on the SSD is the restore source). `research/check-patch-order.py` cannot check 0031 (staged sweet_hfs files are not in its index); CI stage scripts run first, so CI is the check.

- **ignition_level=1 result** (boot 21:01:39 UTC, `research/boot0029k.log`, photo IMG_20261015_230308): preboot/cryptex stages skipped (need >= 2/3), `dylib_cache: finding shared cache on system volume: ignition level = 1, search root fd = 4, subpath = System/Library/Caches/com.apple.dyld/` -> not found -> `ignition boot failed: 19` -> no shared cache -> libSystem not loaded. FIX IN PROGRESS: image v2 = copy of the flashed image + `/System/Library/Caches/com.apple.dyld/` with HARD LINKS to the 44 cryptex cache files (no extra space; avoids symlink-following doubts), then `tools/sparsediff.py ios16-root-20H392.img ios16-root-20H392-v2.img diff.simg` and flash only the diff. Boot with `ignition_level=1` (shim-boot-0029k.img).
- **ignition_level=0 result** (boot 20:58:07 UTC, `research/boot0029j.log`, photo IMG_20261015_230037): all stages skipped as "ignition level insufficient" (hello/preboot/cryptex1 sniff >= 2, select os cryptex path/graft >= 3, **dyld_cache >= 1**), `ignition boot failed: 89`, "ignition partially disabled", then same `Library not loaded: /usr/lib/libSystem.B.dylib (no such file, no dyld cache)`. => dyld gets the shared cache directory from ignition's dyld_cache stage. Next: `ignition_level=1` (`shim/out/shim-boot-0029k.img`) to skip preboot/cryptex stages but run dyld_cache; its log "finding shared cache on %s ... subpath = %s" will show where it searches. If it searches rootfs /System/Library/Caches/com.apple.dyld, add a symlink there (image rebuild; consider a diff-only sparse flash tool to avoid rewriting 12 GB).
- **APPLE dyld/launchd RUNNING (libignition) with `unentitled_ios_sim_launch=1`** (boot 20:53:24 UTC, `research/boot0029i.log`, photo IMG_20261015_225617): kernel prints "Allowing spawn of iOS binary ... boot-arg set to true"; `shared_region: ... check_np ... vm_shared_region_start_address() failed` (no region yet, normal); dyld's built-in **libignition** (Darwin Ignition Sequence 1.0.0, libignition-51~1974; prints rd=ufsroot0, hardware target sweet, ignition level 0x5, platform 0x2, boot spec local, 7 stages): `hello from launchd.1` -> `preboot: mounting preboot` -> `failed to lookup preboot: 25` (ENOTTY: looks for a separate Preboot volume by role) -> ignition fails -> dyld `Library not loaded: /usr/lib/libSystem.B.dylib ... (no such file, no dyld cache)` -> launchd exit -> panic initproc failed. dyld boot-args found via strings: `ignition_level`, `ignition_force_dylib_root` (forced rootfs/livefs/cryptex fallback), `ignition_halt_after`, `ignition_live_app_graft`; dyld cache search paths include /System/Cryptexes/OS, /System/Volumes/Preboot/Cryptexes/OS/, /private/preboot/Cryptexes/OS/ (present in our image). Next try `ignition_level=0` (`shim/out/shim-boot-0029j.img`).
- **APPLE launchd EXECUTED FROM UFS (2026-10-15).** Flashed iOS image: `img2simg` -> `ios16-root-20H392.simg` (12.1 GB) then `fastboot -S 512M flash userdata ...simg` (24 chunks, 307 s, `research/flash-userdata-ios16.log`; a raw-image flash was killed by earlyoom at 2.6 GB RSS - always flash the sparse image). ABL fastboot hung on getvar after the flash; power+vol-down fixed it. Boot 0029u 20:49:04 UTC (`research/boot0029u-ios16.log`), photo IMG_20261015_225134: `hfs: mounted iOSRoot` -> load_init_program /sbin/launchd -> panic `unexpected SIGKILL of launchd (CS_KILLED) with reason -- namespace 9 code 0xe` = OS_REASON_EXEC / EXEC_EXIT_REASON_WRONG_PLATFORM: our kernel is XNU_TARGET_OS_OSX, iOS-platform binaries are "alien" and refused unless spawn attr platform set or DEVELOPMENT TUNABLE `unentitled_ios_sim_launch`. Next try: same kernel, cmdline + `unentitled_ios_sim_launch=1` (`shim/out/shim-boot-0029i.img`). LONGER TERM: macOS-config kernel marks iOS maps alien (vm_map_mark_alien) and differs from iOS in many policies; an iPhoneOS-config kernel build may eventually be needed.
- **iOS 16 ROOT IMAGE BUILT:** `/run/media/dipa/android/ios-sweet-ipsw/ios16-root-20H392.img` (16 GiB case-sensitive HFS+, label iOSRoot, 12 GB used, fsck OK after `fsck.hfsplus -y` rewrote 32 non-ASCII localized WorkflowKit Shortcut names Linux decomposes differently). Built by `tools/mkiosroot.sh OS.dmg SYSTEMOS.dmg APPOS.dmg OUT.img [SIZE]` (needs sudo; apfs-fuse as root; OS dmg is UDIF -> link must end .dmg). Contents: iPhone X 20H392 OS root + SystemOS cryptex at /private/preboot/Cryptexes/OS (so /System/Cryptexes/OS -> cache, 44 files, dyld_v1 arm64) + AppOS at .../App. /sbin/launchd and /usr/lib/dyld root:wheel 0755. NEXT: (confirm) `fastboot flash userdata ios16-root-20H392.img` (auto-sparse), boot 0029u (rd=ufsroot0) -> Apple launchd attempt.
- **MILESTONE ON HARDWARE: BOOT FROM INTERNAL FLASH.** 0029 CI `38797924912` PASSED, `xnu/out-0029` SHA256 `a68bc847...2a37`. Image `shim/out/shim-boot-0029u.img` (payload-0029u = 0029 kernel + `shim/out/sweet-0028.adt` + `rd=ufsroot0`, NO RAM disk). Boots 20:01:34 and 20:12:37 UTC (`research/boot0029u*.log`), photo IMG_20261015_221403: `SWEET UFS: "userdata" on LUN 0: first block 0x2b8c00, 109643 MiB, read-only` -> `BSD root: ufsroot0, major 1, minor 0` -> `hfs: mounted SweetRoot on device b(1, 0)` -> `SWEET: root volume is not authenticated (error 25); continuing unsealed` -> `load_init_program ... /sbin/launchd` -> `*** SWEET userspace: init running as PID 1 ***` -> heartbeat (ran for minutes unattended). userdata currently holds the 8 MB `research/root-hfs.img`. NEXT: build a multi-GB HFS+ image with the iOS 16 (iPhone X 20H392) userland (OS rootfs + SystemOS cryptex contents incl. dyld shared cache at /System/Library/Caches/com.apple.dyld; preserve modes/owners/symlinks; decompress LZBITMAP via apfs-fuse), flash it to userdata (sparse, needs user OK), then try Apple's dyld/launchd. Driver is read-only (root mounts RDONLY), fine for first launchd attempts.
- **userdata FLASHED with the 8 MB HFS test volume** (user said "flash it", 2026-10-15 19:53:17 UTC, `research/flash-userdata-hfs-test.log`: `fastboot flash userdata research/root-hfs.img` OKAY; pre-checks: one sweet device, partition-size:userdata 0x1AC4BFB000, partition-type f2fs, image fsck OK, SHA256 3626ea69...). Android userdata is now destroyed (expected/approved). Boot 0028u at 19:53:20 (`research/boot0028u-hfs.log`), photo IMG_20261015_215541: `BSD root: ufsroot0` -> **`hfs: mounted SweetRoot on device b(1, 0)` from internal UFS** -> panic `rootvp not authenticated after mounting @bsd_init.c:931` (arm64 macOS-config requires FSIOC_KERNEL_ROOTAUTH sealed root for non-ramdisk roots). Patch **0029** (`dd1c284`): SWEET logs `SWEET: root volume is not authenticated (error N); continuing unsealed` instead of panicking (Apple configs keep the panic; pivot_root still requires auth). CI **`38797924912`** running. Next: download out-0029, phone image with sweet-0028.adt + rd=ufsroot0 (no RAM disk), boot -> expect init from UFS.
- **UFS ROOT DRIVER VERIFIED ON HARDWARE (read-only).** 0028 CI `38796139570` PASSED, `xnu/out-0028` SHA256 `8b981640...9da6`; QEMU HFS RAM-disk regression `research/q0028-hfs` still runs init. Phone boot 2026-10-15 19:50:24 UTC (`research/boot0028u.log`, image `shim/out/shim-boot-0028u.img`, phone ADT `shim/out/sweet-0028.adt` with /sweet-ufs, NO RAM disk, `rd=ufsroot0`), photos IMG_20261015_215151/215220: `SWEET UFS: "userdata" on LUN 0: first block 0x2b8c00, 109643 MiB, read-only` -> `BSD root: ufsroot0, major 1, minor 0` -> `hfs_ValidateHFSPlusVolumeHeader: unknown Volume Signature : f188` (Android-encrypted data, as expected) -> `cannot mount root, errno = 19`, kernel retries mountroot (no panic). Nothing written to flash. NEXT (destructive, needs user confirmation right before): `fastboot flash userdata research/root-hfs.img` (8 MB HFS with test init) then boot rd=ufsroot0 -> expect init from internal flash.
- **PATCH 0028 (`33aceac`): XNU read-only UFS root device**, CI **`38796139570`** running (next artifacts xnu/out-0028, research/bt29, run29.log). `bsd/dev/sweet_ufs.c`: reuses ABL's UFSHCI state (like the shim probe), takes over UTRL at a kmem_alloc_contig region (DMA layout: UTRL 0x0, UCD 0x1000, 1 MiB bounce 0x4000), verifies UTRLBA readback before any doorbell, IE=0 polled, one SCSI cmd at a time on LUN0 (TUR x3, READ(10) via bounce, PRDT 256 KiB chunks), flush_dcache64 by PA around each command (host not dma-coherent per DT), finds GPT partition by name (`ufsroot=` boot-arg, default `userdata`), exposes `/dev/ufsroot0`/`rufsroot0` (512-byte logical sectors, physical 4 KiB, DKIOC* ioctls), refuses writes (EROFS). IOKitBSDInit: `rd=ufsroot0` -> sweet_ufs_rootdev() (lazy init) else panic. ADT: `tools/mkadt.py` adds `/sweet-ufs` reg <0x1d84000 0x3000> for the PHONE only (not --qemu). Local compile OK, imports resolve. Sandbox research/bt28 (pre0028 originals). FIRST PHONE TEST PLAN (non-destructive): boot 0028 with phone ADT + `rd=ufsroot0` and NO RAM disk: expect `SWEET UFS: "userdata" on LUN 0: first block 0x2b8c00, 109643 MiB` + `BSD root: ufsroot0`, then root mount failure (userdata is still Android-encrypted) -> panic. That validates the driver before flashing an HFS image into userdata (needs explicit user confirmation at that time).
- **SUPERSEDES the 64 GiB iosroot GPT plan: user said "u can delete android" (2026-10-15).** Use the existing `userdata` partition (LUN0 sda34, 4K LBA 0x2B8C00, 0x1AC4B MiB ~107 GiB) directly as the iOS root: NO GPT changes. Keep bootloaders, recovery (OrangeFox), modem/persist/fsg/modemst untouched. Write the HFS image later with `fastboot flash userdata` (sparse, auto-split under the 768 MiB limit). Android will no longer boot normally (expected; reinstallable). Order: XNU UFS driver first, read-only against the current GPT; flash only once it can locate userdata. Nothing erased yet.
- **DECIDED (user, 2026-10-15): 64 GiB `iosroot` on LUN0 (sda), taken from userdata (wipes Android user data; Android/super kept).** Planned GPT (4K LBAs): userdata 0x2B8C00..0xD7D6FF (~43 GiB, keep type/unique GUIDs and attributes); iosroot 0xD7D700..0x1D7D6FF (0x1000000 blocks = 64 GiB, 1 MiB aligned); backup GPT area unchanged. Procedure: user backs up phone data -> boot OrangeFox recovery (adb) -> back up GPT (sgdisk --backup + raw dd of LBA 0-5 and last 6 blocks) to research/ -> sgdisk edit -> Format Data -> verify Android boots to setup. NOT EXECUTED YET.
- **INTERNAL UFS WORKS FROM THE SHIM (read-only), user authorized internal-UFS approach incl. flashing (2026-10-15, "i allow everything").** Shim probe `shim/ufs.c` (commit `12ed3ed` + filter): ufshc@1d84000 is UFSHCI 2.1 (ver 0x210, cap 0x1587031F, 32 slots), ABL leaves HCE=1, HCS=0x10F (device present, lists ready, UIC ready); probe takes over UTRL at its own buffer (verifies UTRLBA readback before any doorbell), TEST UNIT READY/READ CAPACITY/READ(10) all succeed. LUN0 = 0x1D7D800 x 4 KiB (~126.6 GB), valid GPT (64 entries at LBA 2). Photos IMG_20261015_212916/213325/213429. Big LUN0 partitions (start in 4K LBAs / MiB): super 0xCA00/0x2200 (8.5 GiB), logdump 0x22CA00/64, minidump 0x230A00/128, rawdump 0x238A00/128, recovery 0x240C00/128, cache 0x248C00/384 ext4, exaid 0x260C00/384, cust 0x278C00/1024 ext4, **userdata 0x2B8C00/0x1AC4B MiB (~107 GiB), fs unreadable = encrypted (metadata encryption)**. cache..cust contiguous = only 1.75 GiB (too small for iOS ~10+ GiB). Plan needing user consent: shrink userdata in GPT (wipes Android data) and add an `iosroot` partition at the end of LUN0. LUNs 1-5 not listed yet (sdb..sdf backed up in backup/lun).
- **fastboot limit measured (2026-10-15, read-only getvar):** `max-download-size: 805306368` (768 MiB); `max-fetch-size` unsupported; `is-userspace: no` (ABL fastboot). A `fastboot boot` image (shim+kernel+RAM disk) must be < 768 MiB, so the 2.5 GiB iOS shared cache cannot ride in the boot RAM disk even if XNU gets all RAM. Real userland needs storage access (UFS driver, or USB host) or a much smaller cache. Unlocking full RAM is still needed later (GUI).
- **iOS 16 USERLAND SOURCE (Claude, 2026-10-15).** Chose **iPhone X (iPhone10,3/10,6, D22/D221AP)** iOS **16.7.16 (20H392)** over iPhone 8: same A11 (no PAC -> plain arm64, runs on Kryo 470/ARMv8.2), last iOS for A11; X userland is home-button-less and tall-screen (1125x2436 vs sweet 1080x2400), better fit for later GUI. Note the X has its OWN SystemOS cryptex (different digest from iPhone 8's). IPSW URL in `research/ipsw-x/URL.txt` (+ BuildManifest). Images on the user's external SSD (NOT in git, do not format that disk: it holds the user's photos): `/run/media/dipa/android/ios-sweet-ipsw/iPhone10,3_16.7.16_20H392/` Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р вЂ™Р’В Р В Р вЂ Р В РІР‚С™Р вЂ™Р’В Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р В РІР‚В Р В Р’В Р Р†Р вЂљРЎв„ўР В Р Р‹Р Р†РІР‚С›РЎС›Р В Р’В Р вЂ™Р’В Р В Р’В Р Р†Р вЂљР’В Р В Р’В Р вЂ™Р’В Р В Р вЂ Р В РІР‚С™Р РЋРІвЂћСћР В Р’В Р В Р вЂ№Р В Р Р‹Р РЋРІвЂћСћ `087-86593-047.dmg` = Cryptex1,SystemOS (2,743,074,816 B), `087-86698-044.dmg` = OS rootfs (4,730,814,044 B), both zip CRC-32 verified, plus Firmware/*.root_hash/.trustcache/.mtree. AppOS cryptex is 087-86715-047.dmg (10 MB, same as iPhone 8).
  - Images are raw APFS; files use LZBITMAP (decmpfs type 14). 7z cannot decode. Tools: `ipsw` 3.1.738 (AUR ipsw-bin, user-approved) needs apfs-fuse on Linux; **apfs-fuse** built in user space (system cmake broken: cmake 4.4.4 wants libjsoncpp.so.27, jsoncpp 1.9.6 installed = partial upgrade, NOT fixed) with pip cmake + `-DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DCMAKE_CXX_FLAGS="-include cstdint"`, installed to `~/.local/bin/apfs-fuse` (+apfs-dump-quick). Mount via a comma-free symlink (apfs-fuse splits options on ',' in `iPhone10,3`; exFAT has no symlinks -> put link elsewhere): `apfs-fuse LINK/087-86698-044.dmg MNT` -> `MNT/root/...`; unmount `fusermount3 -u MNT`.
  - Verified from headers: `dyld_shared_cache_arm64` magic `dyld_v1   arm64`; `/sbin/launchd`, `/usr/lib/dyld` = cputype 0x100000c subtype 0 (plain arm64). libSystem exists only inside the cache.
  - **BLOCKER for real userland via RAM disk:** shared cache = 3.10 GiB in 44 files (~2.5 GiB without the 592 MB `.symbols`), but the kernel manages only 1.20 GiB (0xb0000000..0xfd000000). Options: (A) give XNU the phone's full ~6 GB (banks 0x80000000+2G and 0x100000000+0xfcc00000, carve-out holes need pmap support) AND check fastboot max-download-size for a multi-GB boot image; (B) storage driver (Qualcomm UFS) to read a root from flash (no flashing allowed: would need a file/partition strategy); (C) run against individual dylibs extracted from the cache (uncertain).
- **MILESTONE ON HARDWARE: HFS+ ROOT FILESYSTEM -> PID 1.** Boot 2026-10-15 18:22:12 UTC (`research/boot0027b.log`, image `shim/out/shim-boot-0027b.img`), photo `IMG_20261015_202334.jpg`: `BSD root: md0` -> `hfs: mounted SweetRoot on device b(1, 0)` -> `load_init_program: attempting to load /sbin/launchd` -> `*** SWEET userspace: init running as PID 1 ***` -> repeated `SWEET init: still alive`, no panic. Kernel 0027 (built-in Apple OSS HFS + BearSSL MD5), init with SP alignment fix. NEXT: real iOS 16 userland on the HFS image (dyld, libSystem/dyld shared cache, launchd). Known gaps: entitlements (none granted), SHA-1/SHA-384/512 providers, no storage driver (RAM disk only), root mounted read-only.
- **PHONE HFS ROOT (0027) + SIGBUS ROOT-CAUSED.** Phone boot 2026-10-15 17:49:06 UTC (`research/boot0027.log`, photo `IMG_20261015_200031.jpg`): `hfs: mounted SweetRoot on device b(1, 0)` (HFS works on hardware), init printed its first line, then `pid 1 exited -- exit reason namespace 2 subcode 0xa` = SIGNAL/SIGBUS -> `initproc failed to start` panic. Diagnostic boot 18:08:13 UTC (`research/boot0027d.log`, image `shim/out/shim-boot-0027d.img`, diag init `research/diag-init` from scratch diag-init.S with [a][b][c] markers, `cs_debug=1`; photo `IMG_20261015_201547.jpg`): output `PID [a][b]` then SIGBUS -> fault at first `strb w21,[sp]`; no code-signing messages. Cause: kernel enters a static binary with sp at argc, not necessarily 16-aligned (depends on arg/apple string lengths, differs mockfs vs HFS); EL0 SP alignment check -> EXC_ARM_SP_ALIGN -> SIGBUS (sleh handle_sp_align). QEMU does not enforce SP alignment. NOT a kernel bug: real binaries start in dyld which aligns. Fix `1a8fc15`: sweet-init aligns sp at entry. Rebuilt `research/root-hfs.img`, QEMU `research/q0027-hfs2` OK. Phone image `shim/out/shim-boot-0027b.img` SHA256 `098ba46c...c5c` (payload-0027b, ramdisk match check-0027b) ready, awaiting FASTBOOT. Lesson: Assembly `;` is a comment in Apple arm64 asm (use .macro, not ;-joined #define).
- **HFS ROOT WORKS (QEMU).** 0027 CI `38779441895` PASSED, `xnu/out-0027` SHA256 `a8643886...5f6a`. QEMU `research/q0027-hfs` (RAM disk = `research/root-hfs.img`, rd=md0): `BSD root: md0` -> `hfs: mounted SweetRoot on device b(1, 0)` -> `load_init_program: attempting to load /sbin/launchd` -> `*** SWEET userspace: init running as PID 1 ***` + heartbeat, no panic. Phone image `shim/out/shim-boot-0027.img` (payload-0027 = 0027 kernel + sweet-0021.adt + root-hfs.img + rd=md0, ramdisk byte-match check-0027) ready; awaiting FASTBOOT for phone test.
- **HFS ROOT WORK (Claude), patches 0026-0027.**
  - 0026 (`f0e990c` + link fix `64c96f4`): Apple OSS **hfs-627.100.6** (commit `31d5ec238dfab485e78a9a30b8b92d13e8914f03`, paired with xnu-8796.141.3 in macos-135 release.json) staged by `xnu/patches/0026-stage-hfs.sh` into `bsd/sweet_hfs` (core + hfs_encodings; AppleKeyStore include/key prototypes guarded by CONFIG_PROTECT; SDK TargetConditionals copied). New config option `sweet_hfs` (MASTER + MASTER.arm64.sweet); 40 `optional sweet_hfs` files; Makefile.template foreach adds `_CFLAGS_ADD = -include sweet_hfs_compat.h -I...` (MUST come after kernel -D flags; compat undefs BSD/XNU_KERNEL_PRIVATE and the CONFIG_* HFS tests so kext-config.h decides: macOS profile, no content protection). `sweet_hfs_iokit.c` replaces hfs_iokit.cpp/hfs_encodings_kext.cpp: `sweet_hfs_register()` called in bsd_init after vfsinit (encodings init, vfs_fsadd VFS_TBLCANMOUNTROOT, zones, sysctls); is_ejectable 0, iterate_media none, serial KERN_NOT_SUPPORTED, OSKextGetCurrentLoadTag -> kOSKextInvalidLoadTag (renamed via compat macro). hfs_encodings' own `hfs_allocated` renamed per object (separate kexts on Apple; first CI `38777325964` failed on that duplicate at link). mockfs now validates Mach-O magic (its TODO) so non-Mach-O roots fall through to HFS (new fs entries come AFTER mockfs in vfsconf). CI `38778133720` PASSED, `xnu/out-0026` SHA256 `0b49170c...701a`, prints `SWEET HFS: hfs-627.100.6 registered`.
  - HFS+ image: `research/root-hfs.img` (8 MB, mkfs.hfsplus from AUR hfsprogs installed with user approval; loop-mounted with sudo; /sbin/launchd = research/sweet-init, /dev; fsck.hfsplus OK). QEMU `research/q0026-hfs`: `BSD root: md0` then data abort in MD5Init from hfs_getvoluuid (mount computes volume UUID).
  - 0027 (`14bf2b7`): 0020 stager also copies BearSSL hash/md5.c + codec/dec32le.c/enc32le.c; `corecrypto_md5.c` SWEET branch converts MD5_CTX <-> br_md5_context around br_md5_* calls; wrappers sweet_md5.c/sweet_dec32le.c/sweet_enc32le.c. Host test 40/40 match md5sum. CI **`38779441895`** running.
  - Local tooling: `tools/xnu-cc.py` has `XNU_CC_POST` (flags after logged ones). Sandbox `research/bt28/xnu` = 0025 CI tree + 0026/0027 edits; originals `research/pre0026`, `research/pre0027`. HFS local objects `research/hfs-objs`. Checker entries updated to bt28.
  - SHA-1 / SHA-384/512 still have no provider.
- **MILESTONE ON HARDWARE: USERSPACE PID 1 RUNS ON THE PHONE.** Boot 2026-10-15 17:16:00 UTC (`research/boot0025.log`: send OKAY0.410s, boot OKAY0.135s), image `shim/out/shim-boot-0025.img` SHA256 `9dbfa0b1...89db0`. Photo `IMG_20261015_191733.jpg`: `BSD root: md0` -> `load_init_program: attempting to load /sbin/launchd` -> `*** SWEET userspace: init running as PID 1 ***` -> repeated `SWEET init: still alive` (5 s heartbeat), no panic. Kernel 0025 + mockfs RAM disk + built-in no-entitlements AMFI. No flashing performed.
- **NEXT (toward real iOS userland):** real root filesystem with real binaries. Options: (a) build Apple OSS `hfs` (macOS 13.5 tag `hfs-627.100.6`) into SWEET like libpthread, then an HFS RAM disk image; (b) iOS 16 dyld + libSystem/dyld shared cache from the IPSW (needs APFS or repacking onto HFS). Expected hurdles: entitlements (sweet_amfi grants none), SHA-1/MD5/SHA-384/512 providers (BearSSL), missing kexts/daemons. Current init is a static test program, not launchd.
- **MILESTONE: USERSPACE RUNS (QEMU).** 0025 CI `38774788048` PASSED, `xnu/out-0025` SHA256 `5496069b...4877`. QEMU `research/q0025-rd` (150 s, no panic): `BSD root: md0` -> `load_init_program: attempting to load /sbin/launchd` -> `*** SWEET userspace: init running as PID 1 ***` -> `SWEET init: still alive` every 5 s. Exec, ad-hoc SHA-256 code signature, syscalls, devfs /dev/console, select timeouts all work. Phone image prepared: `shim/out/shim-boot-0025.img` 16,515,072 bytes SHA256 `9dbfa0b15140c0bd733a16c4f727f6a7df44a8741f98d8e266d5f2fa4f689db0` (payload-0025 = 0025 kernel + sweet-0021.adt + research/sweet-init + rd=md0; ramdisk byte-match check-0025). Waiting for user to put phone in FASTBOOT.
- **0024 CI `38773277811` PASSED**, `xnu/out-0024` SHA256 `a0ba964b...4348`. QEMU `research/q0024-rd` and **PHONE (boot 2026-10-15 17:05:55 UTC, `research/boot0024.log`, image `shim/out/shim-boot-0024.img` SHA256 `cf3dac86...6964`, 16,510,976 bytes, payload `shim/out/payload-0024.bin` = 0024 kernel + `shim/out/sweet-0021.adt` + RAM disk `research/sweet-init` + rd=md0; ramdisk byte-match `check-0024`)** agree: `Added memory device md0`, `BSD root: md0`, `load_init_program: attempting to load /sbin/launchd`, then data abort in accelerate_entitlement_queries (PC 0x...77d2458, FAR 0x1a0) = NULL AMFI interface. Photo `IMG_20261015_190715.jpg`. RAM disk root is physically verified.
- **0025 (`2518c79`)**: new `bsd/kern/sweet_amfi.c` registers a built-in AMFI interface at EARLY_BOOT/MIDDLE: no entitlements (adjustContextWithoutMonitor succeeds without creating a context, queries KERN_DENIED, copies NULL/KERN_NOT_FOUND, get_xml/transmuted false); WithMonitor KERN_NOT_SUPPORTED; OSEntitlements_query and query_context_to_object panic explicitly (CoreEntitlements closed; no kernel caller); TrustCache version 0 (0015 keys on trust_cache_rt==NULL, img4 absent -> still unavailable); CoreEntitlements table zero (PMAP_CS only). Compiles locally; checker updated (bt27 entries). CI **`38774788048`** running. Next artifacts `xnu/out-0025`, `research/bt29`, `research/run29.log`. Real iOS binaries will need real entitlements later (no OSS CoreEntitlements exists).
- **0021-0024 RAM-disk-root iteration (Claude), QEMU only so far, no new phone boot since 0020.** Each kernel tested with `tools/mkpayload.py KERNEL research/q0021.adt OUT --ramdisk research/sweet-init --cmdline "debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam -noprogress rd=md0"` then `tools/qemu-sweet.py OUT DIR --secs 150 --kernel KERNEL --fail-on-panic` (PATH needs ~/swift/usr/bin for llvm-nm). Fresh ADTs: `research/q0021.adt` (QEMU), `shim/out/sweet-0021.adt` (phone).
  - 0021 CI `38769532000` PASSED, `xnu/out-0021` SHA256 `2b7500a1...962e`, `research/bt25`/`run25.log`. QEMU `research/q0021-rd`: md0 root, then assert `iomediaClass` in IOService::publishHiddenMedia.
  - 0022 (`20ece9c`, publishHiddenMedia without IOMedia class) CI `38770666158` PASSED, `xnu/out-0022` SHA256 `a4d0e787...30c5`, `research/bt26`/`run26.log`. QEMU `research/q0022-rd`: data abort in SHA256_Init (NULL g_crypto_funcs) from vm_kernel_addrhash_internal.
  - 0023 (`c8089d1`, libkern SHA256_Init/Update/Final use built-in ccsha256_ltc_di + ccdigest_init/update on SWEET; also serves code-signing SHA-256; SHA-1/MD5/SHA-384/512 still have NO provider - BearSSL from 0020 could supply them later) CI `38771876423` PASSED, `xnu/out-0023` SHA256 `d763fed7...1003`, `research/bt27`/`run27.log`. QEMU `research/q0023-rd`: **mockfs mounted md0, `load_init_program: attempting to load /sbin/launchd`**, then panic `mockfs_fsnode_vnode failed to create fictitious pages ... rvalue = 5` (mockfs.c:351).
  - 0024 (`3293c80`): mockfs used memdev mi_base (4K page number of a VIRTUAL kernel address for IOKit RAMDisk, truncated to 32 bits) << PAGE_SHIFT as a physical address. Now zero-copy pager mapping only when mi_phys (with 4K units); virtual md uses pagein/blockmap/strategy -> memdev bcopy. memdev's own mdPhys path assumes 4K ppnums (unsafe on 16K arm64), so do NOT switch the RAMDisk to physical. CI **`38773277811`** running. Next artifacts `xnu/out-0024`, `research/bt28`, `research/run28.log`.
  - Sandboxes: bt25/bt26/bt27 contain the next patch's edited files; pristine copies in `research/pre0022`..`pre0024`.
- **PATCH 0021 (Claude): RAM disk root via mockfs -> first userspace program.** Commits `9c37771` (initial; CI `38768500280` FAILED: mockfs_fsnode.c kfree_type(mockfs_fsnode_t) typed-alloc static assert; local xnu-cc stubs `__builtin_xnu_types_compatible` so it can't catch this) and `193772f` (fix), CI **`38769532000`** running: https://github.com/dipa-studio/ios-sweet/actions/runs/38769532000. Next artifacts: `xnu/out-0021`, `research/bt25`, `research/run25.log`.
  - Kernel: `config/MASTER.arm64.sweet` FILESYS_BASE += `mockfs` (XNU's built-in FS: root device is itself a Mach-O, served as /sbin/launchd, plus /dev for devfs). Upstream mockfs bit-rot fixed: kalloc_type/kfree_type used the POINTER typedef mockfs_fsnode_t (nodes were 8 bytes) -> `struct mockfs_fsnode`. `IOService::setRootMedia` asserted IOBlockStorageDriver class exists (IOStorageFamily absent): SWEET-only, a missing class means root=NULL (same as IOSetImageBoot); Apple path keeps assert. All 21 patches apply (`research/check-patch-order.py`); 5 TUs compile locally with -DMOCKFS (`research/mockfs-objs`), imports resolve vs 0020 kernel. Sandbox `research/bt24/xnu` now holds 0021 versions of those 3 files; pristine 0020 copies in `research/pre0021`.
  - Tools: `tools/mkpayload.py --ramdisk IMAGE` appends IMAGE as an extra payload segment right after the kernel, moves kernel_end past it (shim unchanged: ADT+boot_args follow it, image stays below topOfKernelData), and adds ADT `/chosen/memory-map` `RAMDisk`=<phys,size>. Boot with `rd=md0`. Without --ramdisk output is byte-identical to existing 0020 QEMU and phone payloads (verified). `tools/sweet-init.S` + `tools/mkinit.py`: PIC static init (open /dev/console, print PID, heartbeat every 5 s via select, never exits) wrapped into a static arm64 Mach-O (__PAGEZERO, __TEXT@0x100000000, LC_UNIXTHREAD, ad-hoc SHA-256 CodeDirectory v0x20400, 4K pages). Build: `~/swift/usr/bin/clang -target arm64-apple-ios16.0 -c tools/sweet-init.S -o X.o && tools/mkinit.py X.o research/sweet-init` (ld64.lld cannot link static iOS). Signature not verified by a real codesign; the kernel will tell.
  - QEMU with 0020 kernel + RAM disk (`research/q0020-rd.bin`, rd=md0, 150 s `research/q0020-rd150`): `Added memory device md0`, **`BSD root: md0, major 1, minor 0`** (plumbing works), then the setRootMedia assert (now fixed in 0021). NOTE: QEMU needs >60 s to reach IOFindBSDRoot (60 s run showed nothing after stf0; likely RTC/inittodr wait), so use --secs 150.
  - NEXT: download 0021, QEMU 150 s with ramdisk; expect mockfs mount then init exec -> `*** SWEET userspace: init running as PID 1 ***`. Then phone boot with same payload (phone ADT shim/out/sweet-0020.adt pattern + --ramdisk + rd=md0).
- **0020 PHONE RESULT (user transcription of screen, 2026-10-15): KERNEL INIT COMPLETE, WAITING FOR ROOT.** After Skywalk self-tests PASSED, kminit, ifnet_attach lo0/gif0/stf0, screen prints `BSD`, then `Waiting on <dict><key>IOProviderClass</key><string>IOMedia</string><key>Content</key><string>Apple_HFS</string></dict>` and `Failed to write boot-picker-bringup-reason to NVRAM.` No panic. This is IOFindBSDRoot waiting for a root device (none exists); NVRAM warning is expected (no NVRAM driver). QEMU `cpu_idle` snapshot is presumably the same wait (not GDB-confirmed; milestone GDB run was cancelled by user since phone answered it). Draft `research/check-milestones20.gdb` (hbreaks inittodr/vfs_mountroot/IOFindBSDRoot/bsd_utaskbootstrap) left uncommitted/ignored.
- **NEXT MILESTONE: root filesystem -> launchd.** Plan: (1) RAM disk: shim places an image in RAM, ADT /chosen/memory-map `RAMDisk` entry, boot-arg `rd=md0` (XNU md driver). (2) HFS is a separate kext on Apple; build Apple OSS `hfs` (tag paired with macOS 13.5 in distribution-macOS macos-135 release.json) into SWEET like libpthread 0019. APFS is closed. (3) Minimal HFS image with iOS 16 launchd (later: dyld/shared cache; AMFI/code-signing absent will be a later hurdle). User's end goal is full iOS GUI.
- **0020 (AES) VERIFIED + PHONE BOOTED (Claude took over after Codex usage limit).** Actions `38765422261` (`ab9e23f`) PASSED; kernel `xnu/out-0020/kernel.development.sweet` checksum OK; buildtree `research/bt24`, log `research/run24.log`. Actual-kernel AES checks PASS (`research/check-aes20.gdb` / `.log`, 12 extra CBC cases match OpenSSL). 45s QEMU `research/q0020`: no panic, zero unknown glyphs, past old TCP/AES panic -> Skywalk self-tests PASSED -> bsd_autoconf kminit -> ifnet_attach lo0/gif0/stf0; final snapshot PC in `cpu_idle` (idle or waiting; NOT yet diagnosed, could be root-device wait). Image `shim/out/shim-boot-0020.img` 16,461,824 bytes SHA256 `775200cb02d95fc750981516b79d91dcdc96184bbe67a38f9d57c59b4a391828`, ramdisk byte-matches `payload-0020.bin` (`check-0020`). **Phone temporarily booted 2026-10-15 16:10:00 UTC**: one FASTBOOT product sweet, send OKAY0.407s, boot OKAY0.134s, total0.549s, exit0 (`research/boot0020.log`). Awaiting user photo; do not reboot the phone before it. NEXT: read photo; diagnose what QEMU waits on after stf0 (GDB backtrace of threads / longer run). Codex's STOP request below is complete.
- User requests STOP after completing the current0020 AES iteration (Actions/QEMU/phone), then leave a precise committed handoff for another AI. User says FASTBOOT ready again after0019 photo. Do not start a new blocker fix after this iteration.
- Goal: iOS16-generation XNU on Redmi Note10Pro sweet/SM7150. Always commit, use gh/Actions for kernel builds, keep this handoff current. Temporary fastboot boot only; preserve Android/backups. No userland/root filesystem boot yet.
- **Patch0020 update:** initial `e71098d` / Actions `38765012466` superseded by scalar-only compile flags. Added -mgeneral-regs-only to all six provider/BearSSL TUs and corecrypto_aes.c; object disassembly now confirms no SIMD. Updated implementation `ab9e23f`, Actions `38765422261` queued/running: https://github.com/dipa-studio/ios-sweet/actions/runs/38765422261. Do not launch another run. portable BearSSL AES CBC and legacy one-block ECB wired directly into SWEET corecrypto_aes.c. Genuine bitslice implementation, no CPU AES/SIMD requirement, heap or fake global crypto table. Source fetched by `0020-stage-bearssl.sh` from official BearSSL git at immutable `7bea48e5e850ab4cafbe68d3765cdaba13a86d6f`; MIT license retained, downloaded source stays out of git. Kernel limits include adapter only. All128/192/256-bit keys, CBC encrypt/decrypt, copied contexts, in-place/out-of-place; zero block count and size overflow handled, invalid keys clear context. Seven TUs compile to arm64 objects (`research/aes-objs`), imports resolve, all20 patches apply and sources match (`research/patch0020-check.log`). Sandbox `research/bt23/xnu`, originals `research/pre0020`. NEXT: Actions then actual-kernel NIST/random CBC/ECB checks and >=45s QEMU before another phone boot. Next artifacts out-0020 / bt24 / run24.log. 0020 updated CI pending. Local sources/checks match the scalar-only patch.
- **Latest built kernel0019**, implementation `256d3f0`, patches0001-0019. Actions `38763072907` PASSED (4m5s): https://github.com/dipa-studio/ios-sweet/actions/runs/38763072907. Kernel `xnu/out-0019/kernel.development.sweet`, SHA256 `a27df7568f03fb541cf0e8024c0a594fa178a85054fcf9eba29158cbd4c5ecc0`; checksum verified. Log/source `research/run23.log` / `research/bt23` (no nested .git). Seven pthread source/build/header files and staged adaptations byte-match local compile inputs.
- **0019 hardware photo received** `IMG_20261015_175306.jpg`: pthread registration visible, passes mbinit and DLIL checksum/scheduling, same AES fault as QEMU: PC`0xfffffe00079174e0` (`aes_encrypt_key128`), LR`0xfffffe000767c3a4` (`tcp_init`), FAR0x78, x8=0. Disassembly proves NULL g_crypto_funcs->ccaes_cbc_encrypt. Photo processed; no more0019 observation pending. General crypto table remains absent, other hash/mode operations may still fault after0020. DO NOT bypass TCP or install fake crypto. XNU already contains SHA256/HMAC implementations; AES source there is a dispatch wrapper. Full future provider interface libkern/libkern/crypto/register_crypto.h. Apple/corecrypto default README describes evaluation-only licensing, so no external corecrypto was fetched or staged; BearSSL selected for this portable AES integration.
- **0019 pthread FIXED in QEMU and observed beyond its init on phone**: 45s QEMU `research/q0019`, zero unknown glyphs, then AES panic. Actual-kernel API checks PASS `research/check-pthread19.gdb` / `.log`, guest `research/q0019-api`: function/callback table identity, actual provider pthread_init returns, locks/global hash/threadcall/typed zones initialized, thread_selfid via syscall shim + buffer bounds, process hash init/delete via shims restores NULL. Monitor quit prints expected remote-disconnect after PASS. All fixture guests stopped.
- **0019 provider**: genuine Apple libpthread-514.100.2 commit `a6c70ca0e544347a0377babf748f831577ec24f9`, exact paired release with xnu8796.141.3 in distribution-macOS/macos-135/release.json (`research/macos-135-release.json`). 0019 shell stage runs before patches (workflow copies *.sh); three SWEET wrapper TUs use kext BSD header view, vm_fault_external, renamed provider-side pthread_kern/current_uthread; register real function table at EARLY_BOOT SECOND, real pthread_init later. Stager applies bounded address casts, zero user addresses, proper panic format. SWEET opaque ksyn storage enlarged48->56 for trailing kwe_uth, checked with provider static assertion. Local pre-CI TargetConditionals fixture was syntax-only; artifact bt23 carries actual SDK header and CI is authoritative.
- **Phone0019 temporarily booted** 2026-10-15 15:51:36 UTC: exactly one FASTBOOT/product sweet verified; send OKAY0.406s, boot OKAY0.134s, total0.546s, exit0 (`research/boot0019.log`). Image `shim/out/shim-boot-0019.img`, 16,457,728 bytes, SHA256 `19429a57e486b856880df9e27327ed488e0139345311fdb0350974e72103a9a1`. Phone ADT/payload `shim/out/sweet-0019.adt` / `payload-0019.bin` timer19, unpacked ramdisk byte-match (`check-0019`). EntryPA0xb146b488, kernelendPA0xb2000000, boot_argsPA0xb2004000/top0xb2008000. Last user FASTBOOT+USB reply preceded this boot; do not assume phone is still in FASTBOOT.
- **CPU0018 physically verified** by `IMG_20261015_173951 (2).jpg`: boot CPU0 registered, real SGI1 verified, initialization complete -> BSD/MAC/mbinit -> old pthread-table panic. SweetCPU uses legacy IOCPU, ml_processor_register/processor_start/initCPU, real SGI1 clears SIGPdisabled before max CPUs completion; no forced flags/skipped waits. CPU APIs and two-CPU rejection passed (`research/check-cpu18.gdb`, `q0018-api`, `q0018-smp`). Single core; SMP/suspend unsupported. CURRENT SWEET has NO USE_APPLEARMSMP.
- QEMU next run: generate fresh `tools/mkadt.py research/q0020.adt --qemu` (timer27), mkpayload with `debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam -noprogress`, then `tools/qemu-sweet.py PAYLOAD OUT --secs 45 --kernel KERNEL --fail-on-panic`. 12s can miss later panics because IORTC waits30s. Runner snapshot only: panic exit2, blank/incomplete exit3; absence of panic does not mean complete boot. Qualcomm XPU/ABL/panel and phone SMC PSCI require hardware checks.
- Local checker `tools/xnu-cc.py research/run23.log research/bt23 FILTER --per-file`, XNU_CC_OBJDIR for objects. For new BearSSL TUs add XNU_CC_EXTRA with -I bt23/xnu/libkern/crypto/sweet_bearssl/{inc,src}. Patch checker `research/check-patch-order.py` uses temporary upstream index; source fixtures/artifacts ignored under research. GDB mask registers to unsigned64, use function-entry manual-call return traps, discard manipulated guests. No QEMU guest intentionally left running.

## Session log and earlier handoffs (superseded by the active summary above)

### Prior 0019 transition notes (superseded)

- Goal: iOS 16 generation XNU on sweet. Always commit completed work, use gh/Actions for kernel builds, keep this handoff current. Temporary fastboot boot only; preserve Android/backups.
- **0019 build PASSED** Actions `38763072907` (4m5s), implementation `256d3f0`. Kernel `xnu/out-0019/kernel.development.sweet`, SHA256 `a27df7568f03fb541cf0e8024c0a594fa178a85054fcf9eba29158cbd4c5ecc0`; checksum verified. Log/source `research/run23.log` / `research/bt23`; all seven patched files and staged provider adaptations match local compile inputs. Prefer bt23 as the next baseline.
- **0019 pthread FIXED in QEMU**: 45s run `research/q0019` registers provider, passes mbinit, DLIL SUM16 checks and DLIL thread scheduling. Actual-kernel GDB checks `research/check-pthread19.gdb` / `.log` PASS: function/callback table identity, real _pthread_init returns, locks/global hash/cleanup threadcall/typed zones non-NULL, thread_selfid via actual syscall shim with output bounds, process hash init/delete through actual shims restores NULL. Guest stopped after tests; no fixture left running. GDB monitor quit prints expected remote disconnect after PASS.
- **Current next blocker:** QEMU0019 panic data abort FAR0x78 at `aes_encrypt_key128` PC`0xfffffe00079174e0`, called by `tcp_init` LR`0xfffffe000767c3a4`. Disassembly confirms `g_crypto_funcs == NULL`, loading ccaes_cbc_encrypt at+0x78. General crypto registration is still absent; DO NOT bypass TCP or supply fake crypto. Next integrate a genuine compatible crypto implementation/provider (AES first needed here, other digest/mode APIs also used). XNU contains SHA256/HMAC but no AES implementation; its corecrypto_aes.c is a dispatch wrapper. Full crypto table is in libkern/libkern/crypto/register_crypto.h.
- **0019 phone image prepared and verified**, user reports FASTBOOT+USB again; exactly one device/product sweet verified. `shim/out/shim-boot-0019.img`, 16,457,728 bytes, SHA256 `19429a57e486b856880df9e27327ed488e0139345311fdb0350974e72103a9a1`; unpacked ramdisk matches phone payload (`shim/out/check-0019`, `payload-0019.bin`, `sweet-0019.adt`, timer19). EntryPA0xb146b488; kernelendPA0xb2000000; boot_argsPA0xb2004000/top0xb2008000. Usual debug cmdline cpus=1/-noprogress. **Temporarily booted 2026-10-15 15:51:36 UTC**: send OKAY0.406s, boot OKAY0.134s, total0.546s, exit0 (`research/boot0019.log`). User asked for photo after45s. Await the photo; DO NOT reboot again before observation. Bootloader acceptance only; no0019 physical progress observed yet.
- **Hardware photo confirms 0018 progress** (`IMG_20261015_173951 (2).jpg`): real phone prints `SWEET CPU: boot CPU 0 registered, SGI1 verified, initialization complete`, enters BSD/MAC, reaches `mbinit: done`, then the same missing-pthread-function-table panic as QEMU at pthread_shims.c:318. CPU completion/interrupt delivery is now physically observed. The photo was received; no further phone boot performed yet.
- **Patch0019 committed/pushed `256d3f0`; Actions `38763072907` queued/running:** https://github.com/dipa-studio/ios-sweet/actions/runs/38763072907. Do not launch a duplicate. genuine Apple OSS libpthread-514.100.2 provider (immutable commit `a6c70ca0e544347a0377babf748f831577ec24f9`), paired with xnu-8796.141.3 by Apple's `distribution-macOS/macos-135/release.json` (`research/macos-135-release.json`). `0019-stage-libpthread.sh` fetches/stages it before patches; workflow now copies shell scripts too. SWEET-only wrappers compile all three real kernel sources, rename provider-side symbols, use kext header view and vm_fault_external, register the real function table at EARLY_BOOT SECOND. Existing pthread_init then runs the actual provider initialization. No pthread wait/syscall is bypassed. Source staging includes bounded explicit address casts/zero user addresses and panic-format fixes. SWEET kernel opaque ksyn storage enlarged from48 to56 bytes to contain this provider's trailing kwe_uth, with a provider size assertion. Local compile of three provider TUs plus pthread_shims/kern_fork passed; imports resolve and provider exports do not collide with existing kernel symbols. All19 patches apply and changed sources match (`research/patch0019-check.log`). Source sandbox `research/bt22/xnu`, originals `research/pre0019`, objects `research/pthread-objs`. Local TargetConditionals fixture only has target macros for syntax; CI stages the real macOS SDK header and is authoritative. Next Actions artifacts: out-0019 / bt23 / run23.log; run QEMU >=45 seconds. 0019 CI is pending; no 0019 QEMU run yet.
- **Latest kernel implementation `e7d9550`, patches0001-0018; CI `38760004398` PASSED (3m56s)**: https://github.com/dipa-studio/ios-sweet/actions/runs/38760004398. No build is pending. Kernel `xnu/out-0018/kernel.development.sweet`, SHA256 `b3c8d59acc88f93a2c836eb2527a05ed4fbaac7c580a2ea8c3b795137f4aadf1`; checksum verified. Source/log `research/bt22` / `research/run22.log` (baseline for patch0019; no nested .git). New driver/config sources match CI exactly.
- **CPU wait FIXED in QEMU**: SweetCPU uses legacy IOCPU, validates single boot CPU, ml_processor_register -> processor_start -> initCPU real SGI1 -> scheduler/IOKit completion -> ml_set_max_cpus. It does NOT force a flag or skip a wait. CPU APIs passed: Running CPU0, processor_array[0] association, SGI signalling enabled, name, unsupported secondary-start error (`research/check-cpu18.gdb` / `.log`, `research/q0018-api`). Single-core only; SMP and suspend unsupported. Two-CPU topology fails explicitly (`research/q0018-smp`).
- **Next blocker reproduced in 45s QEMU** (`research/q0018-long`, zero unknown glyphs): BSD initialization reaches MAC framework, network mcache and `mbinit: done`, then **`pthread kernel extension not loaded (function table is NULL). @pthread_shims.c:318`**. Do not bypass pthread_init: find/integrate the matching open-source libpthread kernel implementation and register its real function table. A 12s run `research/q0018` looked panic-free before the 30s IORTC wait elapsed; use >=45s or GDB checkpoints for the next iteration. No userland/root filesystem boot yet.
- **Phone 0018 TEMPORARILY BOOTED** 2026-10-15 **15:31:15 UTC**: exactly one FASTBOOT device verified product sweet; send OKAY0.400s, boot OKAY0.134s, total0.539s, exit0. Local log `research/boot0018.log`. This confirms bootloader acceptance only. User was asked for a photo; await it, DO NOT reboot the phone again before their observation. No flashing performed.
- Current hardware image `shim/out/shim-boot-0018.img`, **16,437,248 bytes**, SHA256 **`b7a23595d143a76c72c9fe2cfcc5d77a8f16987b5af1a2703bbffdfa6922908c`**. Phone ADT/payload `shim/out/sweet-0018.adt` / `shim/out/payload-0018.bin` (timer19), unpacked ramdisk exactly matches payload (`shim/out/check-0018`). EntryPA0xb146b488; kernelendPA0xb1ffc000; boot_argsPA0xb2000000/top0xb2004000. Command line `debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam -noprogress`.
- QEMU payload/ADT `research/q0018.bin` / `research/q0018.adt` (timer27). Run `python3 tools/qemu-sweet.py research/q0018.bin research/NEW-OUT --secs 45 --kernel xnu/out-0018/kernel.development.sweet --fail-on-panic`; fresh ADT seed for a new payload. Output fb.png/fb.txt/regs.txt/qemu.log/result.json. Visible panic exit2; blank/incomplete decode exit3; no_panic_observed is snapshot-only, not successful boot. -noprogress prevents the graphical indicator corrupting console text. Qualcomm XPU/bootloader/panel and SMC PSCI still need physical validation.
- Patches0014-0017 fixed PRNG registration/direct SHA256, explicit unavailable trust-cache service with rejected loads/no matches, built-in SweetPlatformExpert, and timer PPI from ADT (phone19/default19, QEMU27). All their checks/artifacts are preserved in the history below. CURRENT SWEET has NO USE_APPLEARMSMP; do not assume gCPUIC/gAIC/gPMGR AppleARMSMP globals exist.
- Local single-file checker: tools/xnu-cc.py research/run22.log research/bt22 FILTER --per-file, output via XNU_CC_OBJDIR. Patch checker `research/check-patch-order.py` applies all18 via temporary index, matches sandbox sources. Sandbox for0018 `research/bt21/xnu`, originals `research/pre0018`, objects `research/cpu-objs`. First compiler issues were missing machine/atomic.h and nonexistent getNameSymbol; fixed and both TUs compiled successfully before CI. Fixtures/artifacts under research are local-only/ignored.
- GDB: mask int(register)&((1<<64)-1) for unsigned kernel pointers; use function-entry manual-call return traps, discard manipulated guests. No QEMU fixture is intentionally left running.

### Earlier active handoff snapshot (superseded)


- **0018 milestone:** Actions `38760004398` PASSED (3m56s), checksums passed, new CPU/build files byte-match CI tree. Kernel `xnu/out-0018/kernel.development.sweet`, SHA256 `b3c8d59acc88f93a2c836eb2527a05ed4fbaac7c580a2ea8c3b795137f4aadf1`; log/tree `research/run22.log` / `research/bt22`. QEMU `research/q0018` 12s: boot CPU registered, SGI1 verified, CPU initialization complete, **BSD initialization entered** (copyright, MAC framework, buffer headers), no panic/zero unknown glyphs. Direct CPU API checks PASS (`research/check-cpu18.gdb`, `.log`, `research/q0018-api`): CPU0 Running, processor matches processor_array[0], real SGI enabled, CPU name correct, secondary-start returns KERN_NOT_SUPPORTED. Two-CPU ADT correctly panics before registration (`research/q0018-smp`). Longer 45s run `research/q0018-long` still running; next BSD wait/fault not yet identified.
- **Prepared 0018 phone image:** `shim/out/shim-boot-0018.img`, 16,437,248 bytes, SHA256 `b7a23595d143a76c72c9fe2cfcc5d77a8f16987b5af1a2703bbffdfa6922908c`. Phone ADT/payload `shim/out/sweet-0018.adt` / `shim/out/payload-0018.bin`, usual debug args with cpus=1 and -noprogress. Unpacked ramdisk byte-compared (`shim/out/check-0018`). Entry PA remains 0xb146b488; kernel end PA 0xb1ffc000, boot_args 0xb2000000/top0xb2004000. User reports FASTBOOT+USB ready; read-only check found exactly one product sweet. NEXT: temporary fastboot boot of this verified image, record send/boot results, then await hardware photo without rebooting again.
- Patch 0018 committed/pushed **`e7d9550`**; Actions **`38760004398`** queued/running: https://github.com/dipa-studio/ios-sweet/actions/runs/38760004398. Do not launch a duplicate run.
- Active continuation: patch **0018** implemented in `iokit/Kernel/arm/SweetCPU.cpp` + arm64 source list + exact qcom,kryo470 personality. Keeps legacy IOCPU, accepts ONLY the single boot CPU, fills ml_processor_info from parsed topology with CPU object as cpu_id, calls ml_processor_register and processor_start. initCPU sends SGI1 via ICC_SGI1R_EL1 and waits (1-second deadline) for real cpu_signal_handler to clear SIGPdisabled. Only after successful startup calls ml_cpu_init_completed/cpusRunning and publishes completion/max CPUs. Secondary startup/suspend are explicitly unsupported. Local C++ compile passed for both TUs (`research/cpu-objs`), all imports resolve, object contains dsb ishst / ICC_SGI1R / isb; all18 patches apply in order and match sources. Sandbox `research/bt21/xnu`, originals `research/pre0018`; next CI artifacts should use `xnu/out-0018`, `research/bt22`, `research/run22.log`. User has the phone available; first run QEMU, then prepare/temporarily boot useful hardware progress.
- Goal: iOS 16 generation XNU on Redmi Note 10 Pro / sweet. User wants persistent progress, commits, kernel builds via `gh` Actions, and this handoff kept current across agent switches. Temporary `fastboot boot` only; preserve Android and backups.
- Latest kernel implementation: **`aa3f991`**, patches **0001-0017**. All four new Actions builds PASSED: 0014 `38748543058` (4m0s), 0015 `38749549779` (4m3s), 0016 `38750733996` (4m3s), 0017 **`38751507437` (4m7s)**. Latest: https://github.com/dipa-studio/ios-sweet/actions/runs/38751507437. No build is pending.
- **Current blocker: CPU initialization has no SWEET CPU driver.** QEMU registers SweetPlatformExpert, then kernel_bootstrap_thread waits in **kperf_init_early -> ml_wait_max_cpus**. Confirmed via actual-kernel GDB call stack (`research/locate-cpu-wait2.log` / `.symbols`) and normal-run `max_cpus_initialized == 2` (MAX_CPUS_WAIT). Do not force the flag or remove the wait. Next implement real CPU registration and completion using XNU's CPU/processor interfaces. CURRENT SWEET uses legacy IOCPU (`USE_APPLEARMSMP` is absent); enabling AppleARMSMP is a separate architectural change requiring GIC/PMGR services. No userland/root filesystem boot yet.
- Fixed this session: PC=0 unregistered PRNG callback (0014, built-in HMAC-SHA256 provider + direct entropy/write_random hashing); absent Image4/AMFI trust-cache service (0015, unavailable runtime, loads rejected and queries no-match); missing platform driver (0016, SweetPlatformExpert exact personality); incorrect QEMU timer IRQ (0017, validated ADT PPI property, phone default19/QEMU27).
- **Latest kernel** `xnu/out-0017/kernel.development.sweet`, SHA256 `055a80190ab998b4df9203f1102072dcc78faad1779a537a514e522b682b582f`. Buildtree/log **`research/bt21` / `research/run21.log`**; all nine changed C/C++/header/config files byte-match local checked sources. Checksums passed. Entry PA `0xb146b488`, kernel end PA `0xb1ff4000`. Preferred baseline for patch 0018: `research/bt21/xnu` (no nested .git).
- **QEMU verified**: `research/q0017-noprogress` ran **30 seconds**, no visible panic, **zero unknown glyphs**, IRQ exceptions returned normally (4 IRQs, tickless idle). It still waits for CPU completion, so this is NOT a completed boot. Earlier 15s run `research/q0017` captured 122 IRQs, timer value27, GICR_ISENABLER0 `0x08000002`, and CPU WAIT; graphical progress overlay corrupted 13 glyphs. Add **`-noprogress`** to keep the console readable. New runner classifies incomplete/blank decoding explicitly (exit3 with --fail-on-panic), visible panic exits2. Snapshot-only; use regs/GDB to diagnose stalls.
- Current QEMU payload/ADT: **`research/q0017-noprogress.bin` / `research/q0017.adt`**. Run: `python3 tools/qemu-sweet.py research/q0017-noprogress.bin research/NEW-OUT --secs 30 --kernel xnu/out-0017/kernel.development.sweet --fail-on-panic`. Generate fresh seed with mkadt for a new payload. QEMU virt models generic ARM execution, not Qualcomm XPU/bootloader/panel or the phone's SMC PSCI conduit.
- **Prepared phone image**: **`shim/out/shim-boot-0017.img`**, 16,416,768 bytes, SHA256 `51ff7fe30b4a6668c3452ffe1da922c5ac30cb8de60625c2a652587ecbd0ec92`. Phone ADT/payload `shim/out/sweet-0017.adt` / `shim/out/payload-0017.bin` (timer19). Unpacked ramdisk exactly matches payload (`shim/out/check-0017`). Command line **`debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam -noprogress`**. NOT sent to phone this session: known CPU-driver wait should be addressed in QEMU first. Last actual phone boot remains 0013; user's latest photo `IMG_20261015_160033.jpg` confirmed the old PRNG PC=0 panic.
- Direct QEMU/GDB API checks: PRNG 600-byte chunking, buffer bounds, changing output, zero-length reads/writes, user reseed, contended refresh, generator1 init/output PASS again on latest0017 (`research/check-prng17.gdb` / `.log`, guest `research/q0017-api`). Trust-cache unavailable-service/argument/output cases PASS on0015 (`research/check-trustcache.gdb` / `.log`). Platform registration + target/product normal/truncated/zero/null/bounds PASS on0016 (`research/check-platform.gdb`, `research/check-platform3.log`). Different platform ID correctly retains IOPanicPlatform fallback (`research/q0016-negative`). Timer PPI32 and size2 correctly panic (`research/q0017-badppi`, `research/q0017-badsize`); omitted property selects19 (`research/q0017-default`). These are API/bring-up checks, not crypto certification or SMP scheduling validation.
- Local checker **`research/check-patch-order.py`** verifies all17 patches and changed source equality using a temporary upstream git index. Fixtures/logs/artifacts under research are local-only and ignored. For GDB unsigned kernel pointers, mask `int(register_value) & ((1<<64)-1)`; x30/x29 may be rendered signed. Stop at a function entry for manual-call return traps, and discard each manipulated guest after API tests. All fixture QEMU guests have been stopped.


- User wants persistent progress toward iOS 16, commits for completed changes, builds through `gh` / GitHub Actions.
- Keep this file current at every milestone so another agent can resume immediately, including when usage limits interrupt a session.
- Patch 0017 committed/pushed `aa3f991`, Actions `38751507437` running: https://github.com/dipa-studio/ios-sweet/actions/runs/38751507437. Next artifacts: xnu/out-0017, research/bt21, research/run21.log. Do not duplicate.
- Patch 0016 kernel downloaded/checksum verified: SHA256 `d06336c54baa06e0df6561a8bd7df98a9b9f7502c9381c62d1a44c045cd1ce46`, `xnu/out-0016/kernel.development.sweet`; buildtree/log `research/bt20` / `research/run20.log`. QEMU `research/q0016` (10s) prints platform expert registered, zero unknown glyphs, no panic observed BUT stalls (timer mapping still wrong until 0017). Direct actual-kernel GDB tests passed for registered instance and target/product names, including maxLength=1/0 and NULL, sentinels intact (`research/check-platform.gdb`, `research/check-platform3.log`, `research/q0016-api3`). First two fixture attempts used premature/wrong return breakpoints; discarded, corrected fixture uses start-return observation then a function-entry return trap. No phone boot yet.
- Patch 0016 CI `38750733996` PASSED (4m3s); artifacts not yet downloaded/booted. Patch 0017 prepared to fix QEMU timer fidelity BEFORE interpreting future no-panic/stall runs: actual `qemu-system-aarch64 -M virt,gic-version=3,dumpdtb=research/qemu-virt.dtb ...` timer property has virtual PPI 11 => INTID 27, while phone uses INTID 19. Kernel formerly hardcoded 19. New optional /arm-io/gic virtual-timer-intid property selects the PPI (validate exact u32 and 16..31); missing property retains phone default 19. One RO-late global drives GIC enable and sleh_irq dispatch. tools/mkadt.py emits phone19/QEMU27. Both C TUs compile (`research/timer-objs`), ADT serialize/parse checks confirm values/addresses, all 17 patches apply and match. Sandbox `research/bt19/xnu`, originals `research/pre0017`; initial local sleh compile failed due read-only exported header not updated, fixed export and BOTH recompiled successfully. CI exports normally.
- Architecture correction for next agent: CURRENT SWEET board_config does NOT define USE_APPLEARMSMP; it compiles the legacy IOCPU path, not cpu_boot_thread/IOPMGR AppleARMSMP. Existing roadmap mentions AppleARMSMP as a future approach. Do not look for gCPUIC/gAIC/gPMGR globals in the current kernel: they are absent. Determine the actual CPU-init wait after platform registration before choosing the next driver architecture.
- Patch 0016 committed/pushed as `0dcdf5c`; Actions `38750733996` running: https://github.com/dipa-studio/ios-sweet/actions/runs/38750733996. Next artifacts: `xnu/out-0016`, `research/bt20`, `research/run20.log`.
- Patch 0016 implemented: new `iokit/Kernel/arm/SweetPlatformExpert.cpp`, arm64 source list, built-in personality in KernelConfigTables.cpp guarded by ARM64_BOARD_CONFIG_SWEET. Matches only xiaomi,sweet at score 10000, keeps IOPanicPlatform fallback for other hardware. Uses IODTPlatformExpert base initialization/power domain and createNubs CPU logical-ID annotation; overrides top-level publishing because base requires nonexistent Apple NVRAM /options. Publishes real CPU/top-level nodes, provides bounded target/product names, and registers the platform service. GIC/PMGR and arm-io child-bus drivers remain separate work. Both C++ TUs compile (`research/platform-objs`), all imports resolve against 0015/own objects, all 16 patches apply and sources match. Sandbox `research/bt19/xnu`; originals `research/pre0016`. NEXT: full Actions/QEMU; inspect CPU boot waits after the platform registers, do not equate absence of panic with successful boot.
- Patch 0015 CI `38749549779` PASSED (4m3s), checksum verified. Kernel `xnu/out-0015/kernel.development.sweet`, SHA256 `ca1b424a596c7058550ad1659080a333e7643270f019656401d80bf2b876645f`; buildtree/log `research/bt19` / `research/run19.log`. QEMU `research/q0015` (10s, zero unknown glyphs) passes trust-cache handling and machine lockdown, then panics `Unable to find driver for this platform: "xiaomi,sweet" @IOPlatformExpert.cpp:2319` (IOPanicPlatform fallback). Next concrete work: add a built-in SWEET IODTPlatformExpert personality/class; keep the fallback for mismatched platforms. No phone boot yet.
- Direct trust-cache API checks PASSED in the actual 0015 kernel under QEMU/GDB (`research/check-trustcache.gdb`, `research/check-trustcache.log`, `research/q0015-api`): runtime pointers NULL, hash/UUID queries return NOT_FOUND, typed/untyped/legacy loads return NOT_SUPPORTED, capabilities outputs zero and bounds preserved, invalid-argument cases still reject. Second PRNG check also verifies contended refresh returns immediately (`research/check-prng2.log`, `research/q0014-api2`).
- Patch 0015 committed/pushed `8f851d4`, Actions run `38749549779` running: https://github.com/dipa-studio/ios-sweet/actions/runs/38749549779. Do not duplicate.
- Direct PRNG API checks passed in the REAL 0014 kernel under QEMU/GDB, stopped before trust-cache init (`research/check-prng.gdb`, log `research/check-prng.log`, guest `research/q0014-api`). Invoked read_random for 600 bytes (chunking and buffer sentinel intact), repeated output differed, zero-length read/write succeeded, write_random(64-byte input) succeeded, secondary generator 1 initialized and generated distinct output. QEMU log has no exceptions during these checks; guest was discarded after the tests. This tests API behavior, not a cryptographic certification or SMP scheduling.
- Patch 0015 implemented in `bsd/kern/kern_trustcache.c`: SWEET with missing Image4/AMFI marks both runtime pointers NULL and logs service unavailability. Existing static loader handles NULL. Public load APIs return KERN_NOT_SUPPORTED; hash/UUID queries return KERN_NOT_FOUND; capabilities outputs are zero with KERN_NOT_SUPPORTED. Invalid-input checks remain, and Apple paths/available-provider initialization retain existing behavior. No trust is granted. Local arm64 compile passed (`research/trustcache-objs`), all 15 patches apply and sources match. Sandbox `research/bt18/xnu`, baseline `research/pre0015`. Next: Actions/QEMU and direct unavailable-service API checks using GDB.
- Patch 0014 CI `38748543058` PASSED (4m0s), artifact checksum passed. Kernel `xnu/out-0014/kernel.development.sweet`, SHA256 `741de20c851755d333759d7e668346f3edb4f325efac4cc7c142d80d1f5ff75c`; buildtree/log `research/bt18` / `research/run18.log`. QEMU run `research/q0014` (10s, zero unknown glyphs) prints `SWEET PRNG: HMAC-SHA256 registered`, passes commpage initialization, loads vnguard policy, THEN panics `image4 interface not available @kern_trustcache.c:253`. PC=0 fault FIXED IN QEMU. No new phone boot performed.
- Next work: SWEET currently has neither AppleImage4 nor AMFI. `trust_cache_runtime_init` unconditionally requires both; unlike BCM2837, SWEET enters this startup path. Investigate an explicitly unavailable trust-cache runtime with rejected loads/no query matches while providers are absent; preserve all Apple-platform checks. Merely skipping the startup call would leave later AMFI/IMG4 dereferences unsafe. Existing load_static_trust_cache already handles trust_cache_rt == NULL.
- QEMU runner now supports `--kernel MATCHING_KERNEL --fail-on-panic`: runtime font extraction from the payload produces exact `fb.txt`, plus `result.json`; a visible panic returns 2. Baseline 0013 re-run `research/q0013-text` detects the same NULL callback panic with zero unknown glyphs. Synthetic glyph roundtrip (including literal `?`) and invalid-VA rejection passed. Screen rows remain circular, not a full log; `no_panic_observed` does not prove successful boot. README has the invocation.
- Patch 0014 committed/pushed as `be61f99`; Actions run `38748543058` is running: https://github.com/dipa-studio/ios-sweet/actions/runs/38748543058. Do not start a duplicate build.
- 2026-10-15 active: hardware photo `IMG_20261015_160033.jpg` confirms the same PC=0 instruction-fetch abort as QEMU (LR `0xfffffe0007443fe4` = read_random). Independently reproduced with kernel 0013 in `research/q0013` (8-second run); prior allocator fix works. Latest tooling commit reviewed: `8d66d2d`.
- Patch 0014 implemented: registers a built-in HMAC-SHA256 DRBG provider at EARLY_BOOT/FIRST, before commpage creation. A shared mutex serializes output/reseed across CPUs (correctness first; no per-CPU scaling yet), initgen validates CPU identities, refresh uses try-lock and the existing entropy filter/health tests. SWEET entropy accumulation and write_random now use the built-in SHA256 directly; no incomplete g_crypto_funcs table is registered. The existing bootloader-seed requirement remains enforced.
- Local validation: both PRNG translation units compile to arm64 objects in `research/prng-objs`; no SHA256 wrapper imports remain. All 14 patches apply in CI order and resulting PRNG sources match local inputs. Sandbox `research/bt17/xnu`, originals `research/pre0014`, checker `research/check-patch-order.py`. NEXT: Actions kernel build, download to `xnu/out-0014`, run the QEMU payload before requesting another phone boot. Baseline QEMU ADT/payload are `research/q0013.adt` / `research/q0013.bin`.
- 2026-10-15 08:15 QEMU EMULATION WORKS (`tools/qemu-sweet.py`, see "QEMU emulation" below). Patch 0013 VERIFIED in QEMU: boot passes kmem_crypto_init and ulock_initialize. NEXT BLOCKER (reproduced in QEMU, expected on hardware too): `pmap_create_commpages -> random() -> RandomULong -> read_random -> prng_funcs.refresh == NULL` (instruction fetch abort at pc 0, lr read_random+0x34). Nobody calls `register_and_init_prng` (closed corecrypto kext does it on Apple). Fix = patch 0014: SWEET-registered cckprng_funcs provider (osfmk/prng/prng_random.c); note random_cpu_init also panics while !prng_ready. The 07:26 hardware boot of 0013 will most likely show this same panic.
- Previous hardware boot: patch 0013 (`a3a46e2`) CI `38686345689` PASSED (3m44s), image `shim/out/shim-boot-0013.img` was temporarily booted on 2026-10-15 at 05:26 UTC: send OKAY (0.407s), boot OKAY (0.134s), total 0.546s. Superseded by the hardware/QEMU PC=0 observation and patch 0014 work above.
- Latest kernel implementation commit: `8f851d4`. Latest successful kernel CI: `38749549779` (patch 0015), https://github.com/dipa-studio/ios-sweet/actions/runs/38749549779.
- CURRENT image: `shim/out/shim-boot-0013.img`, 16,412,672 bytes, SHA256 `110d1c46aee4b60253db24b6535e9781c4cf0fd25ca2a70e9016cf81378cea25`. Kernel `xnu/out-0013/kernel.development.sweet`, SHA256 `f0b1d375995316c550ce7014ff234d8271e9b9ac2857795ceff41b76ba2cd740`, plain arm64. CI log confirms 0013 applied; checksums passed. Entry PA `0xb146b488`, kernel end PA `0xb1ff4000`.
- Current log/buildtree: `research/run17.log`, `research/bt17` (extracted, no nested .git; preferred baseline for patch 0014). Payload/ADT: `shim/out/payload-0013.bin`, `shim/out/sweet-0013.adt` (includes /defaults). Unpacked ramdisk byte-compared with payload in `shim/out/check-0013`.
- Patch-0012 original image: `shim/out/shim-boot-0012.img`, 16,412,672 bytes, SHA256 `cf4b8ec4a65a51888d71c17d09cd0831d6b761b90e2531fdb8e575c32f4fd24a`. Kernel `xnu/out-0012/kernel.development.sweet`, SHA256 `69b78f49f6459cc63a0af44e7cf73c1779ef72130ef72b12ae86c88183ffc742`; checksums passed and sweet_early_relocate symbol present. Entry PA remains `0xb146b488`, kernel end PA `0xb1ff4000`.
- Patch-0012 log/tree: `research/run16.log`, `research/bt16` (extracted, no nested .git; preferred baseline for next patch). CI log confirms 0012 applied. Payload `shim/out/payload-0012.bin`, ADT `shim/out/sweet-0012.adt`; packed ramdisk byte-compared with payload in `shim/out/check-0012`.
- Active payload command line: `debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam`.
- Latest observed photo: `/home/dipa/Downloads/IMG_20261015_071346.jpg` (local only). Stages 9 (kernel framebuffer VA), 10 (TTBR0 off/TLB flush), 11 (physmap table pointers) and 12 (calling pmap_bootstrap) all visible. Persistent diagnostics are VERIFIED ON HARDWARE.
- pmap.c:1987 is the assert after SecureDTLookupEntry(NULL, "/defaults", &entry). The pmap-max-asids property itself is optional; an empty /defaults uses XNU's MAX_ASIDS. Do not bypass the assertion or guess an ASID limit.
- Previous payload-only fix image: `shim/out/shim-boot-0012-defaults.img`, SHA256 `3ff61a268853c6ea7cbf284833f1346a1d791980ca366b6e1a215a86e040512b` (16,412,672 bytes). Same kernel/CI as 0012; ADT 2516 bytes (`shim/out/sweet-0012-defaults.adt`), root /defaults present with no ASID override. Payload `shim/out/payload-0012-defaults.bin`; unpacked ramdisk exactly matches payload (`shim/out/check-0012-defaults`). This boot reached the allocator crypto NULL-pointer fault below.
- Latest hardware photo: `/home/dipa/Downloads/IMG_20261015_071608.jpg` (local only). Normal serial framebuffer console works. VM bootstrap/zone initialization, logging, scheduler, IPC, KDP and ulock_initialize print before the kmem_crypto_init data abort. gPanicBase warnings are expected because PLATFORM_PANIC_LOG_DISABLED is configured, and are not the faulting call.
- Faulting instruction: `ldr x0, [x8, #0x150]` in crypto_random_kmem_ctx_size; x8 = NULL g_crypto_funcs. Source: libkern/crypto/corecrypto_rand.c and osfmk/vm/vm_kern.c:2448. rand.h explicitly permits NON-cryptographic kmem RNGs, but requires no locking in generation and context size <=256. Do not substitute read_random here: the global PRNG provider is also unregistered and kmem generation must remain lock-free. early_random may seed contexts during single-CPU bootstrap; it uses the built-in HMAC-SHA256 DRBG with the host-generated ADT seed.
- Patch 0013 keeps the replacement entirely private to vm_kern.c: SplitMix64 state is 8 bytes per CPU/sizeclass, initialized using early_random. Uniform selection uses rejection sampling to avoid modulo bias. Other platforms retain the original corecrypto calls; SWEET's generic crypto APIs/registration remain untouched. Reference: https://prng.di.unimi.it/splitmix64.c (Sebastiano Vigna, public domain).
- Validation: vm_kern.c compiles to arm64 (`research/kmem-rng-objs`, using `research/run16.log` + `research/bt16`). Undefined symbols include early_random and NO crypto_random_* references. All 13 patches apply in CI order and match the checked source. Original saved as `research/vm_kern.pre0013.c`.
- RNG host checks: extracted actual new helper in `research/kmem-rng-check.c`; 16,384 outputs match the author's downloaded reference (`research/splitmix64-reference.c`), 147,456 bounded outputs satisfy their limits (including 1 and UINT64_MAX), and a forced rejection advances correctly. Full kernel crypto services and the registered kernel PRNG provider remain future work; this patch only supplies the allocator RNG contract.
- Patch-0011 artifacts: kernel `xnu/out-0011/kernel.development.sweet`, log `research/run15.log`, extracted buildtree `research/bt15` (no nested .git). CI log confirms patch 0011 applied; artifact checksums passed. Kernel is plain arm64, entry VA `0xfffffe000746b488` -> PA `0xb146b488`, kernel end PA still `0xb1ff4000`.
- Patch-0011 image: 16,412,672 bytes, SHA256 `29ad5cbfc752473de4af2c471a24a8b34f92da4bff5afec65c614b90cd3ad53a`. Kernel SHA256 `8ac3a956894b09f7bd0d890de8c5de38c65513287feb1e1bcd12db8ca772ee5c`. Payload/ADT in `shim/out/payload-0011.bin`, `shim/out/sweet-0011.adt`. Header unpacked/checked in `shim/out/check-0011`.
- First patch-0011 attempt timed out waiting for FASTBOOT; superseded by the successful send/boot recorded above. Do not repeat the boot before the user reports the current screen.
- Patch-0011 photo: `/home/dipa/Downloads/IMG_20261015_070218.jpg` (local only). Visible stages 1-8 and old red shim text; entry PA B146B488, boot args PA B1FF8000 / top B1FFC000. No evidence yet locating execution after stage 8.
- Patch-0012 sandbox: `research/bt15/xnu` (NO nested .git). Proposed permanent debug VA: VM_MIN_KERNEL_ADDRESS + ARM_TT_L2_SIZE, in the reserved gap below gVirtBase and above low globals; map the same PA framebuffer as Normal-NC in the final TTBR1 before arm_vm_physmap_init changes phystokv(). Keep the early panic sink until normal kprintf startup.
- Patch 0012 validation: all 4 changed C translation units compiled to arm64 objects in `research/post-ttbr0-objs`; internal header export added to osfmk/arm64/Makefile and recreated locally in EXPORT_HDRS for pe_serial.c. All 12 patches apply in CI order and match all 6 edited files. Baselines are saved under `research/pre0012/`.
- Actual mapping-helper host model (`research/early-map-check.c`, barrier stubbed only for host compilation) confirms: VA `0xfffffe0002000000`, L1 index 2016, L2 index 1; descriptor `0x006000009c000605` = framebuffer PA, Normal-NC, outer-shareable, EL1 RW, PXN+UXN. All other L2 entries preserved. The gap is excluded by ARM_LARGE_MEMORY's pmap_virtual_region(0).
- Next boot command line MUST add `-enable_kprintf_spam`: DEVELOPMENT disables kprintf_output by default even when DB_KPRT is set (`pexpert/arm/pe_kprintf.c`). Planned command line: `debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam`.

### Patch 0012 screen legend (after original stages 1-8)
- 9: kernel framebuffer VA live; 10: TTBR0 off / TLB flushed; 11: physmap pointers rebound.
- 12: calling pmap_bootstrap; 13: pmap_bootstrap returned; 14: early I/O page tables ready; 15: arm_vm_init returned.
- 16: calling serial_init; 17: fbcon config read / mapping; 18: fbcon mapping returned; 19: serial_init returned; 20: kprintf startup complete.
- Normal serial initialization clears the screen, so earlier stages may disappear before 19. If serial exists, early console disables after 20; otherwise early panic output stays enabled.
- Local source sandbox: `research/bt13/xnu` (git baseline `623b060`, patches 0001-0008 already in baseline; uncommitted export edits correspond to patch 0009). Preserve those edits when producing patch 0010.
- Previous compile log/tree: `research/run13.log`, `research/bt13`; previous kernel: `xnu/out/kernel.development.sweet`. New successful log/tree: `research/run14.log`, `research/bt14`; new kernel: `xnu/out-0010/kernel.development.sweet`.
- Current device access: patch-0012 image was temporarily started from FASTBOOT; no adb connection is expected. Never flash partitions for bring-up; use `fastboot boot` with the shim image.
- Patch `0010` lives in `xnu/patches/0010-sweet-early-framebuffer-debug.patch`. Its exact compiled sources are under `research/bt13/xnu`; generated objects are in `research/early-objs`.
- Local checks passed: all 5 changed/new translation units compiled to arm64 Mach-O objects; new console only imports `_doprnt` and `iso_font` (both exist in the previous kernel). All 10 patches applied to a temporary upstream git index in CI order, and all 7 resulting changed source files matched the local compile inputs.
- Reproduce changed-file compilation: `XNU_CC_OBJDIR="$PWD/research/early-objs" python3 tools/xnu-cc.py research/run13.log research/bt13 arm_init.c arm_vm_init.c kern/debug.c arm64/start.s osfmk/arm64/sweet_early.c --per-file` (create the output directory first). The helper now accepts explicit new source paths absent from the old artifact's Makefiles and rejects empty selections.
- Device command result: `adb reboot bootloader`, then `timeout 30s fastboot boot shim/out/shim-boot-0010.img`: send OKAY (16028 KB), boot OKAY, total 0.541s. This confirms bootloader acceptance only, not XNU progress.
- The successful boot above was on 2026-10-14. On 2026-10-15, `timeout 45s fastboot boot ...` timed out waiting for a device; no image was sent. Boot image SHA256 rechecked and unchanged. No new build is needed to repeat the trial.
- Earlier retry: `timeout 90s fastboot boot shim/out/shim-boot-0010.img` timed out (exit 124). This is superseded by the successful 2026-10-15 repeat boot recorded above; do not repeat it until the user reports the screen.
- User observation confirms MMU-on C entry, platform expert, CPU topology/bootstrap, startup bootstrap and cpu_init all complete. Failure is within arm_vm_physmap_init (non-XNU_MONITOR branch), before stage 8 / TTBR0 teardown. Old red shim text remains behind the early console; this is expected because only written rows are cleared.
- New edit/compile sandbox is `research/bt14/xnu` (extracted artifact, NO nested .git; `git diff` there would act on the parent project). Use a saved baseline file / generated unified diff, or explicitly initialize a local baseline before editing. `research/bt13/xnu` does have its own baseline git repo.
- Exact user-reported panic: `arm_vm_init.c:1606 Assertion failed: (temp_ptov_table[ptov_index - 1].va + temp_ptov_table[ptov_index - 1].len) <= physmap_end`.
- Root cause: MacOSX build sets `ARM_LARGE_MEMORY=1`; `XNU_MONITOR` is off. Block alignment in arm_vm_physmap_slide can add gaps, but the non-PPL large-memory physmap_end omitted the padding already present in the small-memory branch. Patch 0011 reserves PTOV_TABLE_SIZE*ARM_TT_TWIG_SIZE (8*32MB) in both the aperture bound and its L1 allocation; monitor/PPL builds retain zero padding. The assertion is preserved.
- Validation: `arm_vm_init.c` compiled to an arm64 object using `research/run14.log` + `research/bt14` (object in `research/physmap-objs`). All 11 patches apply in CI order and produce exactly that source. Host harness `research/physmap-check.c` extracts the real XNU slide function with page-table-write stubs: all 65,536 page-aligned slides within 1GB checked against the current kernel memory layout; old bound fails 65,504 cases, padded bound fails zero; worst overrun 0x1ffc000 bytes. Baseline source saved as `research/arm_vm_init.pre0011.c`.
- CI: https://github.com/dipa-studio/ios-sweet/actions/runs/38638702083 (success; artifacts and full log downloaded).
- New image: `shim/out/shim-boot-0010.img` (16,412,672 bytes, SHA256 `ed2c270e0081bad5ff517be415f9bfe8805463aea7866732203fa97ac737e64e`). Previous image preserved as `shim/out/shim-boot-pre0010.img`.
- New kernel SHA256: `3ee05270cc291c49589a101678f904b1b69cb2f2575e05398bce8a4e052f409a`. Artifact checksums passed; arm64 (not arm64e), early-console symbols present. Payload entry VA `0xfffffe000746a488` -> PA `0xb146a488`; kernel end PA `0xb1ff4000`. Command line remains `debug=0xc serial=3 cpus=1 keepsyms=1`.

### Patch 0010 screen legend
- Bottom-left white 64x32 tile: assembly entered `start_first_cpu`, before page tables/MMU.
- Text `SWEET EARLY 1`: entered `arm_init` with MMU on; 2: platform expert done; 3: CPU topology done; 4: CPU bootstrap done; 5: startup bootstrap done; 6: CPU init done; 7: entering `arm_vm_init`; 8: leaving bootstrap TTBR0.
- `SWEET EARLY PANIC:` prints a copy of panic arguments before normal panic handling needs per-CPU/thread state.
- In patches 0010/0011 the console disabled before TTBR0 invalidation; patch 0012 replaces that with a persistent kernel VA alias and diagnostics through normal serial/kprintf startup (see its legend above).
- Screen contents require a physical observation from the user: adb cannot capture a framebuffer after Android has been replaced by a bare-metal kernel.

## QEMU emulation (2026-10-15)
- `tools/mkadt.py OUT.adt --qemu` = same ADT with QEMU virt GICD 0x08000000 / GICR 0x080a0000 / CNTFRQ 62.5 MHz.
- `tools/qemu-sweet.py PAYLOAD OUTDIR [--secs N] [--hmp "x /8gx ADDR"] [--gdb]`: host-side copy of shim/loader.c
  (segments + ADT + boot_args at their PAs, 6-instruction stub sets x0 and jumps), `-M virt,gic-version=3 -cpu cortex-a76`
  (same ID_AA64MMFR0 as Kryo 470), 4G RAM so 0x9c000000 fb and 0xb0000000 kernel are plain RAM.
  Outputs `fb.png` (the screen), `regs.txt`, `qemu.log` (exceptions with ESR/FAR/ELR). `--gdb` halts with a stub on :1234
  (system `gdb` + `set architecture aarch64`, `hbreak *VA` works with the MMU on).
- Not emulated: Qualcomm XPUs, ABL, real panel, PSCI conduit (QEMU virt uses hvc). Hardware still decides those.
- Example: `python3 tools/mkadt.py /tmp/q.adt --qemu && python3 tools/mkpayload.py xnu/out-0013/kernel.development.sweet /tmp/q.adt /tmp/pq.bin --cmdline 'debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam' && python3 tools/qemu-sweet.py /tmp/pq.bin /tmp/q`

## Layout
- `backup/`  partition dumps + full sdb..sdf LUNs, `SHA256SUMS` (all verified on-device == local)
- `dtb/`     live FDT (from OrangeFox), PixelOS boot.img dtb, dtbo, dts versions
- `shim/`    bare-metal boot shim (`./build.sh` -> `out/shim-boot.img`)
- `research/` mainline sm7150 dts, XNU pe_fiq.c etc, PocketDarwin patches
- `tools/unpack_bootv2.py`

## Device access
- No root in PixelOS 17 (user build, adb root disabled). Root = `fastboot boot recovery/recovery.img` (OrangeFox R12.0_2, temp boot, not flashed).
- `fastboot boot` works for stock boot.img, OrangeFox, and our shim.
- Shim resets itself via PSCI SYSTEM_RESET; IMEM restart_reason 0x77665500 is seen
  (bootreason=bootloader) but ABL still boots Android, so it does not stop in fastboot.

## Hardware facts (live DT + shim measurements)
- Framebuffer (ABL cont splash): 0x9c000000, 1080x2400, stride 4320, a8r8g8b8, panel is DSC *video* mode (no kick needed).
- RAM: 0x80000000+2G, 0x100000000+0xfcc00000. Live reserved-memory = PixelOS base dtb + sweet dtbo fixups.
- GICv3: GICD 0x17a00000, GICR 0x17a60000 (stride 0x20000, 8 PEs). GICD_TYPER 0x007B041D: SecurityExtn=1 (DS=0).
  ABL leaves GICD_CTLR = 0x10 (ARE_NS on, groups off). Writing 0x13 reads back 0x12: EnableGrp1A (bit1) is the one that matters.
- GIC Group 1 VERIFIED (shim 2c): vtimer INTID 19 = 30 IRQs/300ms, ptimer INTID 18 = 30, SGI 1 to self = 10/10.
  ICC_SRE=1 already, ICC_CTLR 0x8440, priority/enable writes stick. GICR_IGROUPR0 and GICD_IGROUPRn read 0 from NS
  even though Group 1 delivery works (RAZ in NS view) - do not use them as a health check.
  INTID 28 shows pending constantly (unknown PPI 12).
- Timer 19.2 MHz. Qualcomm PPI numbering: secure-phys/phys/virt/hyp = PPI 1/2/3/0 -> vtimer INTID 19, ptimer 18 (NOT 27/30).
- PSCI 1.1 via SMC, SMCCC 1.1. CPU_ON ok; SYSTEM_SUSPEND and SYSTEM_RESET2 unsupported.
- SMP: CPU_ON works for all 7 secondaries (MPIDR 0x81000n00).
- Entry EL1, MMU off, x0 = DTB (magic ok). ID_AA64MMFR0 = ...101122: 16K granule YES, 4K YES.
- No serial console: debug UART SE is in SPI mode on sweet. Screen is the only debug channel.

## XNU implications
- XNU GICv3 path (pexpert/arm/pe_fiq.c, VMAPPLE) puts the timer (PPI 27) in Group 0 = FIQ. With SecurityExtn=1,
  Group 0 is secure -> impossible from NS EL1. Need: Group 1 IRQ, ICC_IGRPEN1, INTID 19, and the timer handled in the IRQ path.
- XNU VMAPPLE PSCI uses `hvc`; sweet needs `smc`.
- PocketDarwin NonAppleGenericCpu.patch only swaps -mcpu=apple-h7 for -march=armv8-a.

## Milestone 3 (2026-10-14): 16K MMU verified
- ABL loads the Image at 0x80080000 (base 0x80000000 + 0x80000) regardless of text_offset=0.
- 16K granule, T0SZ=28 (L2 start, 32MB blocks), MAIR 0x44ff00, TCR 0x1409CB51C, PARange=2 (40-bit PA).
- Only own image pages WB (Qualcomm XPUs: never map carve-outs cacheable); fb Normal-NC; rest Device.
- AT S1E1R checks all as expected; unmapped -> translation fault L2.
- Fill fb: 110 ms (MMU off) -> 3.5 ms (NC). Memory loop 70 ms -> 0.7 ms. vtimer + SGI IRQs still fine with MMU on.

## XNU loader design notes (xnu-8796)
- Entry: `_start` -> `start_first_cpu`, x0 = boot_args (PA), MMU off, EL1. boot_args: Revision/Version 2,
  virtBase/physBase/memSize/topOfKernelData, Boot_Video (fb 0x9c000000, rowBytes 4320, 1080x2400, depth 32),
  deviceTreeP/Length (ADT), CommandLine[608], bootFlags, memSizeActual.
- start.s maps [kernel mach header .. physBase+memSize) with cacheable BLOCKS. On Qualcomm every XPU carve-out
  must therefore lie below the kernel: use physBase = 0xb0000000 (above ramdump_fb 0xaf000000+16M,
  cdsp_sec, qseecom), end before rmtfs 0xfde01000 -> memSize ~0x4d000000 for bring-up.
- Base ADT: iPhone 8 d20ap DeviceTree from iOS 16.7.16 IPSW (tools/remotezip.py + tools/adt.py; LZFSE payload).
  Template values are empty: the loader must fill chosen/*, memory-map, cpu*/reg etc. like iBoot.
- XNU build: GitHub Actions (dipa-studio/ios-sweet, xnu.yml) via blacktop/darwin-xnu-build, MACOS_VERSION=13.5.
  New-clang fixes in xnu/patches; Xcode 16 iig is incompatible (IORPC.kernelContent) -> macos-14 runner, oldest Xcode.

## Kernel architecture plan (SWEET machine config)
- First stock build (VMAPPLE) is arm64e (PAC). Kryo 470 = ARMv8.2, no PAC -> SWEET must build plain arm64
  (HAS_APPLE_PAC is only defined for __arm64e__, so arm64 drops PAC automatically).
- Template: VMAPPLE (16K pages, GICv3 code in pe_fiq.c) minus APPLEVIRTUALPLATFORM hypercalls/paravirt PAC,
  plus BCM2837 (generic ARM: no APPLE_ARM64_ARCH_FAMILY Apple sysregs). Do not link the KDK lib<cfg>.os.*.a.
- Timer: XNU expects it on FIQ (sleh_fiq -> rtclock_intr). SWEET: GIC Group 1, so sleh_irq must ack ICC_IAR1,
  route INTID 19 to the same timer path, SGIs to cpu_signal_handler, EOI via ICC_EOIR1.
- SMP/interrupts: open-source AppleARMSMP (USE_APPLEARMSMP) needs an IOInterruptController (AIC role) and an
  IOPMGR (CPU power -> PSCI CPU_ON via SMC). Plan: built-in IOKit classes (SweetGIC, SweetPMGR, platform
  expert) compiled into the kernel and matched via iokit/KernelConfigTables.cpp -> no closed kexts needed.
- Debug: xnu patch 0003 sweet-fbcon = kprintf drawn on the framebuffer (ADT node "sweet-fbcon").
- ADT /arm-io ranges must not map to parent 0 (pe_arm_get_soc_base_phys()==0 disables serial): use parent 0x1000000.

## Status 2026-10-14 late: first XNU boot attempt
- SWEET kernel builds (CI run 38635343732, patches 0001-0009). Verified offline: arm64, no PAC, no >v8.2 code,
  70300 classic relocs all in range (slide 0 = no loader work), entry = __start.
- Boot: shim loader worked (initrd 0x846F0000-0x855FE3E0, BOOTARG 0xB1FF8000, JUMP 0xB146A488) but screen stayed
  red -> xnu died/hung before serial_init (fbcon). kprintf is a no-op before STARTUP_SUB_KPRINTF.
- Historical next-step plan (patch 0010, now implemented and built; see active handoff above): early fb debug channel
  1. start.s start_first_cpu (after mov x20,x0 / mov x21,#0): PA marker band (MMU off, direct store to 0x9c000000).
  2. start.s after both create_bootstrap_mapping calls: add ONE block entry to the existing V=P L2 table
     (x25 + 2*PGBYTES; do NOT call create_bootstrap_mapping again: fb and RAM share L1 entry 0, it would replace
     the L2 table). Entry = TYPE_BLOCK|VALID|SH(OUTER)|ATTRINDX(CACHE_ATTRINDX_WRITECOMB=1)|AF|PNX|NX|0x9c000000,
     index = (va & ARM_TT_L2_INDEX_MASK) >> ARM_TT_L2_SHIFT.
  3. new osfmk/arm64/sweet_early.c (+files.arm64 entry): sweet_early_mark(n) colored bands at screen bottom and
     sweet_early_putc using iso_font via VA=PA while the bootstrap TTBR0 is live; disable before
     arm_vm_init's set_mmu_ttb(invalid_ttep) (arm_vm_init.c:2148).
  4. markers in arm_init after PE_init_platform, ml_parse_cpu_topology, cpu_bootstrap, kernel_startup_bootstrap,
     cpu_init, before arm_vm_init.
  5. panic hook at top of panic_trap_to_debugger: va_copy + _doprnt(fmt, &copy, sweet_early_putc, 16).
  Verify with tools/xnu-cc.py (compile+symbols) and patch-order simulation before the single CI run.

## Local WSL verification (2026-10-27)

- After Windows restart, Ubuntu-24.04 starts under WSL2 with custom kernel 6.18.40.1-microsoft-standard-WSL2+; /proc/filesystems includes hfsplus.
- Added D:\ios-sweet\LOCAL-BUILD.md with the IPSW verification, one-time DMG extraction, full rootfs build, and tweak-only repack commands.
- Ubuntu WSL archive is about 371 MiB; the D-backed ext4.vhdx currently occupies about 9.3 GiB.
- Apple IPSW download now resumes through aria2 with four HTTP range connections; at the 2026-10-27 10:51 checkpoint it was at 52% with about 6 h 47 min estimated remaining. `tools/download-ipsw-parallel.sh` resumes after a Windows restart.


## sweet_k6a device capture and touch patch (2026-10-27)
- Read-only root capture at D:\ios-sweet\research\sweet-k6a-live-capture-20261027 includes boot.img, dtbo.img, live FDT and checksums. FDT board-id 46/0; active GT9896 on 0xa84000:0x5d. Live regulator phandle resolves to pm6150l_l7, RPMh resource ldoc7, fixed 3200000 microvolts; raw coordinates 8639 x 19199.
- Added 0082-sweet-k6a-touch.patch. Opt in with XNU boot argument sweetk6a=1: votes ldoc7 at 3200 mV and divides Goodix coordinates by 8. Default sweet behavior is preserved. Patch application checked against reconstructed touch/rpmh files after all relevant preceding patches, including 0072. Not compiled or tested on hardware.
- Live FDT RAM reaches 0x27bb00000, but do not extend highmem yet: XNU bootstrap mapping, actual reserved areas and access restrictions require validation. Existing highmem profile is not proof of upper RAM usability.
- Local rootfs finished: D:\ios-sweet\artifacts\ios16-root-sweet-k6a-20H392-001.simg, SHA256 ffb1301154ba2669c2582c8541ca967946b48e387ea89c88d1ee3974bf26d240. HFS fsck passed. No claim that this constitutes a bootable device port; mobileactivationd container was absent during tweak step. Full XNU build still requires macOS workflow and credentials; no kernel was built or booted.

## Local shim preparation (2026-10-27)
- Device userdata is /dev/block/sda36, sysfs reports LUN 0 and 4096-byte logical/physical blocks, consistent with existing UFS driver assumptions. Data was read only.
- Installed WSL packages gcc-aarch64-linux-gnu, binutils-aarch64-linux-gnu, mkbootimg and lzfse on D-backed Ubuntu. Ubuntu mkbootimg lacks its gki module; official Android 14 generate_gki_certificate.py saved to D:\ios-sweet\tools\python\gki and PYTHONPATH selects it.
- Extracted original DTB from captured ColorOS boot.img and D22AP device tree from locally downloaded IPSW; generated shim/out/sweet-k6a.adt. Built diagnostic shim/out/shim-diagnostic-k6a.img, SHA256 94c7a7675e5197b93fc1922ff5f2a8fbf03858d104c5706a47dc815916760ce5. It contains no XNU kernel and has not been booted.
- tools/build-sweet-k6a.sh accepts a separately built SWEET kernel, produces ADT/payload/boot image with sweetk6a=1. Its read-write UFS root boot arguments require the intended iOS root on userdata; no flash or boot was performed. A kernel incorporating patch 0082 remains necessary; public upstream xnu-kernel artifact 12147422947 requires GitHub authentication and does not contain our patch.

## XNU build on user GitHub (2026-10-27)
- Live Android reports goodix_ts maximum coordinates 8639/19199, confirming DTB advertised input range. Android getprop spoofed locked/green, while captured kernel command line says androidboot.vbmeta.device_state=unlocked and verifiedbootstate=orange; verify directly in fastboot before relying on it.
- GitHub CLI installed in D-backed Ubuntu. User authenticated as nonrootus; branch codex/sweet-k6a-local pushed to their fork at commit 905d71af7f17716854ab577e81df9f51dbdc86db. XNU workflow run 40478936434 is in progress: https://github.com/nonrootus/ios-sweet/actions/runs/40478936434
- Diagnostic boot image was unpacked and embedded DTB matched source hash; ADT parsed fully and contains 63 product properties. No image has been booted on the device. To continue, inspect CI, download xnu-kernel artifact on success, then run tools/build-sweet-k6a.sh with the kernel; inspect failure logs and fix if needed. Do not flash userdata without explicit confirmation, per repo instructions.

- Read-only partition backups persist, modemst1, modemst2, fsg, fsc, vbmeta saved under D:\ios-sweet\backup\sweet-k6a-20261027; SHA-256 on device and PC matched each one. These contain per-device data and stay outside git. Boot and dtbo backups are in the capture directory.

- XNU run 40478936434 completed successfully; xnu-kernel artifact is 59,989,334 bytes compressed. Download to D:\ios-sweet\build\xnu-k6a-40478936434 started; verify its completion and build the boot image with tools/build-sweet-k6a.sh.

## First sweet_k6a XNU image and diagnostic boot (2026-10-27)
- XNU workflow 40478936434 succeeded on 905d71af7f17716854ab577e81df9f51dbdc86db. Artifact kernel.development.sweet saved under D:\ios-sweet\build\xnu-k6a-40478936434; SHA256 9513de342c2ddf894ea5c7c7f8090f00cab810f86217e1393ac8f0cbe7c3965a matches artifact manifest.
- Built D:\ios-sweet\src\ios-sweet\shim\out\shim-boot-sweet-k6a.img, SHA256 94a1b9c0794aaabd4af08e11a5756fb1b936209e2c11edca3a2eb8b5064d453a. Unpacked and verified SWEETXNU header, ten segments, sweetk6a=1, highmem 0x100000000 + 0xfcb00000, and embedded DTB identical to captured boot DTB. Not booted; root on userdata is currently Android data and kernel arguments enable UFS writes.
- Device entered fastboot: unlocked yes, product sweet, is-userspace no. fastboot boot shim-diagnostic-k6a.img returned OKAY; no partitions flashed. Waiting for user observation of screen, diagnostic should reset after ~3 minutes. Do not treat OKAY as proof shim ran successfully.
- User photo of diagnostic screen confirmed shim framebuffer works, UFS TUR/CAP/READ rc=0, GPT identified and userdata listed; read-only diagnostic succeeded. User requests proceeding directly to iOS. Before flashing userdata obtain explicit confirmation that Android user data will be erased (AGENTS.md requires confirmation of each destructive action). Boot and calibration backups exist; no backup of userdata. Rootfs and XNU image are prepared but XNU has not yet booted on this device.
- Additional read-only XNU probe built: shim/out/shim-boot-k6a-probe.img SHA256 86a3a27d755a359984b8cee4d3ba2df85d15bebd9c32bb8d19804128d4b08975; user requested direct iOS instead of probe. Do not confuse with final shim-boot-sweet-k6a.img.

## Root installed and first boot transport issue (2026-10-27)
- User explicitly authorized erasing userdata if no temporary full-iOS method. Confirmed fastboot unlocked yes, partition-size:userdata 0x38405fb000, max-download-size 805306368. Flashed D:\ios-sweet\artifacts\ios16-root-sweet-k6a-20H392-001.simg with fastboot flash userdata. All 16 sparse chunks returned OKAY, final exit 0, 385.020 seconds. Android userdata was replaced; boot and calibration partitions not flashed.
- fastboot boot shim-boot-sweet-k6a.img stalled on Sending, no OKAY. User reports phone remains on fastboot screen. Host fastboot devices initially empty during attempt, after interrupt shows ???????????? fastboot; requested USB reconnect. Kernel has not been confirmed transferred or started. Resolve transport before retry; do not repeat userdata flash.

- After user restarted fastboot with Power+Vol Down, USB serial <TARGET_SERIAL> reappeared. fastboot boot shim-boot-sweet-k6a.img returned Sending OKAY and Booting OKAY. Waiting for first XNU screen photo; iOS startup not yet confirmed.

## First-boot SIGBUS root cause (2026-10-27)
- User supplied partial transcription; complete SWEETLOG recovered read-only from userdata via installed recovery to D:\ios-sweet\research\sweet-k6a-live-capture-20261027\sweetlog-first-boot.txt. Kernel booted iOS launchd; SpringBoard and multiple daemons repeatedly SIGBUS in libobjc. Log shows Goodix 9896 responds and ldoc7 vote succeeded.
- SpringBoard slide=0x2beb0000, pc=0x1abf741a4, far=0x1adc69328. On local shared cache unslid PC=0x1800c41a4 is STR X8,[X0]; fault address unslid=0x181db9328 lies in read-only objc header table. Derivation: optimized image flag in local rootfs dyld_shared_cache_arm64.41.dylddata at file offset 0x76f460 is 0, whereas original SystemOS has image_info flags 0x48. This explains libobjc fallback treating a read-only cached header as mutable.
- Compared 44 dyld files in clean raw root with local SystemOS DMG; only .35 and .41.dylddata mismatch. Original .41 source sha256 eb9f190819f8b6974db2250dafa06fd67f83097995503f7a37e690cca2f048ca; .35 source sha256 328b405d252b770a4f0a40431b157cb4e6510eae4a11e45e40c7f5e5d43ac1bd. User requests continuing repair. Original root image remains intact, a separate repaired copy is being prepared. Local commit 8de3c4b adds repair tool; no reflash has been done.
- Limit WSL to 4GB and swap to 2GB on D in .wslconfig, at user request to prevent C space exhaustion. Never stage big images on C. A previous diagnostic patch 0083 was locally committed, but automatic approval review rejected pushing it to user GitHub. It is not needed for the identified image corruption.

## Repaired iOS image (2026-10-27)
- User asked to continue. WSL restarted with 4GB memory / 2GB swap on D. Finished a separate 16GiB raw copy D:\ios-sweet\build\raw\ios16-root-sweet-k6a-20H392-repair.img. Used tools/repair-dyld-cache.py to restore .35 and .41.dylddata in place preserving hard links. Both matched SystemOS SHA256 immediately and after unmount/remount; fsck.hfsplus -f -n reported volume OK.
- Created D:\ios-sweet\artifacts\ios16-root-sweet-k6a-20H392-repair.simg (12,145,201,660 bytes). Android sparse structure verified: 27,826 chunks, expanded size 17,179,869,184 bytes. Original raw and original sparse retained. Device remains in recovery; no repaired image written yet. Per AGENTS.md ask explicit confirmation before this new destructive userdata flash. The repaired image returns initial local rootfs state and discards changes made in the first iOS boot. Kernel 40478936434 from shim/out/shim-boot-sweet-k6a.img is unchanged and was built without diagnostic patch 0083.

- User explicitly confirmed reflash of repaired image. fastboot flash userdata ios16-root-sweet-k6a-20H392-repair.simg completed 16/16 OKAY, exit 0, 366.573s on 2026-10-27. Requested user restart fastboot via Power+Vol Down due previous post-flash ABL USB hang, then boot existing shim-boot-sweet-k6a.img and inspect.

- User restarted fastboot; fastboot boot shim-boot-sweet-k6a.img returned Sending/Booting OKAY on repaired root. Waiting for photo to determine whether objc SIGBUS is resolved.

- On repaired-root boot user reported SMP SpringBoard PC addresses and repeated exec fairplayd.H2/bluetoothd/xpcproxy. SMP is 90-second periodic sampler and confirms process existed at sampling, not necessarily healthy. No complete log/photo from this boot yet. Prepared shim/out/shim-boot-sweet-k6a-ui.img SHA256 7df1b6ad2b7404cc176b8d29101cd1eb11ad376e8509e1fab3b31ebd03fa1077, same kernel/root args plus sweetfb_noconsole=1, which hides console after first GUI swap. Not booted. Retrieve current SWEETLOG through recovery before rebooting into UI variant to avoid losing previous boot's ring.

- Repaired-root boot log captured read-only from recovery to D:\ios-sweet\research\sweet-k6a-live-capture-20261027\sweetlog-repaired-boot.txt (156579 bytes). Earlier repeated SpringBoard/backboardd SIGBUS absent; same SpringBoard PID 26 and backboardd PID 56 sampled repeatedly, FB swap 1..7 observed, GT9896 selected and actual touch coordinates/down/up logged. bluetoothd and fairplayd.H2 repeatedly exec; cause unknown. driverkitd terminated signal 9. Current image draws console over UI; next boot prepared shim-boot-sweet-k6a-ui.img with sweetfb_noconsole=1 to reveal first rendered frame. No success claim until screen seen.

- After capturing repaired-root log, booted shim-boot-sweet-k6a-ui.img via fastboot; Sending and Booting OKAY. Awaiting user photo to establish whether GUI is actually visible and responsive. No reflashing done.

- User reports Apple logo persists on UI image. Captured D:\ios-sweet\research\sweet-k6a-live-capture-20261027\sweetlog-ui-boot.txt: SpringBoard[26]/backboardd[56] sampled at 90s, no repeated SIGBUS, FB swaps 2-5; repeated bluetoothd/fairplayd.H2 launches, GT9896 active. Cause of Apple screen unresolved; activation container had been skipped at initial rootfs creation, but no proof it causes hang. Downloading official ipsw utility to symbolize stack. Built and booted shim/out/shim-boot-sweet-k6a-ui-6cpu.img SHA256 41be600f7c678038f8298b9b1384812bd7a60fcaa061c5606f70c5e59184bdb7, fastboot boot OKAY; user asked to let run 5 min.

- UI-6cpu boot log saved as sweetlog-ui6-boot.txt; 6/6 cores initialized SGI verified, SpringBoard[26] remains blocked in Launch Services at 3 successive samples. Symbolicated old UI sample using streaming .symbols parser: SpringBoard main stack waits in NSXPC synchronous reply -> LaunchServices database -> _LSCopyServerStore; lsd launched but was not included in sampler. Started shim-boot-sweet-k6a-lsd.img SHA256 788199ab3c37456e4ff3768a656a49995ead8c5e914c51b77b6ff31ec722813d with sweetsample=SpringBoard,backboardd,lsd,containermanagerd,installd after capturing log; fastboot boot OKAY. Wait at least 90 seconds then recover log and symbolicate lsd. ipsw a2s OOM under 4GB WSL; streaming nlist parser uses much less memory.

- Diagnostic log sweetlog-lsd-boot.txt recovered in recovery, 137706 bytes. lsd PID 100 sampled: thread 3 waits for database seeding; thread 2 waits on dispatch semaphore during MobileInstallation identity / built-in app install session setup. This narrows the bottleneck but does not establish the cause; symbolication uses nearest shared-cache symbols and is approximate. No installd sample appeared; log has exec containermanagerd but sampler output only lsd, SpringBoard and backboardd. Virtual random failure is present, causality unproven. Phone remains in recovery, adb serial <TARGET_SERIAL>.

- Mapped lsd thread 2 wait addresses 0x19c57c4bc, 0x19c57c6e8 and 0x19c57c0f8 (unslid) to libMobileGestalt.dylib using dyld image mapping; disassembly confirms semaphore wait at 0x19c57c4b8. Earlier nearest-symbol assignments within this range were misleading. MobileGestaltHelper exec appears in log; its connection to the semaphore is unproven. Built shim/out/shim-boot-sweet-k6a-mg.img SHA256 315a9aa59f4662fd388562005d16f6bf4371b86f6aec63955581842b82a97b97 with lsd/MobileGestaltHelper samples; fastboot boot succeeded. Wait at least 90 seconds, recover SWEETLOG and inspect helper samples. No flash performed.

- Recovered sweetlog-mg-boot.txt from recovery, 137259 bytes, flush 17. lsd again blocks at same libMobileGestalt semaphore; another lsd thread sampled inside libMobileGestalt callback at unslid 0x19c57c558 with CFRunLoop stack. MobileGestaltHelper executed but did not appear in sample (both full and 15-character names selected), so it may have exited or its process name differed; not proof of failure. The saved initial raw image contains installd binary and launchd plist, but the live userdata has not been inspected for these. ipsw disass under 1.8GB virtual-memory cap failed to allocate; do not repeat OOM-prone a2s. Phone remains in recovery. No fix established; next determine exact blocking callback and helper lifetime before changing image or kernel.

- Analyzed lsd MobileGestalt wait: 0x19c57c0dc references IONetworkController, block waits for matching IOService via run loop and semaphore. At 0x19c57c55c timeout result 4 loops until a matching service appears. Built experimental candidate on D: raw ios16-root-sweet-k6a-20H392-mg-timeout.img and sparse artifacts/ios16-root-sweet-k6a-20H392-mg-timeout.simg; patched only cache .09 offset 0xe2455c bytes e0000054 -> 00050054 (timeout branch exits wait). Applies to any user of this helper, is experimental and does not implement networking. Source root image unchanged. fsck.hfsplus -f -n passed, patched bytes verified on read-only remount, sparse structure 27826 chunks, expanded 17179869184 bytes, sparse 12145201660 bytes. No phone write yet. Flashing candidate userdata resets all changes from prior iOS boots: obtain explicit user confirmation per AGENTS before flash; recovery and partition backups retained.

- User explicitly authorized writing experimental mg-timeout image to userdata. fastboot flash userdata completed all 16/16 chunks OKAY, 366.448s, exit 0. Next boot shim/out/shim-boot-sweet-k6a-mg.img temporarily; if fastboot USB hangs after large flash, user must restart fastboot with Power+Vol Down, then inspect screen and collect log after >=90 s. Patch remains unproven on hardware.

- After successful mg-timeout flash fastboot boot initially hung Sending. User restarted fastboot; shim-boot-sweet-k6a-mg.img then booted with Sending/Booting OKAY. Waited more than 90 s. User asked to report display and enter fastboot; currently neither ADB nor fastboot detects device, awaiting user. Need boot recovery and capture log before next XNU boot; compare lsd semaphore sample and screen. Fastboot OKAY alone does not prove iOS success.

- User reported Apple logo on mg-timeout image. Recovered sweetlog-mg-timeout-boot.txt: 3 samples, lsd still in same semaphore / CFRunLoop path; timeout branch patch did not resolve the stall. Decoded dyld shared stub 0x1a2593260 -> 0x186ec9fe8 _CFRunLoopRunInMode from CoreFoundation export symbols; sampling remains inside CFRunLoopRunInMode, before timeout branch. Prepared second experimental sparse copy artifacts/ios16-root-sweet-k6a-20H392-mg-nowait.simg; HFS FIBMAP maps cache .09 offset 0xe24544 to raw 0x23e6d7544 and sparse file offset 0x22c426920, original 684240b9 -> 2e000014 (branch to callback cleanup at 0x19c57c5fc before running event loop). Existing timeout patch remains. Code path generic to this MobileGestalt helper, not a network driver, may have side effects. Sparse structure verified, 27826 chunks and expanded 17179869184 bytes. Userdata has NOT been flashed with second candidate; obtain explicit confirmation before each destructive flash. Phone currently in recovery.

- User explicitly approved second experimental userdata flash. fastboot flash userdata ios16-root-sweet-k6a-20H392-mg-nowait.simg completed 16/16 OKAY in 370.832s. Await fastboot restart due repeated post-flash USB hang, then temporarily boot shim-boot-sweet-k6a-mg.img, observe screen and retrieve log. No success claim yet.

- After successful nowait userdata flash user restarted fastboot; temporary fastboot boot shim-boot-sweet-k6a-mg.img returned Sending/Booting OKAY. Waited >90s; requested user report screen and return to fastboot for SWEETLOG. Neither fastboot nor ADB currently detects the running device. Need retrieve log before rebooting another XNU image; result not yet established.

## User reports iOS interface reached (2026-10-27)
- User reports after booting nowait userdata with shim-boot-sweet-k6a-mg.img that the system launched and applications can be opened, but it lags. This is user-reported; no photograph or post-boot diagnostic log captured. Previous request to enter fastboot superseded: do not interrupt current live session without coordinating. The nowait MobileGestalt patch is the change under test; it may have contributed but causality not yet proven. No claims about graphics acceleration, hardware compatibility, activation, or stability. Next investigate lag from existing logs and code without rebooting, preserving live user session; collect new log later with user coordination.

## sweet_k6a GPU investigation (2026-10-27)
- User reports the nowait image reaches iOS and opens applications but is laggy; requests GPU acceleration. Preserve the live session. Added read-only tools/gpu-dt-info.py and docs/sweet-k6a-gpu.md. Verified parser against captured live FDT: GPU qcom,chipid 0x06010800, GPU register window 0x05000000/0x40000, GPU SMMU 0x05040000/0x10000, GPUCC 0x05090000/0x9000, GMU 0x0506a000/0x31000, firmware node names a615_zap. These are DT descriptions only, not powered MMIO observations. Mesa Freedreno/Turnip are Linux/GL/Vulkan driver references, not an existing iOS Metal driver. No GPU code run, no acceleration implemented, performance cause unmeasured. Next inspect firmware, power and SMMU requirements and design opt-in probe before GPU command submission.

- GPU power tracing: expanded tools/gpu-dt-info.py to resolve supply phandles, and verified captured FDT identifies GPU CX GDSC at 0x0509106c parent pm6150l_s2_level and GX at 0x0509100c parent pm6150_s2_level. These are DT values, not proof powered. Listed original boot ramdisk with cpio: no firmware/a615/a618/gmu/adreno/kgsl/gpu filename matches, other partitions remain unexamined. Linux A618 legacy GMU uses flat firmware <=0x8000; SM7150 reference names a618_gmu.bin and a615 zap. Asked user whether current iOS session may be interrupted to inspect Android partitions read-only through recovery. No GPU hardware access or acceleration enabled.

- User requested GPU acceleration. Downloaded two reference files only from kernel.org linux-firmware qcom to D:\ios-sweet\research\gpu-reference-firmware: a630_gmu.bin (32768 bytes, SHA256 da8d9b1b1f5c1a0b311f32567093b4828f3c80031dd8435f91ac13c664e173a6) and a630_sqe.fw (34188 bytes, SHA256 1c21b527d9183487cc550dabbb3f43e555df5a977a461934fc61f0635a9aa90c). Added tools/a618-firmware-check.py; Linux test skips first 4 SQE bytes, reference passes version and size checks. These are NOT verified compatible with this phone and have not been loaded. GPU driver/Metal acceleration unimplemented. Preserve live iOS; user has not yet answered request to interrupt session and read Android partitions for device-specific firmware.

## Device GPU firmware and ios-alioth comparison (2026-10-27)
- User approved interrupting iOS for read-only recovery inspection. Mounted /dev/block/mapper/vendor ext4 ro,noload and modem vfat ro; found and copied vendor/firmware/a618_gmu.bin, a630_sqe.fw, a615_zap.b00/b01/b02/elf/mdt to D:\ios-sweet\research\sweet-k6a-gpu-firmware-20261027; all seven host SHA256 matched device. GMU 32768 B and SQE 32136 B pass offline version/size checks; no GPU code or firmware loaded. Unmounted both and fastboot boot shim-boot-sweet-k6a-mg.img returned OKAY to restore iOS.
- Before restarting saved sweetlog-nowait-working-boot.txt (580825 B): lsd samples no longer show prior MobileGestalt semaphore stack; framebuffer records >16000 swaps; assetsd repeatedly SIGABRT, cause unknown. User observed working iOS before recovery; new boot not yet visually confirmed.
- User supplied https://github.com/MrMoxing/ios-alioth and a screenshot claiming graphics fixed in a newer version. The repository main README and its handoff report Adreno 650 initialization but no working GPU, reset at CP_SQE_CNTL=1; GitHub API on 2026-10-27 reports only main branch and no releases. Screenshot may refer to newer code elsewhere; user asked for its URL. Do not conflate graphic glitch fixes with proven GPU acceleration. Downloaded redwood_adreno.c and redwood_gpu_layout.h from that main branch to D:\ios-sweet\research\ios-alioth-reference; it supports A650/A660, assumes newer block-format GMU firmware and different SoC addresses. A618 needs flat legacy GMU loading and different GPU, SMMU, power, clock maps, so do not run this driver unmodified. Source is helpful to study, not acceleration on this device.

- Started an actual offline A618 driver component at xnu/gpu/sweet_a618_firmware.{c,h}: freestanding validation and buffer views for legacy flat GMU and a630 SQE (skip 4-byte header, Linux version check). Test xnu/gpu/sweet_a618_firmware_test.c passed with captured a618_gmu.bin and a630_sqe.fw and negative cases; ARM64 freestanding gcc compile passed. The module is not integrated into XNU, does not load firmware or touch hardware, and is not graphics acceleration. User has been asked for link to newer ios-alioth release; current main supports A650/A660 and not A618. No iOS session interruption in this turn.

- Found ios-topaz (https://github.com/MakrSas/ios-topaz), an ios-sweet fork reporting UI rendered on A610 through Mesa. Downloaded select sources to D:\ios-sweet\research\ios-topaz-reference: patch 0901 RedwoodGPU + TopazGpuW, 0905 embedded firmware patch, Mesa Darwin glue and redwood-drm. Source credits HackiOS APSL kernel and MIT userland. Its IOKit RedwoodGPU / userland MSM translation is a promising integration reference. Topaz A610 uses GMU wrapper and different address/clock/power map; A618 uses legacy full GMU, so hardware init cannot be copied unmodified. No proof or device test for sweet_k6a yet.

- Added xnu/gpu/sweet_gpu_va.{c,h}: bounded 64 KiB-aligned first-fit GPU virtual-address reservation helper with overflow checks and unmatched/double-free rejection; caller provides window and locking. It does not map memory or program SMMU. Test sweet_gpu_va_test.c compared 30000 randomized allocations/frees against an independent bitmap, passed under ASan/UBSan; freestanding ARM64 cross-compile passed. No XNU integration, GPU bring-up or acceleration yet.

- Offline inspected captured a615_zap.elf: ELF32 little-endian DSP6, entry 0x5000, 3 headers; b00/b01/b02 match ELF slices at 0, 0x1000, 0x3000; MDT equals b00+b01. Byte comparisons only, signature/authentication not tested. No GPU MMIO or TrustZone access performed.

- Added offline xnu/gpu/sweet_gpu_pte.{c,h} descriptor/index encoder for proposed 4KB, 32-bit GPU VA and 36-bit PA stage-1 layout (MAIR attr0=0x44, outer-shareable from topaz reference). This is unverified for sweet_k6a: no context-bank discovery, memory ownership, cache sync, TLB invalidation or hardware access. Boundary tests passed under ASan/UBSan and ARM64 freestanding compile passed. GPU remains unstarted.

- Prepared 0084-sweet-k6a-gpu-bus-probe.patch, opt-in only with sweetk6a=1 and sweetgpuprobe=1: maps GCC page and reads only clock CBCR at 0x00171004 (Qualcomm gcc-sdmmagpie); no GPU/GPUCC access or writes. git apply --check passed on 40478936434 saved XNU build tree; ARM64 syntax compile with minimal stub headers passed. Not compiled against actual XNU, full kernel not built, not run. This is diagnostic, not GPU acceleration. Earlier automatic review rejected pushing unrelated patch 0083; do not push it or bypass that rejection. Live iOS has not been interrupted in this turn.

- Prepared clean build branch codex/gpu-k6a-probe at 983939f5022b3e5ddf2a2c9d379bdadcb4764097 on nonrootus/ios-sweet, from already-pushed 905d71a. Branch contains only new opt-in 0084 GPU GCC bus probe; rejected unrelated 0083 is not present. GitHub Actions run https://github.com/nonrootus/ios-sweet/actions/runs/40535344803 queued. Windows worktree at D:\ios-sweet\build\gpu-k6a-probe-worktree; WSL cannot use its Windows-style .git pointer, use main repo commit ref as needed. Do not confuse CI success with hardware test. After success download kernel to D, build temporary image with sweetgpuprobe=1 and existing working root args, then coordinate reboot to fastboot and read result via recovery.

- Added offline xnu/gpu/sweet_gpu_pm4.{c,h} type-7 PM4 encoder and A6xx CP_ME_INIT sequence generator; independent parity/size tests pass under ASan/UBSan and freestanding ARM64 compile. Not connected to ring or hardware. GPU not initialized, and no claim of acceleration. GitHub run 40535344803 for opt-in GPU bus probe is still queued; no duplicate triggered.

- Added offline xnu/gpu/sweet_gpu_tables.{c,h}, with caller-provided aligned table pages, map/unmap, invalid descriptor rejection and failed-allocation rollback. Tests with fake pages pass under ASan/UBSan and ARM64 freestanding compile. No ownership enforcement, locking, cache sync, TLB invalidation, context setup or hardware access; proposed 32-bit IOVA / 36-bit PA still unverified for sweet_k6a. CI GPU-probe run 40535344803 remains queued as of latest check.

- GitHub Actions run 40535344803 attempt 1 completed failure; job 122298989103 was cancelled without any steps because GitHub could not acquire a hosted macOS ARM runner, annotations explicitly state capacity constraints. Retried failed job (attempt 2); inspect run before any further retry. This is not a source compilation result. GitHub says macos-14 image retires 2026-11-02; our XNU build currently requires Xcode 15 iig, so switching to newer images is not yet validated.

- Added tools/pack-gpu-fw.py and built D:\ios-sweet\research\sweet-k6a-gpu-firmware-20261027\gpu-firmware.bundle (81920 bytes) from four phone-owned firmware files. Round-trip compared bytes and hashes; corrupted-byte negative test rejected. Existing mkpayload.py --ramdisk and IOFindBSDRoot can create a RAM memory device while rd=ufsroot0 remains root, but this bundle has no kernel reader and has not been boot-tested. Intended to avoid another 12GB reflash for firmware changes; no firmware or GPU code executed on hardware.

- Built temporary shim/out/shim-boot-sweet-k6a-gpu-fw-test.img SHA256 ed09cb0ea146ffc426961839f55e116fc11dd7665e0962c9cffc506f99050532 with existing kernel and 81920-byte firmware bundle as RAMDisk, retains rd=ufsroot0. Build output only: not booted, no reader integrated, no verified contents on device. Added offline xnu/gpu/sweet_gpu_bundle.{c,h}: bounded format reader provides data and stored hash views but does NOT verify hashes or signatures. Test with real bundle and malformed entries passed ASan/UBSan and ARM64 compile. GitHub 40535344803 retry remained queued on latest check.

- Prepared 0085-sweet-gpu-bundle-probe.patch: optional sweetgpubundle=1 checks only RAMDisk length and SWEETGPU magic in IOFindBSDRoot and reports presence; contents/signatures unverified, no GPU access. git apply --check passed on saved XNU tree. Not yet compiled against XNU or tested on hardware, not on CI branch. GitHub run 40535344803 retry still queued.

- Since GPU probe run 40535344803 remained queued, created separate branch codex/gpu-k6a-macos15 commit c938f4771b79000c88b789bf1cdfa22b076c02a6 (same probe with runner changed macos-14 -> macos-15), pushed to nonrootus and started Actions run https://github.com/nonrootus/ios-sweet/actions/runs/40546258128. macOS 15 has only Xcode 16+, known iig ABI incompatibility, so this is explicitly an experiment to obtain real diagnostics, not a validated kernel. Original run remains queued. No device flash/boot.

- macOS 15 experiment Actions run 40546258128 succeeded, all steps success. Downloaded xnu-kernel artifact (~60.6 MB) to D:\ios-sweet\build\xnu-gpu-probe-40546258128 and verified SHA256SUMS; built temporary shim/out/shim-boot-sweet-k6a-gpu-probe.img SHA256 b1b8de022f47a177ec4f665f12a6b7b686cbae37b6276c53b5093e3806162be5, cpus=6 sweetk6a=1 sweetgpuprobe=1, current UFS root, no ramdisk. No device boot yet. Kernel is a GCC-bus read-only probe only, no GPU acceleration. Before test user must switch current iOS to fastboot, then fastboot boot temporary image; recover log after observation. Previous working shim-boot-sweet-k6a-mg.img retained.

- User entered fastboot. Temporary fastboot boot shim-boot-sweet-k6a-gpu-probe.img returned Sending/Booting OKAY; waited >75 sec. Requested screen observation and fastboot to recover log. Not yet known whether new kernel reached userspace or whether probe ran. Next boot recovery, copy log before next XNU boot and inspect SWEET GPU line. No flash.

- User observed iOS loaded on gpu-probe image but lag remained. Captured sweetlog-gpu-bus-probe.txt: SWEET GPU cfg AHB CBCR 0x00000001, not reported off; no GPU registers touched. This validates diagnostic read, not GPU readiness. Device now in recovery. Added opt-in bundle magic probe 0085 to macOS15 CI branch commit 677b156e80c59e1b5aef8fec9f1def05667cfe03; Actions run https://github.com/nonrootus/ios-sweet/actions/runs/40549785257 in progress. On success verify artifact, build temporary image with GPU bundle using --ramdisk and sweetgpubundle=1, retain rd=ufsroot0; test and recover log. No user data reflash needed.

- CI 40549785257 completed success; downloaded artifact to D:\ios-sweet\build\xnu-gpu-bundle-40549785257 and sha256sum -c passed. Built temporary shim/out/shim-boot-sweet-k6a-gpu-bundle-probe.img SHA256 787084b891aa5d33d6ffacb9d7ec2814d94798411319f17d3156afc9857c3f7c, with RAMDisk bundle (0x14000 bytes), rd=ufsroot0, sweetgpuprobe=1 sweetgpubundle=1. From recovery used adb reboot bootloader and fastboot boot returned Sending/Booting OKAY. Waiting for user screen observation and fastboot to fetch log. Probe checks magic only, no hash/signature validation, GPU remains unstarted; no partition flash.

- User reports iOS booted on GPU-bundle-probe. Captured sweetlog-gpu-bundle-probe.txt: bundle magic found 81920 bytes, cfg AHB CBCR 0x00000001, UFS root and SpringBoard start. Confirms package presence and boot, not content verification, GPU initialization or acceleration. Prepared 0086-sweet-gpu-bundle-validate.patch integrating offline bundle layout and A618 GMU/SQE version checks into XNU, opt-in sweetgpucheck=1. Patch independently git apply --check passed but has not yet been checked sequentially with 0084/0085, compiled, tested or pushed. User requests fewer repetitive build/boot cycles: batch remaining integration and checks before another device test. Phone currently in recovery.

- Sequential validation caught 0086 context conflicts with 0084/0085 in bsd/conf/files and IOKitBSDInit.cpp. Rebuilt 0086 against sources after applying 0084 then 0085 in a small temporary tree; git apply --check now passes in sequence. Still no XNU compile or hardware test; batching work as user requested.

- In response to user request to batch work, pushed GPU validation patch 0086 on macOS15 branch e9d53a71714e032892db93ffb46662b14109c570; CI https://github.com/nonrootus/ios-sweet/actions/runs/40553230450 queued. Not requesting device reboot while compiling. Continued comparing legacy A618 GMU against Linux: legacy OOB bits, flat ITCM firmware, HFI v1 and manual SPTPRAC differ from A650/A610; power-on code remains unimplemented. GPU acceleration not working.

- Applied 0084/0085/0086 sequentially to a minimal test tree. Combined bsd/dev/sweet_gpu_firmware.c ARM64 freestanding compile against stub kernel headers passed. Host ASan/UBSan wrapper test accepted actual firmware bundle and rejected bad magic; intentionally corrupting GMU content remains accepted, confirming contents/hashes are NOT authenticated. No hardware use. CI 40553230450 queued.

- Added offline xnu/gpu/sweet_hfi_codec.{c,h}: HFI command header encoder and bounded ACK response parser, with host unit test passing ASan/UBSan and ARM64 freestanding compile. References Linux a6xx_hfi.h and a6xx_hfi.c protocol definitions; A618 legacy queue IDs 0/4/5 differ from newer devices. ACK id/type assumptions remain unverified against this device; no queue, DMA barriers, firmware startup, XNU integration or GPU access implemented. Phone remains in recovery. CI 40553230450 status check failed due TLS handshake timeout; no conclusion available.

- Extended tools/gpu-dt-info.py to report speed-bin GPU power levels and GMU power levels from captured FDT. Verified five GPU bins (0, 172, 146, 128, 167), with initial frequencies 180 MHz for first four and 140 MHz for bin 167; GMU levels 0 and 200 MHz. Active chip speed bin and ARC votes remain unknown, so these are device-tree data, not validated operating settings. No hardware access. CI 40553230450 is in progress, Build step running.

- Recovery sysfs and dmesg read without writes saved to D:\ios-sweet\research\sweet-k6a-live-capture-20261027\recovery-gpu-observations.txt. Android recovery reports Adreno618v1, frequency list 180/267/355/430/565/650/800 MHz, default pwrlevel 6, current 180 MHz. GPU SMMU reports non-coherent table walk (firmware override) and five stream matching register groups, making explicit page-table cache maintenance essential for any future XNU integration. The active speed-bin identity remains undetermined; recovery values are not proof of iOS driver operation. CI 40553230450 Build completed successfully; packaging/upload still in progress at last check.

- CI run 40553230450 completed success including Build. Artifact xnu-kernel is 60,572,720 compressed bytes; download to D:\ios-sweet\build\xnu-gpu-validation-40553230450 initiated, checksum verification pending. No GPU hardware test requested for this validation-only change.

- Added offline xnu/gpu/sweet_hfi_ring.{c,h} legacy v1 ring copy and length validation, with wraparound, full, incomplete and malformed-message tests passing ASan/UBSan and ARM64 freestanding compilation. It only operates on caller memory and is NOT a live HFI queue: synchronization, DMA cache maintenance, index publication, signaling, GMU startup and hardware integration are absent. No device interaction from this code. Kernel artifact download still pending.

- Prepared 0087-sweet-gpu-bundle-sha256.patch using XNU SHA256 APIs. Host wrapper linked to OpenSSL accepted the real bundle and rejected modified payload/magic; git apply --check passed on extracted 0086 source. Hashes only check corruption and do not authenticate firmware. Not compiled against XNU, not run on device or pushed. User asks focus on actual GPU driver bring-up rather than more ancillary checks. Artifact download is in progress (41 MB observed at last check).

- CI 40553230450 artifact download finished to D:\ios-sweet\build\xnu-gpu-validation-40553230450; sha256sum -c SHA256SUMS reports kernel.development.sweet OK. It contains 0086 bundle validation, not 0087 or an A618 GPU driver. No test boot performed. Existing sweet_rpmh code supports touch VRM ldoc7/ldoc11 only; it cannot vote GPU ARC power domains. Linux A618 GMU startup uses power-domain and clock enable, 200 MHz GMU clock, then GMU firmware/HFI; these dependencies must be implemented before any GPU register access. Topaz RedwoodGPU service requires a functional backend and must not be advertised prematurely.

- Recovery regulator sysfs read-only snapshot: gpu_cx_gdsc and gpu_gx_gdsc both disabled and num_users=0 when idle. gpu_cx_gdsc consumers include GPU, SMMU and GMU; gpu_gx_gdsc consumers include GPU and GMU. Parent pm6150l_s2_level is enabled with one user and shared with GCC and other blocks; pm6150_s2_level disabled with zero users. Reported microvolts values are regulator level encodings, not physical voltages. This is recovery state only; it does not establish iOS startup state or a safe write sequence.

- Prepared 0088-sweet-gpu-rpmh-arc.patch adding sweet_rpmh_gpu_arc_info to existing XNU RPMh source. Reads only raw command-db ARC address and 16-bit aux levels for cx.lvl/gfx.lvl, validates bounds/type, serializes using existing lock; does not issue votes or enable GPU. Live FDT confirms these resource names. A synthetic command-db test under ASan/UBSan passed, as did ARM64 freestanding compile against stub headers and git apply --check against saved 40478936434 tree. Host test harness at D:\ios-sweet\build\gpu-arc-work; not compiled against real XNU, not pushed, and not tested on device. Further work: decode platform ARC levels, implement shared resource vote aggregation and correct power/clock sequence, integrate GMU startup and SMMU with cache maintenance. GPU acceleration remains unavailable.

- Added 0087 and 0088 to existing clean macOS15 CI branch commit 7fc67d5e7e0eb17b5976089130e454f272a28489 and pushed to nonrootus/ios-sweet. Initial push to origin dipa-studio failed 403 (not authorized there); successfully pushed to the previously used user fork. Started workflow https://github.com/nonrootus/ios-sweet/actions/runs/40563832588; queued. These patches do not start GPU. No device test or flash.

- CI run 40563832588 completed success for 0087 and 0088, including XNU Build; no hardware test. Phone <TARGET_SERIAL> is attached in recovery as of 2026-10-28. Attempted read-only debugfs mount in temporary recovery directory to inspect ARC command database; recovery kernel reports No such device (debugfs unavailable), empty temporary directory removed. ARC lookup is built but not invoked, no GPU power vote or bring-up implemented; don't schedule a boot solely for this diagnostic.

- Prepared 0089-sweet-gpu-rpmh-select.patch on top of 0088: maps a requested consumer level to an ARC table selector with +1 encoding, ignores trailing zero padding and rejects malformed order or unsupported levels. Conservative policy refuses selector zero. Host synthetic command-db tests passed ASan/UBSan, ARM64 freestanding compile with stub headers passed, patch apply --check passed. Uses cx.lvl/gfx.lvl lookup but sends no vote, has no caller, and is not built against real XNU or tested on hardware. Shared resource aggregation, actual ARC writes and clocks remain unimplemented; GPU acceleration unavailable. Reference Qualcomm rpmh-regulator.c from Android source for level encoding.

- Prepared 0090 and 0091 on top of 0088/0089: refactors existing RPMh TCS sender for one or three commands (retains touch voltage/mode/enable order), and adds experimental ARC raise-only function using a caller-supplied verified baseline. Emulated register tests checked one-command ARC and three-command touch transactions, cleanup and no-lowering; ASan/UBSan and ARM64 stub cross-compile passed; patches 0089/0090/0091 apply sequentially. Test harness is under D:\ios-sweet\build\gpu-arc-work. No actual XNU build or device execution; API has no caller. Baseline and coordination of ALL shared-resource writers are unverified, no safe release/sleep vote handling exists, so never invoke on hardware until resolved. No GPU boot or acceleration.

- Pushed 0089/0090/0091 in CI branch commit 533e2c303371c551f1b21dd55c9f7db0be8f8298; run https://github.com/nonrootus/ios-sweet/actions/runs/40637536404 in progress. Prepared 0092-sweet-gpu-rpmh-read.patch for one-command RPMh reads using response-data offset 0x40 (pre-v3 layout) and read message ID; checks response against ARC aux table, no caller and no hardware test. Qualcomm says RPMh read returns this DRV vote, not globally aggregated rail state. Mock transaction/read/write and invalid-response tests passed ASan/UBSan, ARM64 stub cross-compile and patch apply --check passed. Do not combine a read and an independent write without serializing all relevant APPS DRV clients, and do not treat its response as rail voltage; outstanding firmware, clocks, SMMU and graphics driver remain unimplemented.

- Prepared 0093-sweet-gpu-rpmh-zero-baseline.patch: ARC raise primitive now distinguishes verified selector 0 from an unknown baseline and validates selector against command-db levels. On synthetic register model, read/raise and zero/invalid baseline tests passed ASan/UBSan, ARM64 stub compile and sequential application of 0089-0093 passed. Neither read nor raise is invoked on device; concurrency with other APPS DRV clients, actual level, power-domain sequencing and recovery are unresolved. CI 40637536404 remains in Build for 0089-0091; 0092/0093 not on its branch.

- Prepared 0094-sweet-gpu-rpmh-checked-raise.patch: under rh_lock, read APPS DRV vote, validate selector, refuse unexpected external vote changes, and only raise. Simulated RPMh tests covered zero initial vote, raise, repeated no-op and external-change rejection; ASan/UBSan and ARM64 stub compile passed; patch applies after 0093. This is experimental and has no caller, not real XNU compiled or device-tested. Other writers not using rh_lock can still race; global aggregated voltage is not visible through this read and release/sleep handling remain absent. Never run this on hardware before resolving shared ownership and power sequence.

- From captured FDT: GX GDSC at 0x0509100c has domain-addr phandle 0x05091508, sw-reset 0x05091008, force-enable-root-clk and reset-aon-logic; CX GDSC at 0x0509106c has hw-ctrl-addr 0x05091540 and 500us timeout. These are descriptions, not permission or proof safe for MMIO. Qualcomm GDSC binding documents GX root-clock and AON reset sequencing. Previously saved gpucc-sdmmagpie reference reports 750/780 MHz max, while recovery driver reports 800 MHz; a later Qualcomm branch differs, so select reference version consistent with actual device rather than assuming old clock table. No GPU/GPUCC register access performed.

- CI 40637536404 succeeded for 0089-0091; no hardware test. Added 0092-0094 to CI branch commit aff2bf3f30b0baec3dd4d660702c100d679e9797 and started https://github.com/nonrootus/ios-sweet/actions/runs/40638321198 (in progress). Qualcomm downstream GDSC driver confirms reset-aon toggles domain bit 4, then clears clamp bit 0 before clearing SW_COLLAPSE; FDT also requires forced root clock. These source observations are not sufficient to issue MMIO: actual clock ownership, baseline votes, CX readiness and failure cleanup remain unresolved.

- Prepared xnu/gpu/sweet_gpu_gdsc.{c,h}, tests, and 0095-sweet-gpu-gx-gdsc.patch for a guarded GX GDSC enable sequence using callbacks, per captured FDT and Qualcomm register definitions. Root-clock acquisition, existing ON/HW-control rejection, resets, unclamp, collapse clear, bounded 100us polling and retaining root clock on uncertain failure were exercised against a fake register model; ASan/UBSan and ARM64 freestanding compilation passed; patch applies to minimal post-0086 conf. The code is NOT connected to hardware or boot, no XNU build or device execution. Requires caller to ensure parent rails, GPUCC bus, clock ownership, synchronization, memory retention and safe cleanup before use; tests cannot establish those preconditions. GPU still unstarted.

- Corroborated root clock in live FDT: GPUCC clock id 18 matches GPU_CC_GX_GFX3D_CLK_SRC in Qualcomm's later sdmmagpie 4.14 header; source root command register 0x101c and 800 MHz entry match the observed runtime table better than old reference. Saved the two small reference files on D under research/sdmmagpie-clock-reference. Added 0096-sweet-gpu-gx-root-clock.patch and source helpers to acquire/release RCG force-enable while preserving a preexisting force bit; modeled success, borrowed, and timeout cases passed ASan/UBSan and ARM64 stub compile; patch apply check passed after 0095. No hardware access or real XNU build; PLL/parent readiness, clock ownership, CX power, failure recovery and integration remain prerequisites. No GPU acceleration.

- Prepared 0097-sweet-gpu-cx-gdsc.patch: callback-based CX enable clears SW_COLLAPSE at GPUCC+0x106c, polls FDT-referenced hardware status GPUCC+0x1540 up to 500 us, refuses already-on or HW-controlled state and does no rollback on uncertain timeout. Synthetic fake-register success/already-on/timeout tests passed ASan/UBSan; ARM64 freestanding compile and patch apply check passed. No boot/hardware access or XNU build; parent voltage, bus, clock ownership and safe integration still needed. 0095/0096 staged on CI worktree commit 3d42c13 but not pushed while previous build runs.

- CI 40638321198 succeeded for 0092-0094. Pushed 0095-0097 in CI branch commit 8211cb3c7bf48782a39f8dc4ce9ab6f7301a49ee; https://github.com/nonrootus/ios-sweet/actions/runs/40639250560 in progress. Prepared 0098-sweet-k6a-gpu-power-bridge.patch and xnu/gpu/sweet_gpu_k6a_power.{c,h}: real MMIO callback wiring with whitelist, ARM barriers, explicit caller-supplied mapping/delay, CX then GX/root sequence, and no automatic retry after uncertain failure. Synthetic fake-register integration tests and ARM64 freestanding compile passed; patch apply --check passed. This code HAS NO CALLER, no device test or XNU build. Parent rails, GPUCC bus, parent clocks, global ownership, retention, failure recovery and GMU initialization remain unverified; no boot hook or safe runtime use. Power-domain success would still not mean graphics acceleration.

- Prepared 0099-sweet-gpu-firmware-store.patch on top of 0087: when sweetgpucheck=1, IOFindBSDRoot validates SHA-256 over bounded, kernel-owned copies of all four bundle files, validates A618 GMU/SQE format and publishes immutable views to future driver callers. No caller loads firmware into GPU; hashes do not authenticate contents. Host test with actual 81920-byte device bundle passed ASan/UBSan for corrupt-before-publish, successful copy, post-copy source mutation and invalid index; ARM64 freestanding compile using SHA stubs passed; patch applies to post-0087 source. Not XNU-compiled or device-tested. No large rootfs write or download.

- Prepared 0100-sweet-gpu-gmu-legacy-load.patch and sweet_gpu_gmu.{c,h}: for A618 flat legacy GMU firmware, checks CM3 is held in reset, then writes up to 0x8000 bytes across GMU window offsets 0x3000..0xafff using caller-provided MMIO operations, never releases reset. The 32KiB region spans the 16KiB ITCM and 16KiB DTCM windows; do not describe it as 32KiB ITCM alone. Tested with actual extracted a618_gmu.bin against fake register memory, including reset rejection, partial write failure and size checks; ASan/UBSan, ARM64 freestanding compile and patch apply check passed. Not connected to firmware store or hardware, no XNU build/device test. Parent power, clocks, SMMU/HFI queues, reset ownership and failure recovery must be established first; no GPU acceleration.

- Prepared 0101-sweet-k6a-gmu-loader-bridge.patch connecting the kernel firmware-store API to legacy GMU loader through bounded MMIO callbacks. Rejects absent power-domain success, unset caller clock-verification flag, missing firmware, bad mapping or CM3 not held in reset; never starts GMU. Host simulated power + firmware load, failed clock gate and reset rejection passed ASan/UBSan; ARM64 freestanding compile and patch check passed. Has no runtime caller, clock flag is an assertion from the future caller NOT hardware verification, and the code is not XNU-compiled or device-tested. Power, clock parents, SMMU, HFI and fault recovery remain unfinished. No acceleration or flash.

- Prepared 0102-sweet-gpu-hfi-v1-table.patch and sweet_gpu_hfi_table.{c,h}: constructs a 4-header legacy A615-family downstream HFI layout (queue IDs 0/4/5/1, last disabled, 16-byte-aligned queues, 16608 bytes). Layout, overflow and guard tests passed ASan/UBSan and ARM64 freestanding compile; patch applies after 0100. This is one downstream variant, not device-verified; upstream Linux uses a different table/queue allocation layout. No DMA ownership, IOMMU mapping, cache synchronization, doorbell, GMU start, XNU build or hardware test. CI 40639250560 succeeded for 0095-0097; pushed 0098-0101 as branch d60ba507cf0361b87dbcbd7b3bf14d798b357484 and started run https://github.com/nonrootus/ios-sweet/actions/runs/40640250862 (queued initially). No GPU acceleration.

- Prepared 0103-sweet-gpu-arc-probe.patch for an opt-in combined diagnostic requiring sweetk6a=1 sweetgpuprobe=1 sweetgpuarcread=1. Logs cx.lvl/gfx.lvl raw command-db mappings and obtains APPS DRV vote using a read TCS; touches TCS control registers but issues NO voltage vote, and does not access GPU/GPUCC. ARM64 stub compile and patch check passed; no XNU build/device test. Read may timeout and quarantine the existing RPMh slot; preserve known-good boot and retrieve logs. This will be batched with firmware copy and HFI validation rather than requesting a separate micro-test. Earlier full sequence 0084-0101 applied on a minimal saved XNU tree.

- Corrected offline sweet_hfi_codec response parser: legacy V1 ACK requires message type 2 as well as ACK ID 126; previous test incorrectly accepted type 0. Added negative type check, host ASan/UBSan and ARM64 freestanding compile passed. Source reference Qualcomm downstream kgsl_hfi.c V1 receiver. This codec remains unintegrated and not hardware-tested.

- Prepared 0104-sweet-gpu-hfi-v1-codec.patch to compile the tested HFI V1 packet codec and offline ring helpers into XNU, on top of 0102; includes corrected ACK type check. Neither module is safe for live shared-memory use as-is: caller must provide synchronization, uncached mapping or cache maintenance, and MMIO doorbell; no HFI exchange has occurred. Patch applies to post-0102 configuration, no real XNU build/device test. CI worktree commit b2e98d4 stages 0102/0103 but is not yet pushed.

- Prepared 0105-sweet-gpu-hfi-transport.patch and sweet_hfi_transport.{c,h}: sends and receives V1 messages in the prepared four-header layout using volatile uncached memory, supplied outer-shareable barrier and doorbell callbacks. Bounds, wraparound, incomplete reply and failed doorbell (poisons transport) tested under ASan/UBSan; ARM64 freestanding compile and patch check passed. Requires uncached mapping for BOTH CPU and device, real IOMMU mapping, a correct doorbell and external locking; hardware coherency, callback implementation, XNU build and device behavior unverified. No runtime caller; do not use on cached/live memory. No GPU acceleration.

- Prepared 0106-sweet-hfi-v1-start-messages.patch and updated HFI codec: builds INIT with debug IOVA/size and boot state, and FW_VERSION with upstream-supported 1.10 value. Host ASan/UBSan boundary/header tests and ARM64 freestanding compile passed; patch applies after 0104. This constructs only two messages; legacy startup also requires device-specific perf and bandwidth tables, mapped HFI memory, a running GMU and verified ACKs. No runtime caller or device test. CI 40640250862 was in progress at last successful poll; subsequent status check timed out during TLS handshake.

- CI 40640250862 succeeded for 0098-0101. Pushed 0102-0106 in build branch commit 4d8d72583d7b60417a7a3f437b7ff6a9e11611de and started https://github.com/nonrootus/ios-sweet/actions/runs/40641293368, in progress. Captured FDT describes qcom,smmu-v2 at 0x05040000, dynamic mapping, 3-level tables, and iommus arguments 0 gfx3d_user, 2 gfx3d_secure, 4 gmu_user, 5 gmu_kernel; provider has #iommu-cells=1. These are stream specifiers, not confirmed hardware context-bank numbers. It also lists implementation-specific setup register/value pairs; do not write blindly. No runtime GPU use or flash.

- Prepared 0107-sweet-smmu-discover.patch and read-only sweet_smmu_discover helper. It examines hardware ID registers and existing valid stream mappings, detects masked/overlapping matches, bypass/fault/translation and invalid context banks. Rejects unsupported EXIDS, absent 4K support, impossible counts, inaccessible reads. Caller must first establish powered SMMU, clocks, safe register access and stable mapping snapshot; no ownership inference, no writes and no runtime caller. Host ASan/UBSan and ARM64 freestanding compile passed. Local patch check required ignore-space-change because this saved test tree has CRLF; real XNU build and device behavior remain unverified. No acceleration yet.

- Recovery read-only sysfs on current device confirms Adreno618v1 and IOMMU groups 10/11/12/13 correspond to gmu_user/gmu_kernel/gfx3d_user/gfx3d_secure. These are Linux IOMMU group IDs, not context-bank IDs. Prior k6a boot log showed USB DWC3 at 0x0a600000 and all reported USB clocks on; the existing sweetusb=2 CDC-ECM live logger was proven on another sweet device, not on this model. Windows host has no usbipd command installed, so do not assume WSL can receive live logs or enable this path blindly.

- CI 40641293368 completed success (0084-0106). Downloaded xnu-kernel to D:\ios-sweet\build\xnu-gpu-combined-40641293368; sha256sum -c passed. Reused prior bundle-probe shim Image after confirming byte equality; built shim-boot-gpu-combined.img SHA256 b92ed67009ecfabf799f1a64127b9d236920cdc014ed2d800d396c198d7e2e11, 81920-byte firmware RAMDisk, sweetgpucheck=1 sweetgpuprobe=1 sweetgpuarcread=1, existing UFS root. After recovery adb reboot bootloader, fastboot boot returned Sending and Booting OKAY; no partitions flashed. Waiting for boot and log; no claim GPU started. User explicitly approved publishing only patch 0107 to nonrootus/ios-sweet branch codex/gpu-k6a-macos15; pushed f41be78 and dispatched XNU CI.

- Rechecked MrMoxing/ios-alioth README and SESSION-HANDOFF: repository itself reports GPU rendering not achieved on Adreno 650 and repeated resets when starting CP_SQE_CNTL; several prerequisite or platform hypotheses remain unresolved. This is evidence for alioth only, not proof of behavior on A618. https://github.com/MrMoxing/ios-alioth/blob/main/docs/SESSION-HANDOFF.md ; https://github.com/MrMoxing/ios-alioth . Do not activate CP based on those experiments. CI for 0107 is run 40643070854, build in progress. User asked to return phone to fastboot after combined diagnostic to retrieve SWEETLOG; no screen result yet.

- Combined GPU diagnostic on sweet_k6a: user reports iOS loaded; returned to fastboot, rebooted recovery and read persistent log to D:\ios-sweet\research\sweet-k6a-live-capture-20261027\sweetlog-gpu-combined.txt. SWEET GPU firmware copy/check returned 0 for 81920-byte bundle (integrity, not authentication); GCC cfg AHB 0x00000001, not reported off. ARC command-db cx.lvl=0x30000 with nonzero levels 16,64,128,192,256,384; gfx.lvl=0x30050 levels 16,64,128,192,256,320,384,416. Read TCS returned success: APPS vote cx selector=5 and gfx selector=0; these are not aggregate hardware rail state or measured voltages. Subsequent three-command touch RPMh operation also completed; SpringBoard and backboardd executed. No GPU/GPUCC registers accessed, no GPU start, no acceleration. Device currently recovery; no partition flashed.

- XNU CI run 40643070854 succeeded with 0107 SMMU read-only helper; no device invocation. Live FDT shows GPU SMMU depends on vdd CX and gcc_gpu_memnoc_gfx_clk; downstream gcc-sdmmagpie maps that voted branch to GCC base +0x7100c (0x0017100c), bit0 vote. Existing combined phone log only tested cfg AHB 0x00171004; it did not read 0x0017100c, so SMMU clock availability and safe MMIO remain unknown. Do not equate status bit with reliable ownership or write that register blindly.

- User confirmed known-good mg image loaded and returned phone to fastboot. Prepared 0108-sweet-gpu-memnoc-probe.patch, adds read-only GCC memnoc CBCR at 0x0017100c to existing opt-in sweetk6a GPU probe; reports raw vote/off bits, does not touch SMMU or GPU. ARM64 stub compile and local patch check passed; no complete XNU build or device test. Reading vote/clock status alone is not proof of powered SMMU, ownership, or safe MMIO. Phone currently fastboot. CI 40643070854 for 0107 succeeded. No new firmware download, flashing or device changes in this step.

- User authorized publishing only patch 0108; pushed build branch commit 715704e8ad4b7ae59a176c9709b3fc7cdd440dce to nonrootus/ios-sweet and started CI https://github.com/nonrootus/ios-sweet/actions/runs/40644916576 (in progress). Phone fastboot, working previous iOS confirmed by user; no new test or flash. 0108 is GCC-only read for a required SMMU clock, not GPU startup or proof access to SMMU is safe.

- Captured FDT also describes GMU clocks gpucc IDs 11 (CX GMU) and 14 (CXO), plus GCC IDs 27 and 43, and the GPU node references the same GMU/CXO clocks. Qualcomm downstream gpucc-sdmmagpie source places CX GMU CBCR at GPUCC+0x1098 and CXO at +0x109c. This identifies dependencies only; GPUCC accesses require powered parent and a valid bus. No reads or writes were performed and no conclusion about their runtime state can be made.

- Reviewed saved SWEET XNU cache implementation because recovery reports non-coherent SMMU table walks. osfmk/arm64/caches_asm.s generic non-Apple CleanPoC_DcacheRegion reaches DC CVAC loop plus DSB SY; osfmk/arm/caches_internal.h declares clean_dcache and clean_dcache64. This is a candidate primitive only, not yet verified on this kernel/device or integrated with table publishing, break-before-make, TLB invalidation, DMA coherency, or synchronization. Existing offline table builder remains unsafe for live mappings.

- CI 40644916576 succeeded with 0108. Downloaded xnu-kernel with TMPDIR explicitly on D into D:\ios-sweet\build\xnu-gpu-memnoc-40644916576; SHA256SUMS verified. Built shim-boot-gpu-memnoc.img SHA256 d394c84f57d63ce6812ad2bba7363e8c4ac983318eeec313adcf67f5ca3f3a85 using existing bundle and working shim. Phone in fastboot, fastboot boot returned Sending and Booting OKAY; no flashing. Waiting for user screen report and recovery log, no claim hardware GPU accelerated.

- User reported iOS booted with 0108 and returned phone to fastboot; rebooted to recovery and read persistent log to D:\ios-sweet\research\sweet-k6a-live-capture-20261027\sweetlog-gpu-memnoc.txt. GPU cfg AHB CBCR=0x00000001 (not reported off); GCC GPU memnoc GFX CBCR=0x80000220 (bit31 off, bit0 vote clear). This is a momentary early-boot observation on the voted branch, not proof every parent rail or other controller is off. GPU/SMMU were not touched. Firmware copy/check 0 and SpringBoard/backboardd exec confirmed. Must establish clock ownership and correct CX supply before attempting SMMU register access. Current device recovery; no flash.

- Prepared 0109-sweet-gpu-branch-clock.patch and sweet_gpu_branch helper for the voted GCC GPU memnoc branch; generic callback model preserves an existing vote, sets bit 0 only if absent, waits 5us and polls off bit with a 200us bound, leaves uncertain state poisoned on failure. Based on Qualcomm clk-branch.c BRANCH_VOTED, https://android.googlesource.com/kernel/msm/+/e26b0777dc92ab47d16b0134e57cd1c9e1083a9a/drivers/clk/qcom/clk-branch.c . Synthetic ASan/UBSan tests cover existing vote, delayed on, timeout, write failure and inaccessible reads; ARM64 freestanding compile and sequential patch checks passed. No actual MMIO callback, live invocation, full XNU build, release, power sequencing, or synchronization with other clock clients. Not hardware tested; does not start GPU.

- User explicitly authorized publication of 0109; pushed commit 7e7c322db3d95e35a8cc73000e500beebfccc9f1 to nonrootus/ios-sweet codex/gpu-k6a-macos15 and started https://github.com/nonrootus/ios-sweet/actions/runs/40646997581 (in progress). This adds an uncalled helper only: no real register callback, hardware vote, bus access or GPU acceleration. User's phone is in recovery after successful 0108 diagnostic.

- Further clock reference review: gpu_cc_gmu_clk_src uses root command register GPUCC+0x1120, two documented configurations 19.2MHz bi_tcxo and 200MHz GPLL0 divided, CX-regulated; GX source derives through GPU PLL0 and requires GX/CX/MX rail configuration. These are downstream source tables, not measured live settings and not authorization to program them. 0109 CI 40646997581 in progress; after log capture the previous proven mg image was temporarily booted via fastboot (Sending/Booting OKAY), user screen not yet observed.

- Prepared 0110-sweet-gpu-clock-vote-probe.patch (not pushed): opt-in sweetk6a=1 sweetgpuprobe=1 sweetgpuclk=1 invokes 0109 helper through bounded GCC 0x0017100c MMIO read/write with barriers and delay. Default off; no GPU/GPUCC/SMMU access. It may set memnoc branch bit0, polls up to 200us, retains acquired vote until reboot; no release/rollback on uncertain failure. Caller assumes sole early boot owner; parent clock, later shared ownership, full kernel compilation and actual hardware behavior unverified. ARM64 stub compile and sequential patch check passed; no hardware execution. CI 40646997581 still building 0109. Phone in fastboot per user.

- User explicitly authorized 0110 publication and requested taking more risk to bring up GPU faster. CI 40646997581 for 0109 succeeded. Pushed only 0110 as c8b5075d338e02132b6c6623ab1440e5152cf666 and dispatched https://github.com/nonrootus/ios-sweet/actions/runs/40648630322. It adds optional GCC memory clock vote only; it does NOT start GPU or touch SMMU/GPUCC. Full acceleration remains missing, so do not claim otherwise. User phone fastboot. Avoid repeated minor tests; bundle independent validation where safe, but do not guess unverified power sequences or claim hardware initialization is complete.

- Qualcomm downstream binding defines qcom,dynamic as allowing dynamic domains for hardware that switches among domains within one context bank, not a mapping from DT stream IDs to CB indices. https://android.googlesource.com/kernel/msm/+/refs/heads/android-msm-sunfish-4.14-s-v2-beta-1/Documentation/devicetree/bindings/iommu/arm,smmu.txt . Captured device nodes use stream specifiers 0,2,4,5; keep actual CB allocation/ownership unverified. Prepared D:\ios-sweet\build\xnu-gpu-vote-40648630322\build-image.sh with opt-in sweetgpuclk=1, not yet executed. CI remains running and phone in fastboot.

- CI 40648630322 succeeded for 0110; downloaded kernel with TMPDIR on D, SHA256SUMS passed. Built D:\ios-sweet\build\xnu-gpu-vote-40648630322\shim-boot-gpu-vote.img SHA256 34066432fea9e1551a3f72e50fbc9862ace656821ed7a9a78f0078243e5022bb, with sweetgpuclk=1. fastboot boot Sending/Booting OKAY; no partition flashing. This test may set bit0 at GCC 0x0017100c; it retains the vote to reboot, does not access GPUCC/SMMU or start GPU. Await user screen report and persistent log.

- User reports iOS loaded with 0110 clock-vote image and returned to fastboot; entered recovery and saved D:\ios-sweet\research\sweet-k6a-live-capture-20261027\sweetlog-gpu-vote.txt. Before vote memnoc CBCR=0x80000220; after setting bit0 and polling 200us result rc=-2, state=0x80000221, owned=1 poisoned=1: vote readback set but branch remained OFF during polling. This does not identify exact cause (parent clock, power domain, gating, delay or platform protection remain possibilities). No GPUCC or SMMU access; iOS SpringBoard and backboardd started. Do not retry or access SMMU assuming clock on. Device currently recovery; no flashing.

- Prepared 0111-sweet-gpu-cx-read-probe.patch, not pushed: opt-in sweetgpucxread=1 gated by sweetk6a/sweetgpuprobe and GCC cfg AHB not-off maps GPUCC 0x05091000 and reads CX control +0x6c and hardware status +0x540, no GPUCC writes. Prints before read and waits 1s to give persistent logger a chance; this does NOT guarantee logging before abort. CFG clock on does NOT prove GPUCC registers powered or safe; read may hang, abort or reboot, prior user accepted test risk, no destructive partition operation intended. ARM64 stub compile and sequential patch check passed; no full XNU compile or hardware test. Need source publication authorization before CI per prior auto-review rejection.

- To reduce user wait and bandwidth, tested selective HTTP-range extraction of xnu-kernel artifact from run 40648630322 using local tools/remotezip.py: downloaded only kernel.development.sweet (6,525,912 compressed bytes) and SHA256SUMS (80 compressed bytes), each CRC verified, then sha256sum -c passed. Full artifact previously 60.6 MB. Added tools/fetch-github-kernel.py; accesses gh token and signed redirect in memory, suppresses exception details to avoid exposing signed URLs. Test output D:\ios-sweet\build\gpu-range-check-40648630322. No firmware image downloaded. CI 40650952741 (0111 CX status read) in progress; user approved its publication. Phone recovery following clock-vote timeout.

- CI 40650952741 succeeded with 0111. Selective HTTP-range fetch downloaded kernel 6,521,077 compressed bytes and SHA256SUMS 79 bytes; CRC and sha256sum -c passed. Built D:\ios-sweet\build\xnu-gpu-cx-40650952741\shim-boot-gpu-cx.img SHA256 ee39edc0dd94fcc05912c66bc673b86645cc664c03df7c03379112036d64c7fe, flags sweetgpuclk=1 sweetgpucxread=1. User approved risk. Fastboot boot returned Sending/Booting OKAY; no partitions flashed. This image votes memnoc and reads GPUCC CX registers only; no GPU start. Await device observation and retrieve log; register read could hang/reset and pre-read delay does not guarantee saved log.

- User reports iOS loaded with 0111; recovery log D:\ios-sweet\research\sweet-k6a-live-capture-20261027\sweetlog-gpu-cx.txt confirms GPUCC reads completed: CX GDSC control=0x00222001 (collapse bit0 set, hardware control bit1 clear), CX HW status=0x00005ff4 (power-on bit31 clear), consistent with CX domain off. Memnoc vote bit0 set but off status remained 0x80000221 after 200us; firmware store passed and SpringBoard/backboardd executed. This supports but does not prove CX off causes memnoc timeout. No GPUCC writes were made. Phone in recovery.

- Prepared opt-in 0112-sweet-gpu-cx-power-probe.patch: with sweetgpucxon=1 after checking cfg AHB and APPS CX ARC read vote nonzero, maps previously read GPUCC CX page, uses existing tested CX GDSC helper to clear collapse bit0, polls status bit31 up to 500us. Then existing sweetgpuclk=1 memnoc branch vote runs only if CX succeeds. Skip on missing vote/cfg clock or any CX failure, no GPU/SMMU or GX access, no rollback of uncertain power state; boot arg default off. This writes power domain and may hang/reboot; nonzero APPS vote is NOT measured voltage or proof ownership; no phone test, no full XNU build. Pre-write one-second delay only gives log a chance, not guaranteed. ARM64 stub compile, existing GDSC model tests and sequential patch check passed. User previously explicitly accepted device test risk; source push still requires explicit approval after auto-review rejection.

- User authorized publishing 0112: pushed commit e2e51dd53c036b02000f48d90519ca884a4b37ef and dispatched https://github.com/nonrootus/ios-sweet/actions/runs/40652959177 (in progress). Prepared build script D:\ios-sweet\build\xnu-gpu-cxon-40652959177\build-image.sh with sweetgpucxon=1 sweetgpuclk=1; uses selective kernel download. This is an opt-in power/clock test, no GPU/SMMU/GX startup, no device execution yet; failed CX preconditions skip clock request. User accepted risk; phone fastboot.

- Cross-checked GDSC power-on semantics against Qualcomm generic implementation: gds_hw_ctrl is used as status register when present, PWR_ON bit is checked, software clear of collapse precedes polling and 1us delay. Source https://android.googlesource.com/kernel/common/+/9af93db9e140a4e6e79cdb098919bc928a72cd59/drivers/clk/qcom/gdsc.c . This supports register interpretation, but does not prove prerequisites, ownership, or real platform safety. CI 40652959177 in progress.

- CI 40652959177 succeeded. Selected kernel artifact was 6,521,029 compressed bytes; CRC and SHA256SUMS verified. Built D:\ios-sweet\build\xnu-gpu-cxon-40652959177\shim-boot-gpu-cxon.img SHA256 b45e9aa192545bc442e691897ba371458ad4b0cbcf20e03fcfbe186a79600517 with sweetgpucxon=1 sweetgpuclk=1. User authorized risk; fastboot boot Sending/Booting OKAY; no partition flash. Opt-in test requests CX power then only on success votes memnoc; no GX/SMMU/GPU execution. Await user screen observation and recovery log; no claim it ran successfully.

- User reports iOS loaded with 0112 power-on test. Recovery persistent log D:\ios-sweet\research\sweet-k6a-live-capture-20261027\sweetlog-gpu-cxon.txt confirms CX power-on rc=0 stage=2 status=0x80001fe0, then GCC memnoc clock vote rc=0 state=0x00000221 owned=1 poisoned=0; subsequent CX control 0xf8222000 status=0x80001fe0. Firmware copy/check passed and SpringBoard/backboardd executed. This demonstrates CX and memnoc enabled during this specific boot, not GPU execution, IOMMU readiness, graphics acceleration, long-term stability, or safe shared ownership. No partitions flashed; phone currently recovery. Next batch read SMMU discovery and GMU reset/clock status only after establishing relevant bus/clock preconditions; preserve existing working image.

- Prepared 0113-sweet-gpu-smmu-probe.patch (not pushed): opt-in sweetgpusmmuread=1 requires 0112 CX enable success and memnoc acquired, then reads GPUCC GMU/CXO/root clock status and maps first 4KB of SMMU to run 0107 read-only stream matching for SID specifiers 0,2,4,5. No SMMU writes or GPU/GMU startup. A successful 0112 boot confirmed required rails/branch at one moment but not stable concurrent ownership or safe MMIO; reading can hang/reset. Prints marker and waits 1s before MMIO (not guaranteed persisted). No device test. Freestanding ARM64 stub compile and sequential patch check passed; existing SMMU helper model tests passed. Need explicit source publication approval due previous auto-review rejection.

- User explicitly approved publishing 0113. Pushed b2c4e49cc16f258286b9cd6082848d414a1a7f2b to nonrootus/ios-sweet and dispatched https://github.com/nonrootus/ios-sweet/actions/runs/40654731852. Prepared D:\ios-sweet\build\xnu-gpu-smmu-40654731852\build-image.sh with sweetgpusmmuread=1 + previous CX and memnoc opt-ins. CI running, device fastboot, no SMMU device execution or GPU start yet. Reads of SMMU remain capable of abort/hang and user has accepted test risk.

- Captured sweet_k6a live FDT contains qcom,gmu-pwrlevels @0=0 and @1=200000000 Hz; Qualcomm upstream A6xx driver sets GMU core to 200 MHz before enabling its clock bundle. https://android.googlesource.com/kernel/common/+/68a00586559f5fce3bb163f4618f1b71ef05b4e7/drivers/gpu/drm/msm/adreno/a6xx_gmu.c . This is a requested supported rate, not evidence of current configuration or permission to change it; wait for 0113 clock status. CI 40654731852 in progress.

- CI 40654731852 succeeded. Selected kernel 6,520,645 compressed bytes; CRC and SHA256SUMS passed. Built D:\ios-sweet\build\xnu-gpu-smmu-40654731852\shim-boot-gpu-smmu.img SHA256 17179a5abcebefc4ab70f81164a64d609e2630410cd94bcf6c1e8b8c258ad5c5 with sweetgpucxon=1 sweetgpuclk=1 sweetgpusmmuread=1. Fastboot boot Sending/Booting OKAY; no partitions flashed. This tests CX+memnoc then reads GPUCC clock state and SMMU; SMMU read may fault/hang despite prerequisites and log marker may not persist. Await user report and recovery log; no GPU start.

- User reports iOS loaded with 0113 and returned to fastboot. Recovery log D:\ios-sweet\research\sweet-k6a-live-capture-20261027\sweetlog-gpu-smmu.txt confirms CX enable rc=0 status=0x80001fe0, memnoc vote rc=0 state=0x00000221, GPUCC GMU CLK=0x80004220 (off), CXO=0x00000001, ROOT=0x80000000. Read SMMU ID0=0x48016605 ID1=0x20008005 ID2=0x00007511; helper returned rc=1 (no currently valid matching SMR) for SID 0,2,4,5. These are observations of current nonsecure view, NOT proof entries are free/owned, context banks, coherency or authorization to program them. SMMU register reads succeeded and iOS SpringBoard/backboardd exec. No SMMU writes, GMU start, GPU execution or acceleration. Phone recovery; no flash.

- Prepared 0114-sweet-gmu-clock.patch and sweet_gmu_clock.{c,h}: callback-only GMU root/branch 200MHz setup following sdmmagpie frequency table (source 6 = divided GPLL0, HID divider 2 => /1.5); checks root/branch off, CXO present, rejects HW clock control and busy update, preserves unrelated bits, polls RCG update and GMU branch/root with bounded timeouts and poisons on uncertain failure. Caller must first independently verify 300MHz parent, establish power and exclusive ownership; not integrated, no hardware caller or device test. Host ASan/UBSan model cases for successful init, missing parent, busy state and stuck update, ARM64 freestanding compile and sequential patch check passed. Sources https://android.googlesource.com/kernel/msm/+/64baf9f5436a22365838b8091a1af19fa252f9a0/drivers/clk/qcom/clk-rcg2.c and https://android.googlesource.com/kernel/msm/+/52f6820174ab3c4335f23f3f17c4785011c43679/drivers/clk/qcom/clk-rcg.h . GMU remains off and graphics unaccelerated.

- Prepared 0115-sweet-gmu-clock-probe.patch on top of 0114: with sweetgmuclock=1 and successful CX+memnoc, reads GPLL0 mode/L/fraction and GCC source vote; requires active/locked and expected 600MHz encoding L=31 frac=0x40000000 for 19.2MHz reference, then asserts GCC divided GPU parent vote bit16 and invokes 0114 200MHz GMU clock helper. The /2 parent is described by gcc-sdmmagpie fixed factor, but frequency is inferred from register encoding, not measured; early exclusive ownership, XO rate, parent gate and platform behavior remain unverified. No GPU core, SMMU or GMU firmware writes. Default off. Can hang/reset, keeps votes/unknown partial state until reboot, no automatic rollback. ARM64 stub compile and sequential patch check passed, 0114 host model tests passed; no full XNU build or phone test. Full test requires explicit source-publication approval after prior auto-review rejection. Source Qualcomm alpha PLL https://android.googlesource.com/kernel/msm/+/9eb6e00944471a5552932bc919a796f92663ede6/drivers/clk/qcom/clk-alpha-pll.c .

- CI 40657346818 for 0114/0115 succeeded; kernel downloaded to D:\ios-sweet\build\xnu-gmu-clock-40657346818 and SHA256SUMS verified, but NOT booted. User requested Claude review: Claude flagged Fabia fraction and RCG force-enable concerns. Confirmed target same-revision Qualcomm clk-alpha-pll.c at 2055939b3577edbf42657871ad6bc147af037a82 uses ALPHA_REG_16BITWIDTH=16 for FABIA, so 600MHz with 19.2MHz XO is L=31 frac=0x4000, not 0x40000000 in 0115. Prepared 0116-sweet-gpll0-fabia-frac.patch, git apply --check passed; no build/device test. Do not boot old 0115 test. Claude also suggested shared-RCG enable sequencing but target gpucc-sdmmagpie uses clk_rcg2_ops rather than shared_ops; verify exact path, root and ownership rather than blindly adopting. Require user approval before publishing 0116 because automatic review rejected earlier new source egress. Phone visible in fastboot; no device writes this session.

- Follow-up Claude review verified against same 2055939b3577 Qualcomm sources: gpu_cc_gmu_clk_src uses clk_rcg2_ops, not clk_rcg2_shared_ops; regular clk_rcg2_configure writes CFG and calls update_config, while forced path depends on FORCE_ENABLE_RCG flag. Therefore Claude's assertion that force-enable is required for this exact root is not yet established. Do not blindly apply speculative rollback while UPDATE could be pending. Keep hardware launch gated pending corrected fraction guard and full build. Source saved locally research/sdmmagpie-clock-reference/clk-rcg2-2055939.c; https://android.googlesource.com/kernel/msm/+/2055939b3577edbf42657871ad6bc147af037a82/drivers/clk/qcom/clk-rcg2.c .

- User approved publishing 0116; pushed build branch commit 94705906622ecf66ddac91b13354895903513cbd and dispatched https://github.com/nonrootus/ios-sweet/actions/runs/41182175583. Prepared D:\ios-sweet\build\xnu-gmu-fixed-41182175583\build-image.sh with sweetgmuclock=1 in addition to previously successful CX/memnoc/SMMU diagnostics; no boot yet. PLL guard corrected from 32-bit to 16-bit fractional encoding; direct register readback is not actual frequency measurement or proof of shared clock ownership. Await CI and verify artifact. Phone last observed fastboot.

- Claude had recommended requiring both PLL ACTIVE and LOCK bits. Target Qualcomm Fabia implementation at 2055939b instead waits for ACTIVE when PLL FSM mode is set, and LOCK in non-FSM mode; both unconditionally is not supported by that code. Existing 0115 guard accepts either and therefore is less restrictive but does not verify mode-specific readiness. Do not call this proof of live frequency/ownership. The 0116 corrected encoding is compiled only after CI 41182175583; phone in fastboot.

- CI 41182175583 succeeded for 0116; selective 6,517,855-byte kernel download CRC and SHA256 verified, built D:\ios-sweet\build\xnu-gmu-fixed-41182175583\shim-boot-gmu-fixed.img SHA256 40dc5198f1348d4bc4542230216480f101c49ea03d1c187435a2cc920ec1a6fa with sweetgmuclock=1. Fastboot boot Sending/Booting OKAY; no partitions flashed; await screen and persistent log, no claim GMU started. User indicated Claude WebFetch available: MCP simple example.com test succeeded, subsequent review requests failed with EINVAL. Earlier Claude review caught Fabia frac bug; exact Qualcomm revision verified locally, shared_ops assertion not applicable to target ordinary clk_rcg2_ops.

- User reports iOS booted after 0116 GMU clock test; recovery log D:\ios-sweet\research\sweet-k6a-live-capture-20261027\sweetlog-gmu-fixed.txt shows GPLL0 mode=d0100005 L=0000001f frac=00004000 gates=01241d7b; GMU clock operation rc=0 stage=3 last=00004221 poisoned=0 following CX enable rc=0 and memnoc vote rc=0. SpringBoard and backboardd executed. This is register/operation success, not an independent frequency measurement, proof of shared clock ownership, GMU firmware execution, GPU rendering, or acceleration. Test was fastboot boot only, no partition flash. Phone currently recovery.
- Prepared 0117-sweet-gmu-clock-readback.patch: after RCG UPDATE clears, rereads CFG and requires source 6, divider 2, mode 0 and HW clock control disabled before enabling branch. Failure leaves state poisoned; no claim of measured frequency or ownership. Host ASan/UBSan success and missing-CFG-write test, ARM64 freestanding cross-compile, and patch reverse/forward checks passed. Not yet XNU-built or phone-tested. User authorized future source-only pushes to existing build branch without asking each time; never send phone dumps or private files.
- Published 0117 only to nonrootus/ios-sweet codex/gpu-k6a-macos15 as 49086e11bc9243d0881081a4678d39a9b177d6f9; GitHub Actions run 41184030444 is in progress. The user gave continuing authorization for source-only pushes to this branch. Sequentially applied patches 0107-0117 to D:\ios-sweet\build\gpu-next-probe successfully. FDT reports GMU register resource 0x0506a000 size 0x31000; this encompasses the proposed reset offset 0x14000, but mapping does not establish safe access or reset state. Upstream Linux legacy path loads up to 0x8000 bytes to the ITCM register window, then configures HFI table IOVA, boot config, fence, power settings and other registers before releasing CM3 reset: https://android.googlesource.com/kernel/common/+/0d534518ce87317e884dbd1485111b0f1606a194/drivers/gpu/drm/msm/adreno/a6xx_gmu.c . No GMU reset, firmware writes, SMMU programming, HFI or graphics acceleration has been performed. Phone remains in recovery.
- Prepared 0118-sweet-gmu-status-probe.patch on top of 0117: explicit sweetgmustatus=1, gated by successful CX/memnoc/GMU clock and cfg AHB not-off, read-only GMU window registers SYSRESET +0x14000, FW_BUSY +0x14068, FW_INIT_RESULT +0x14070, RPMH_POWER_STATE +0x143b0 and GENERAL_7 +0x14730. Logs marker and waits 1s before every read; persistence before a hang is not guaranteed. 0xffffffff stops further reads. FDT GMU range covers them; these conditions do not prove MMIO access, ownership or reset safety, and reads can hang/reset device. No GMU writes, firmware copy, GX, SMMU writes or CM3 release. Patch applied on sequential 0107-0117 tree and ARM64 freestanding compile with XNU stubs passed; no full XNU build or phone execution. Claude WebFetch and upstream source corroborated A618 legacy flat firmware layout and identified that 0101 bridge demands GX; its necessity is unproven, so do not call it yet. Actual FDT registers: 0x0506a000 size 0x31000; GPU AHB was 0x1 and CX GDSC reported ON in 0116 boot.
- User continuing source-only push authorization exercised: 0118 published as a57468be623dbd238cbd6ec4fd3a85d0756e1cc0; GitHub Actions 41184440804 pending/running. Earlier 0117 run 41184030444 may be superseded by workflow concurrency; the new run contains both patches. Prepared D:\ios-sweet\build\xnu-gmu-status-41184440804\build-image.sh with sweetgmustatus=1, not executed. No artifact downloaded and no device test performed; phone recovery. Firmware/HFI/SMMU startup remains unimplemented.
- GitHub Actions 41184440804 completed success for 0117+0118. Selective artifact download 6,520,038 compressed bytes, archive CRC and SHA256SUMS passed. Built D:\ios-sweet\build\xnu-gmu-status-41184440804\shim-boot-gmu-status.img sha256 a14e35b7470c3702d0bf566414b42eba32c53fd55dca7c46b3e3e9166c69827e, with sweetgmustatus=1. Rebooted recovery to fastboot and fastboot boot returned Sending/Booting OKAY; no flash or GMU result known yet. Asked user to report screen and return phone to FASTBOOT; obtain recovery persistent log before claiming MMIO success. Test may fault or hang when reading GMU. No GPU/GMU firmware execution or acceleration established.
- User reports iOS booted on 0117/0118 test and returned FASTBOOT. Read recovery persistent log D:\ios-sweet\research\sweet-k6a-live-capture-20261027\sweetlog-gmu-status.txt: CX rc=0 stage=2 status=0x80001fe0, memnoc rc=0 state=0x221, GMU clock rc=0 stage=3 last=0x4221 poisoned=0 (0117 readback requirement passed), cfg AHB=1. GMU read-only status +0x14000 SYSRESET=1, +0x14068 FW_BUSY=0, +0x14070 FW_INIT_RESULT=0, +0x143b0 RPMH_POWER_STATE=0xf, +0x14730 GENERAL7=0. SpringBoard/backboardd executed. This confirms these register reads completed and reset bit value at that boot; not permission/guarantee of firmware writes, persistent clock/rail ownership, GMU startup or GPU acceleration. No partition flash. Phone recovery.
- Prepared 0119-sweet-gmu-tcm-verify.patch and updated local sweet_gpu_gmu unit tests: checks reset=1, compares readback for each firmware word with the kernel-owned source, checks reset again; returns error at first mismatch. Verified with device-extracted 32768-byte a618_gmu.bin in host ASan/UBSan simulated MMIO, including mismatch and reset rejection; ARM64 freestanding compilation and sequential patch check passed. Matching bytes would not prove execution or authentication.
- Prepared 0120-sweet-gmu-tcm-load-probe.patch: only with sweetgmustatus=1 and explicit sweetgmuload=1 after same-boot CX/memnoc/GMU-clock success, cfg AHB not-off, valid GMU status and reset=1, uses separately mapped 0x0506d000+0x8000 and status 0x0507e000, validated kernel firmware store index 0 exact size 0x8000, existing loader and 0119 readback. Never writes reset or starts CM3, never touches SMMU/GX or storage. Marker delays do not guarantee persisted logs. MMIO writes may hang/reset, retention, exclusivity, clocks and TCM access not established; absence of partition writes does not guarantee a successful boot. Sequential patch check and ARM64 stub compilation passed, no full XNU build/phone test. Await independent review before sending or executing.
- Claude independently reviewed legacy GMU layout and 0119/0120; agrees with register offsets and flat 32KiB copy but pointed out extra cold-start state and retention uncertainty, absence of once guard and need for source bundle verification. Local pack-gpu-fw.py verify confirms all 4 bundle entries byte-match phone-extracted inputs; a618_gmu.bin SHA256 9ef10b2b179054fb57af25008e29feb24300c2eaa eabf907bd741786bbacbf2e (spaces here are not digest characters). SHA verifies consistency, not provenance/authenticity. Prepared 0121-sweet-gmu-tcm-preflight.patch: require same-boot reset=1, busy=0, init result=0, GENERAL7=0; one attempt per boot; sample first/last TCM words before any write, log classifications rather than firmware data, stop if both read as all ones. Nonzero samples do not prove ownership, and reads/writes can still fault or hang. No register/control writes beyond 0120's TCM writes; no GMU release. ARM64 stub compile and sequential patch check passed. Earlier 0119/0120 published as 595beb3 to authorized build branch; test has not run on device.
- Published 0121 preflight as build-branch commit ab0a5516ce3b0083034338131601b55576abdee6, dispatched GitHub Actions 41185746201 (pending). Prior 41185576206 may be cancelled by workflow concurrency. Prepared D:\ios-sweet\build\xnu-gmu-tcm-41185746201\build-image.sh with sweetgmuload=1, not executed. Wait for successful build and independent review; hardware test intentionally writes GMU volatile TCM but does not flash partitions or release CM3; hazards include hang/reboot and uncertain device state. Phone recovery.
- Claude second review of 0119/0120 identified potential false positive if TCM retained identical firmware and that power/clock readings become stale; proposed probe writes outside normal upstream GENERAL7/RSC ordering. Prepared 0122-sweet-gmu-tcm-power-recheck.patch: rereads cfg AHB, CX GDSC status, GMU clock branch/root/CFG before sample, immediately before write and after verification. If TCM endpoint words both equal firmware endpoint words, compares full TCM and skips the write on prior complete match or read/reset failure; skips both-all-ones sample per 0121. Does not prove exclusive ownership or that partially retained memory is safe. Nonzero TCM sample alone is not claimed proof of ownership. Read access to uninitialized TCM might fault; preflight reads can hang. Upstream enables GENERAL7 and performs RPMh/RSC handling before TCM load; this experimental test does neither and cannot establish that difference is safe. No claim of GMU execution. Source patch applies after 0121 and ARM64 stub compile passes, no device execution yet.
- Published 0122 as build-branch commit 8c906cf2fd0ac8a3ce6eb02f707c0f6662890ee1; Actions run 41186011144 dispatched. Created D:\ios-sweet\build\xnu-gmu-tcm-41186011144\build-image.sh. Earlier 0119-0121-only CI may be superseded. No new boot/test yet; phone recovery. Proper SHA256 of local a618_gmu.bin and matching bundle entry is 9ef10b2b179054fb57af25008e29feb24300c2eaaeabf907bd741786bbacbf2e.
- CI 41186011144 for 0119-0122 succeeded; selective kernel download 6,513,313 compressed bytes, CRC and SHA256SUMS passed. Built D:\ios-sweet\build\xnu-gmu-tcm-41186011144\shim-boot-gmu-tcm.img sha256 5966b7977445ae854eba657b52cac757db695ed35e3bd4f427624040fa280937 with sweetgmuload=1; recovery rebooted to fastboot, fastboot boot Sending/Booting OKAY. No partitions flashed. This opt-in test may write volatile GMU TCM after guards and leaves CM3 reset; no claim actual write, verify, GMU execution, or iOS boot until log/user result. Asked user screen and return FASTBOOT; then read SWEETLOG with recovery as prior. Test deliberately differs from upstream retention/RSC ordering, so hangs/aborts remain possible.
- User reported iOS booted; log D:\ios-sweet\research\sweet-k6a-live-capture-20261027\sweetlog-gmu-tcm.txt shows TCM load rc=0 written=32768, verify rc=0 matched=32768 and reset remained 1, followed by SpringBoard/backboardd. However 0122 markers are absent from both log and the downloaded kernel: 0122 was skipped. Root cause: our generation of 0121 used a locally contaminated baseline containing an attempted-once guard that 0121 itself did not add; 0122 expected that guard as context and git apply skipped it. The dxb build script treats unapplicable patches as warnings, so a successful CI and matching SHA did not prove all intended patches were included. 0121 status guards and sample did run, but 0122 fresh power checks, once guard and preexisting firmware detection did not. Thus 32768-byte readback is a match after attempted writes, not proof that bytes changed or that GPU/GMU executed. No partitions flashed. Phone recovery.
- Regenerated 0122 from the actual post-0121 baseline; applied 0107-0122 sequentially to a fresh copy of the post-0106 tree with all checks succeeding, compiled resulting probe for ARM64 with stubs. Added GitHub workflow step that fails SWEET DEVELOPMENT builds unless source and final kernel contain the 0122 power-check and once-guard markers; verified previous kernel fails this marker test. This catches this specific missing patch, not every possible skipped patch.
- Published fixed 0122 and source/binary marker CI checks as build branch 393d7e8, then full git apply --reverse --check of 0122 as 831ffe93c9e75a7065b0094b2405e4b20357c753; dispatched Actions 41187259590. Script prepared at D:\ios-sweet\build\xnu-gmu-tcm-41187259590\build-image.sh; do not execute until CI success and local artifact marker checks. Claude agreed old 0122 context was wrong and actual old-kernel result does not prove memory changed; Claude additionally claimed old patch malformed, but independent git apply --stat for old and fixed both exited 0, so that claim is unsupported and rejected. dxb upstream intentionally skips unapplicable patches, so requiring every patch without auditing compatibility could break legitimate build; current workflow strictly checks 0122 specifically and two binary markers.
- Corrected CI 41187259590 completed success, including reverse-check of the full 0122 patch and source/binary marker checks. Downloaded only 6,520,039 compressed bytes; CRC and SHA256SUMS passed. Independently checked binary has 'TCM prerequisites', 'GMU TCM already attempted' and 'preexisting TCM comparison'. Built D:\ios-sweet\build\xnu-gmu-tcm-41187259590\shim-boot-gmu-tcm.img SHA256 d9143ce62bd1059294e6255f058672dc65f395d176ca23d5b0fff5d0c54dfc2d and temporarily fastboot booted (Sending/Booting OKAY); no partition flash. Await user screen and FASTBOOT, then read persistent log. This boot may skip the TCM write if old contents already match; success not established until log, GMU remains in reset.
- User reports iOS booted corrected 0119-0122 and entered recovery. Persistent log D:\ios-sweet\research\sweet-k6a-live-capture-20261027\sweetlog-gmu-tcm-verified.txt: CX status=0x80001fe0, AHB=1, GMU CLK=0x4221 ROOT=0 CFG=0x602 before/after; SYSRESET=1, BUSY=0, INIT=0, GENERAL7=0; pre-sample first=other last=other, code entered load without prior full comparison, meaning at least one endpoint differed from the firmware endpoints. Load rc=0 written=32768, verify rc=0 matched=32768, after-check still reports prerequisites observed and verification rechecks reset=1. This supports TCM changing to firmware bytes and readback in this boot, assuming observed read values accurately reflect hardware. No CM3 reset release, firmware execution, HFI, GPU rendering or acceleration. iOS SpringBoard/backboardd executed. No partition flashed; phone recovery. Prior old-kernel unverified patch error fixed and CI enforced full patch plus binary markers.
- Prepared 0123-sweet-smmu-snapshot.patch and local xnu/gpu/sweet_smmu_snapshot.{c,h}, model test: read-only nonsecure snapshot of GR0 IDs/sCR0/GFSR, all SMR/S2CR, GR1 CBAR/CBA2R and CB SCTLR/ACTLR/TCR2/TTBR/TCR/MAIR/FSR. Geometry derives page size and number of pages from ID1, verifies aperture against captured FDT 0x10000, validates bounds; sample ID1 0x20008005 gives 4KiB page, 5 banks, 5 groups, 0 stage-2-only, CB base +0x8000. Host ASan/UBSan with observed IDs, fault/invalid geometry cases and ARM64 freestanding compile passed; strict 0xffffffff stops scanning, which may conservatively reject valid values. Read-only snapshot cannot prove ownership, stable concurrency, secure state or authorize writes. Source reference https://kernel.googlesource.com/pub/scm/linux/kernel/git/torvalds/linux/+/d4c08d8b23b22807c712208cd05cb047e92e7672/drivers/iommu/arm/arm-smmu/arm-smmu.c and arm-smmu.h.
- Prepared 0124-sweet-smmu-snapshot-probe.patch: explicit sweetgpusmmusnapshot=1, only after same-boot CX+memnoc success, maps 0x05040000+0x10000, reads snapshot and emits raw status; no SMMU writes or automatic bank selection. Context-bank reads have not been tested and may hang or abort; marker delay is not a persistence guarantee. Sequential apply and ARM64 probe compilation passed, 0122 reverse check still passes. Added CI checks for 0124 patch and marker. No full XNU build or phone execution yet. Device FDT confirms SID 4 gmu_user and 5 gmu_kernel; Linux group IDs 10/11 are not CB IDs. Claude suggested optional GMU launch with zero HFI addresses, but that would not establish safe DMA and is rejected until translation/mapping is implemented. The previously observed legacy firmware word at +0x7fe0 is 0, which suggests upstream FW_INIT comparison 0xbabeface for that version convention; not hardware boot evidence.
- Auto-review rejected a combined command that would stage and push source patches 0123, 0124 and CI workflow changes to github.com/nonrootus/ios-sweet branch codex/gpu-k6a-macos15. Stated reason: no explicit authorization for this exact payload and destination in the trusted context, despite user previously granting continuing source-only push authorization. Do not bypass rejection indirectly. Local commit c3d21fb contains code and tests; no GPU firmware or device data is in the proposed payload. Full XNU CI has not run and no SMMU snapshot device test occurred; phone remains recovery. Resume after explicit approval of these exact files and destination.
- Independent static source review: Qualcomm downstream arm-smmu.c selects GR0+0x400 secure alias for CR0/GFSR only when calxeda,smmu-secure-config-access is present; parsed live FDT lacks this property, consistent with snapshot reading +0x0/+0x48. FDT also lacks qcom,skip-init and qcom,enable-static-cb, and includes qcom,dynamic and qcom,use-3-lvl-tables. https://android.googlesource.com/kernel/msm/+/b6410c3f75259c0ca2df45a01838d2e46272723e/drivers/iommu/arm-smmu.c . This static cross-check does not establish that secure/hypervisor policy allows access or ownership. Auto-review again rejected push after user explicitly approved 0123+0124 and CI, saying consent was in untrusted transcript; no indirect workaround used. Local source tests and ARM64 stub compile passed; full XNU CI/device snapshot still unperformed.
- Permissions configuration changed by user; repeated exact authorized source push succeeded. Published 0123 and 0124 plus CI checks as build branch commit 03daabb6d85db4c3844222e1971b69b7275cc278 and dispatched Actions 41188995207. Prepared D:\ios-sweet\build\xnu-smmu-snapshot-41188995207\build-image.sh: explicit sweetgpusmmusnapshot=1, no sweetgmuload, existing CX/memnoc/GMU clock/status flags. This will only read SMMU, not start GMU or program SMMU or TCM; context bank register accesses untested and may hang. Do not boot until successful CI, verify 0124 and 0122 checks and independently verify binary marker. Phone last in recovery.
- While SMMU CI 41188995207 runs, compared legacy HFI table initialization against device-family LineageOS KGSL hfi_init and kgsl_hfi.h: all queue headers initialize rx_wm=1, tx_wm=1, rx_req=1; our offline 0102 builder left them zero. Prepared 0125-sweet-hfi-v1-queue-watermarks.patch and updated local test to verify all four queue headers, including disabled queue, as in downstream. ASan/UBSan host test and ARM64 freestanding compile passed; patch applies after 0124. This corrects a documented protocol initialization difference but does not establish HFI transport, DMA or GPU acceleration. No phone test or full XNU build of 0125. Source https://github.com/LineageOS/android_kernel_xiaomi_sm6150/blob/lineage-20/drivers/gpu/msm/kgsl_hfi.c and https://github.com/LineageOS/android_kernel_xiaomi_sm6150/blob/lineage-20/drivers/gpu/msm/kgsl_hfi.h .
- CI 41188995207 succeeded with 0123/0124 and reverse-apply/marker checks; selectively fetched 6,485,203 compressed bytes (CRC passed), verified SHA256SUMS and binary markers for 0122 and 0124. Built D:\ios-sweet\build\xnu-smmu-snapshot-41188995207\shim-boot-smmu-snapshot.img SHA256 ff6ebd79427cf7304315ef164a3cd3758b8c2e748d8d4f7a4877effaea89dce4, with sweetgpusmmusnapshot=1 and no sweetgmuload. Recovery rebooted to fastboot; fastboot boot Sending/Booting OKAY, no partition flashed. Await user screen and recovery, then read saved log. SMMU GR1 and context reads may hang/abort; no snapshot success established yet. User permits source push without repeated confirmation and current session changed approval policy to never/full access.
- Published 0125 HFI queue watermarks and CI reverse-apply check as build branch commit 8db06b06e4822f344e22f805653abdc9f5a4c484; dispatched Actions 41190006566, in progress. This only changes inactive HFI table builder; existing test boot 41188995207 already running and does not contain 0125. Requested Claude HFI review but service returned DNS ENOTFOUND, so relied on independently reviewed device-family KGSL hfi_init/hfi.h; no claim of device testing. Await phone recovery and log from SMMU snapshot while CI runs.
- User reports iOS booted SMMU snapshot and entered recovery. Persistent log D:\ios-sweet\research\sweet-k6a-live-capture-20261027\sweetlog-smmu-snapshot.txt: rc=0; ID0=48016605 ID1=20008005 ID2=00007511, CR0=00200626 GFSR=0; five SMR entries all 0, S2CR all 000200ff, five context banks read CBAR/CBA2R/SCTLR/ACTLR/FSR/TCR2/TTBR0/TCR/MAIR all zero. This is a nonsecure snapshot of one instant, not proof of secure or hypervisor ownership, future availability, ability to write or safe DMA. CR0 bit10 USFCFG=1, CLIENTPD bit0=0 in this view; do not assume this establishes protection or permits GMU startup. iOS SpringBoard/backboardd started. No SMMU writes or partition flash; phone recovery. 0125 build 41190006566 pending status. All work on D.
- Claude independently reviewed SMMU table helpers and identified missing stage-1 PTE nG bit, risking stale global TLB entries when invalidating by ASID; verified Linux io-pgtable-arm.c explicitly sets bit 11 for stage-1 PTEs: https://kernel.googlesource.com/pub/scm/linux/kernel/git/iommu/linux/+/4c008893415385a0941bbb626c666620a4d7ab00/drivers/iommu/io-pgtable-arm.c . Fixed offline xnu/gpu/sweet_gpu_pte.c and updated model expected descriptors; host ASan/UBSan PTE and table tests and ARM64 freestanding compile passed. These helpers are not presently included by XNU patches (initial candidate patch did not apply and was removed); they remain offline only. Do not assume that adding nG alone makes live mappings safe: no pinned pool, noncoherent cache cleaning, ownership, synchronization, TLB invalidation or mapping policy has been implemented. Claude suggested concrete context register values/CB selection but did not verify target-specific secure ownership, so do not apply them blindly.
- CI 41190006566 for 0125 HFI watermarks succeeded including enforced 0125 reverse-apply check. No hardware HFI execution.
- Prepared offline helper sweet_gpu_table_publish_inactive: walks a caller-owned inactive 32-bit IOVA tree, validates descriptors, cleans child pages before parent through required caller-supplied 4KiB sync+completion-barrier callbacks, fails on callback error. Caller must ensure exclusive inactive tree, allocator ownership and no aliases; no live mutation safety, CPU mappings, cache callback, TLB invalidation, SMMU setup, or hardware caller. Host ASan/UBSan model verifies child-before-root, rejection before writes and failed sync, ARM64 freestanding compilation passed. Prepared 0126-sweet-gpu-table-helpers.patch to include corrected offline PTE and table helpers in XNU; applies on clean 0107-0125 tree, no runtime caller, no full XNU build or device execution. Independent Claude review requested before release. User requests continuing porting; phone recovery after SMMU snapshot.
- Claude reviewed preliminary inactive table sync helper and identified real missing protections: alias cycles, duplicate child tables, leaf alias to table pages, root PA resolution, and unrestricted leaf attributes. Independently fixed offline helper: caller supplies 2053-entry scratch outside kernel stack, collects distinct table PAs and rejects duplicates, checks root mapping, validates exact PTE attributes/36-bit PA and rejects leaf PAs that match any table before any sync; then cleans child-first. Added model tests for table-page leaf mapping, root cycle, duplicate child, reserved bits and failure path. ASan/UBSan host tests, ARM64 compile and sequential 0126 apply check passed. 0126 is prepared but not published or device-tested. All cache operations remain abstract callbacks, offline inactive tree only; no claimed device-visible memory ownership, runtime SMMU configuration or GMU start. Claude follow-up review requested; no device writes.
- Claude follow-up reviewed corrected inactive table publisher: confirmed masks/root count, flagged large scratch must not be on kernel stack, assumptions about resolve, and O(number of leaves * table pages) behavior. Changed collection to keep sorted PAs and validate leaves via binary search; explicitly require heap/static scratch disjoint from tables, stable injective resolve and caller-owned pinned leaf pages. ASan/UBSan test and ARM64 cross-compile passed, 0126 regenerated and sequential apply check passed. This does not allocate pages, sync real caches, control TLB or run on hardware; SMMU ownership and attributes remain unproven.
- Published 0126 inactive table helpers and CI reverse-apply check as build branch 16f3e0c10bbc8aa65e0033fd45525a77edcbd2e5; Actions run 41192447467 in progress. Helper has no runtime caller and cannot initialize SMMU or start GMU. Host sanitizer and ARM64 stub tests passed; full XNU CI pending. Phone recovery. To get real translation, still need pinned owned backing memory, device-visible PA, synchronized cache operations, independently justified CB ownership and TCR/MAIR/TLB fault/recovery sequencing; don't program guessed values.
- GitHub Actions 41192447467 completed success for 0126 inactive table helpers, with the reverse-apply CI check. Helpers have no runtime caller and the CI success is compile verification only; no new image downloaded or test boot performed. User phone remains recovery. Independently checked saved XNU headers: clean_dcache(void VA, length, phys flag) and IOBufferMemoryDescriptor's wired default and physical segment interfaces are candidate components, not a verified allocator/device-visible PA or cache-coherency solution. Continue toward owned pinned pool, real cache and TLB ops before enabling SMMU/GMU.
- On 2026-11-04 inspected xiongnemo/hakios-alioth default branch alioth HEAD 30945feb5b574a86031fbfc1600c003c1ca89576 via GitHub API (the main branch is different; use alioth). README and docs/alioth/status.md claim phone-tested Adreno 650 OpenGL ES via Mesa/freedreno, Wi-Fi via PCIe/MHI ath11k, Bluetooth HCI UART including audio, and four selected Titan 480 camera sensors; Metal not implemented, RAM session is nonpersistent. These are author claims/screenshots for POCO F3, not independent testing or evidence of functioning on sweet_k6a. The branch has source devices/redmi-k40/overlays/xnu/files/bsd/dev/hakios.adreno.c, umi_wifi.c, umi_bluetooth.c, umi_camera.c, and iokit/Kernel/hakios.gpu.cpp, plus userland overlays. GPU code specifically profiles A650/A642L and a650/a660 firmware; ours is observed Adreno618 legacy firmware. Do not use its MMIO addresses, firmware startup, camera sensor/ISP/BT/Wi-Fi paths as-is. Most relevant next research: compare SMMU, cache clean, memory ownership, HFI and GPU IOService+Mesa interfaces with our 0126; map Wi-Fi/BT/camera hardware from actual sweet FDT/vendor before choosing driver. README https://github.com/xiongnemo/hakios-alioth/blob/alioth/README.md ; status https://github.com/xiongnemo/hakios-alioth/blob/alioth/docs/alioth/status.md ; GPU source https://github.com/xiongnemo/hakios-alioth/blob/alioth/devices/redmi-k40/overlays/xnu/files/bsd/dev/hakios.adreno.c . Attempted filtered clone to D was interrupted while it was still downloading; no images downloaded and no device test.
- User requests fix wallpaper/missing apps plus GPU/Wi-Fi/Bluetooth/cameras. Phone was not visible in adb or fastboot at start; asked user what applications/wallpaper symptoms and phone USB state. Did not change the installed system. Mounted saved repair.img read-only (not the later installed mg-nowait image); /Applications has 143 entries including valid Info.plist for Camera and Safari, /Library/Wallpaper/Stills and Collections including iOS 16 assets exist, while baseline /private/var/mobile/Library/SpringBoard and /private/var/db/com.apple.lsd are absent/empty. These are baseline image observations only, not proof of current phone files or root cause; Linux HFS stat emitted ENODATA for many metadata reads, while Python listing/selected plist reads succeeded. Unmounted after inspection. Do not reflash userdata or delete caches without confirming state and backups.
- Parsed saved sweet_k6a FDT: Bluetooth compatible qca,wcn3990, Wi-Fi node qcom,icnss at 0x18800000 (does not by itself identify active firmware/chip model), camera has five generic qcom,cam-sensor slots across CCI 0x0ac4a000/0x0ac4b000 and qcom,camcc-sdmmagpie; sensor model cannot be derived from node name. Added read-only tools/device-peripherals.py based on existing bounded FDT parser and verified against saved FDT; no device access or hardware writes. Alioth is SM8250 A650 and its Wi-Fi path PCIe/MHI/ath11k, so don't reuse it blindly. Fetched five specific public source files (total <400KB) on D:\ios-sweet\research\hakios-alioth-source-30945feb for comparative analysis, no firmware/images. Current GPU unaccelerated; no Wi-Fi/BT/camera functionality claimed. Asked Claude for independent analysis, awaiting result.- User reports black wallpaper and only a few apps. Saved repair.img (older baseline, not proven identical to installed phone filesystem) contains 32 valid staged app bundles absent from /Applications. Prepared read-only tools/staged-system-apps.py; planning it on the mounted baseline showed 32 absent and none already present. A disposable HFS fixture confirmed a preliminary copying experiment on a dummy bundle only; this does not validate metadata, application registration, or actual iOS apps, so the copying implementation was removed. No apps installed and no caches or user data changed by this tool. Wallpaper cause remains unknown. Claude independently suggested staged apps as a hypothesis and PosterBoard diagnostics; its sda34 suggestion was wrong, recovery by-name maps userdata to sda36.
- Recovery dmesg showed qcom icnss platform probe and camera ISP/JPEG probe, not functioning iOS drivers. Rebuilt previously tested 41188995207 diagnostic boot image on D with sweetnull for backboardd, SpringBoard, PosterBoard, lsd, installd, iconservicesagent and sweetsample for PosterBoard, lsd, SpringBoard, installd. SHA256 913b427b8d97170b33033364901518e1524b65e036b57167aefeab5850331b99. Rebooted recovery to fastboot and fastboot boot returned OKAY, no partition flash; kernel persistent log mechanism can write diagnostic log to userdata as in previous tests. User asked to check wallpaper and return to recovery; result and new log pending. /dev/null tee captures only writes actually made there, not all OS logs. No GPU acceleration, Wi-Fi, Bluetooth, camera or wallpaper fix claimed.
- 2026-11-05: extracted NEW ui diagnostic log from recovery: sweetlog-ui-diagnostic-20261104.bin/.txt, total 268486 bytes flush 15 (previous was 219014/10). SpringBoard, lsd, PosterBoard and iconservicesagent exec observed; numerous CATransformLayer/nil-layer warnings and missing AppleM2ScalerCSCDriver. These do not establish wallpaper root cause. No useful PosterBoard tee output or installd exec seen in examined log.
- User specifically points back to hakios-alioth wallpaper success. Retrieved targeted source files from alioth branch (not a whole image). userland/src/eagl.c lines 1604-1617 documents wallpaper missing for CoreAnimation function 0x59/cst glUseProgram(0); plain_draw_begin at 2830 supplies shader for textured draws. This is GL/Mesa integration, not drop-in for our CPU renderer. userland/src/inject_sb.c 774-795 documents a separate black poster selection scene and disables long-press switcher, not a wallpaper rendering fix. Their inject.c targets iOS16.5 20F66 cache addresses, ours uses 20H392: no address transplant. userland/build.sh and select-system.py relocate staged apps into Applications. Sources saved under research/hakios-alioth-source-30945feb, but new files were downloaded from moving alioth branch, not pinned to that folder-name SHA; pin before reuse.
- Prepared temporary read-only USB block reader under build/adb-hfs-readonly: phone Python opens userdata O_RDONLY, communicates via adb shell -T; FUSE file and loop mount both read-only. Initial raw header read confirmed HFSX. No successful filesystem mount yet: fixed a FUSE method/lock name collision, next attempt lost adb device; final adb devices empty. Cleanup trap attempted unmount and stopped helper. This is experimental local tooling, no filesystem edits or full image transfer. Phone state must be rechecked before next attempt. No wallpaper, apps or GPU fix deployed. Existing tools/mkiosroot.sh modification left untouched.
- 2026-11-05: successfully mounted CURRENT phone iOS filesystem READ ONLY through adb + FUSE + read-only loop. Fixed shell binary newline translation by base64 framing; constrained exposed size to actual HFSX header size 17179869184 (4096 * 4194304), not full 241598181376-byte userdata; otherwise Linux rejects secondary volume header. No device filesystem writes. Capture build/adb-hfs-readonly/inspect.sh, output research/sweet-k6a-live-capture-20261027/ui-files-20261105.txt. Mounts cleaned up after each inspection.
- Live findings: Applications 143, staged_system_apps 32; Safari and Camera bundles exist. IconState lists Photos/AppStore/Settings plus widgets, dock Phone/Safari/Messages. SpringBoard wallpaper dictionaries both have none entries. PosterBoard prefs only locale/build values; PRBPosterExtensionDataStore/59/Extensions empty, gallery cache sections contain empty items. LegacyPoster.appex exists in PaperBoard.app and declares com.apple.posterkit.provider. These support investigating registration/default-poster initialization, not proof of renderer defect. MobileInstallation log shows 0 containerized apps scanned and system app migration reported complete; installd HAS run in device history, despite no exec in sampled latest log. Do not claim never ran.
- Added opt-in --promote-offline to tools/staged-system-apps.py: for backed-up loop-mounted build images only, renameat2 NOREPLACE moves staged bundles into Applications on same fs, retains inode metadata/hardlinks rather than copying. Default remains read-only. Dummy HFS fixture tested dry-run, UID/GID/mode/inode/hardlink/symlink preservation, existing destination skip, repeat. No actual Apple app boot test, no automatic build integration, no deployment. Test script build/adb-hfs-readonly/test-promotion.sh and disposable 64MB test image remain on D. User tools/mkiosroot.sh unchanged.
- Claude review agrees GLES-only wallpaper fix from HakiOS does not apply to SWContext, recommends examining poster data and app migration. Live reads above supersede its inference that installd never ran and confirm empty poster gallery. No GPU/Wi-Fi/BT/camera functionality added; wallpaper fix still unresolved. Next: validate registry/default-poster setup with installed 20H392 and prepare backed-up offline image app promotion before any proposed phone write; do not blindly enable all migration or transplant 20F66 addresses. Phone last in recovery.
- 2026-11-05 GPU: prepared 0127-sweet-gpu-wired-memory.patch and xnu/gpu/sweet_gpu_memory.{cpp,h}. Preparation-only IOBufferMemoryDescriptor pool (1..64 4K logical pages) uses wired kernel allocation aligned to native page_size (16K), mapper disabled, verifies each host-PA 4K segment below 36-bit limit with unique pages, exposes bounded page lookup and explicit VA cache clean + dsb sy. No GPU/SMMU caller, no MMIO, no GMU release, no runtime page-table integration or acceleration. Destroy only valid while never exposed to DMA; active ownership protocol remains future work.
- Claude reviewed target XNU sources and caught clean_dcache C++ linkage and 4K alignment suballocation on 16K kernel. Independently confirmed headers/allocation code and fixed extern C, native-page alignment, explicit MapperNone physical lookup; guarded unsupported coherent/Apple cache configurations. CPU zero-fill is explicit and requires caller clean after final writes, not claimed immediately PoC-visible.
- Installed clang-18 in D-backed WSL (51.3MB download). Local ARM64 syntax and assembly emission against actual saved XNU source/generated headers succeeded using build/check-gpu-memory.py; compiler uses fallback macros for Apple-only type metadata builtins, so NOT release-quality full kernel build. Assembly has unmangled _clean_dcache call and dsb sy. Patch apply --check passed against saved XNU tree; full macOS CI and runtime tests pending. GitHub CLI log fetch from WSL timed out on TLS. Phone remains recovery; no device operations this milestone.
- Published 0127 and reverse-apply CI check to nonrootus/ios-sweet codex/gpu-k6a-macos15 as 35a5ca2. Windows configured gh credential-helper pointed to deleted .codex-temp executable; publication used existing WSL gh credential in-memory with Windows git Authorization header, no secret printed or stored in repository. Source push succeeded. Two workflow dispatch attempts returned HTTP422: Actions has been disabled for this repository. GET actions/permissions reports enabled=true, allowed_actions=all; repository public, not archived/disabled. Therefore no CI run started; reason unresolved, not assumed billing. Asked user to inspect Actions banner. No repo permissions changed. Complete macOS build/link and phone verification remain outstanding; local syntax/assembly only, GPU still not accelerated.
- User enabled Actions; dispatch accepted HTTP204. Full XNU run https://github.com/nonrootus/ios-sweet/actions/runs/42037042030 at build branch 35a5ca25b05f0b51aee7e1b4d48ca8ef2d35690b is in progress, Build stage. Added host model test sweet_gpu_memory_test.py: compiles actual adapter body against mocked IOKit/cache and replaces ARM barrier with a counter, explicitly not hardware validation. ASan/UBSan PASS for allocation failures, bad segment length, zero/unaligned/out-of-range/duplicate physical addresses, cleanup, lookup bounds, CPU zeroing and clean requests. No runtime integration or device boot.
- Full macOS XNU CI 42037042030 completed SUCCESS for build branch 35a5ca25b05f0b51aee7e1b4d48ca8ef2d35690b including Build, required-patch reverse-apply verification and artifact uploads. This is full build/link evidence for 0127, not runtime evidence. No artifact download or device boot needed yet: preparation adapter has no caller, SMMU programming/HFI integration/GMU start remain unfinished. Host memory fault-path ASan/UBSan test passed separately. Phone recovery preserved.
- Prepared 0128-sweet-hfi-owned-memory.patch plus sweet_gpu_hfi_memory.{cpp,h}: composes 0127 wired pool with real HFI v1 initializer and 0126 inactive page tables. Owns eight 4K pages (five HFI, root+two child tables), requires nonzero 64K-aligned 32-bit IOVA, maps only owned data pages, cleans data then leaf/parent/root tables; scratch resides in heap context, not stack. Opaque object exposes addresses only after successful publication and cannot be installed into live SMMU yet; no DMA lifecycle or device calls. Caller must reserve IOVA. No runtime caller or hardware changes.
- Host ASan/UBSan composition test passed actual HFI/PTE/table code against modeled memory: noncontiguous physical addresses, three IOVA ranges including 0xffff0000, HFI header/queue pointers, clean order 0..4,7,6,5, all eight page-get and clean-failure paths, allocation failure and cleanup. Actual target-XNU-header ARM64 assembly emission passed after copying new source/header to saved buildtree; not a full kernel build. 0128 apply --check passed against config fixture after0127. Claude review pending; no source push yet.
- Claude reviewed 0128 composition: no blocking prep-only correctness issue found. Added explicit live-HFI cache-line hazard to header: CPU/GMU indices share lines, so current cached allocation cannot be used for non-coherent live queues; future queue memory needs verified uncached mapping/synchronization, proper firmware IOVA window, matching SMMU attributes and quiesce lifetime. Do not mistake clean/invalidate or zeroing root on destroy for a live ownership protocol. Added model assertions for all unused table entries and HFI tail zero padding. Patched source exists (review's missing0128 note was stale).
- Published 0128 plus CI reverse-apply check as build-branch ea1a6dc802e61ffc2aae3306c3cee23c54ef4d76; Actions run https://github.com/nonrootus/ios-sweet/actions/runs/42040631290 in progress. Expanded sanitizer model passed after review. No hardware access.
- Follow-up cache research: IOBMD cache flags feed iomdOptions to IOMemoryDescriptor memory-entry cache mode; IOMemoryDescriptor maps InhibitCache to VM_WIMG_IO, WriteCombineCache to VM_WIMG_WCOMB. Saved pmap source maps WCOMB to CACHE_ATTRINDX_WRITECOMB. This is source evidence only, not verified loaded SWEET pmap behavior. Important for next revision: current eight-page prep pool has HFI logical page4 and table pages5..7 in one native16K page. Live queue data and table storage should use separate native-page-isolated descriptors before choosing differing cache modes. Do not merely flip cache attributes for five4K pages within this shared pool; do not install current prepared object into SMMU.
- Run42040631290 Build step succeeded but required-patch verification failed (job127290221337); overall run not green. Reproduced a concrete verification failure locally:0128 appends files.arm64 after0127 EOF hunk, making0127 reverse-check fail although source unchanged. Fixed build workflow to reverse-check0127 source files excluding files.arm64 and separately grep its exact build declaration;0128 still reverse-checked in full. Both local checks passed. Full job log download failed/stalled and was stopped; annotations only say exit1, so do not claim log-confirmed failing command.
- Published verification fix ce4c967996ece75b67bd91756b0e9ffe77f0ba1a and dispatched https://github.com/nonrootus/ios-sweet/actions/runs/42043576208 . Latest state queued, no successful recheck yet. GitHub annotations mention macOS arm64 runner capacity constraints. No hardware boot/flash this turn. Next: check42043576208, resolve any failures, then separate HFI data/table descriptors along16K boundaries and verify an uncached queue mapping before any SMMU/GMU runtime call. Current 0128 must remain preparation-only.
- 2026-11-05: 0129-sweet-hfi-separated-memory.patch splits HFI into separate 5-page data and 3-page table descriptors. Existing native-page-aligned backend allocates whole 16K pages (32K data,16K tables), so data tail no longer shares a native page with tables. Cache modes unchanged; prep-only, no live SMMU/GMU caller. Host ASan/UBSan passes both allocation failures, all8 page/clean failures, noncontiguous data rejection, actual table mappings/HFI layout/clean order and cleanup. Fake native-page isolation is model setup, not proof of runtime allocation. ARM64 assembly emission against saved target headers passed; sequential0127-0129 apply plus final-source comparison passed. Claude review found no blocking prep-only issue; native allocation isolation independently follows IOBufferMemoryDescriptor page_size alignment and whole-page allocation, runtime unverified. Claude also flagged possible WB physmap alias for future NC queues on NO_MONITOR; must independently inspect actual linked pmap and PTE/MAIR before choosing live cache protocol.
- CI42043576208 failed before any step: job127300446364 cancelled, annotations explicitly say no hosted runner acquired and macOS arm64 capacity constraints. Added macos-15/macOS-15-intel runner choice (official label macos-15-intel) to workflows; next dispatch will try Intel host while retaining SWEET arm64 target. Updated final-source CI verification for0129 instead of reverse-checking superseded0128 source. YAML and local required-patch/config/final-source checks passed. No phone changes; wallpaper/apps remain uncorrected on device.
- Published0129 as e7f14b30ba4362e1a502a0b77476fee838182e35; Intel fallback run https://github.com/nonrootus/ios-sweet/actions/runs/42048471623 started (Build in progress at14:54UTC). Main implementation commit3764a1f. Phone<TARGET_SERIAL> remains recovery; another unrelated ADB device is attached, so always pass the target serial. No phone writes or boots performed.
- Cache-source follow-up: generated saved osfmk Makefile has NOS_ARM_PMAP and compiles osfmk/arm/pmap/pmap.c; SWEET NO_MONITOR excludes __ARM_PTE_PHYSMAP__ update path at pmap.c10668. However a remaining cached linear alias is not by itself proof of inevitable failure: Linux v6.12 arch/arm64/mm/dma-mapping.c arch_dma_prep_coherent + kernel/dma/pool.c + kernel/dma/remap.c use cache preparation and a distinct Normal-NC mapping; arch/arm64/include/asm/pgtable.h pgprot_dmacoherent documents Normal-NC. Keep original cached alias unused and validate the entire allocation/cache-transition/lifetime protocol; do not adopt Claude suggestion of per-field invalidation as a proven fix. Runtime MAIR/PTE/alias evidence still absent. Mainline a6xx_gmu_memory_alloc uses GMU uncached IOVA range0x60000000+PAGE_SIZE through0x80000000, with a fixed dummy allocation at0x60000000; this reference does not validate exact A618 vendor firmware requirements. Current generic prep-only API intentionally does not choose firmware IOVA.
- CI42048471623 SUCCESS on Intel host: Build14:48:24-15:03:15UTC, required-patch/final-source verification15:03:15-15:03:18UTC passed; job127317815561 overall success. Thus full build/link verifies0127-0129 together and fixes prior verification failure; no kernel download or phone boot (new prepared-memory path still has no runtime caller). Main code3764a1f, published e7f14b30ba4362e1a502a0b77476fee838182e35. Need implement and runtime-validate queue cache mapping/access/lifetime before SMMU/GMU integration; no acceleration, wallpaper or app fix deployed.
- Claude follow-up withdrew the claim that an unused WB physmap alias fundamentally blocks the Linux-style NC approach. It proposed forcing physically contiguous allocation, but independent source review rejects that as necessary for our current backend: IOBufferMemoryDescriptor.cpp368 uses IOMallocAligned_internal when alignment>1, IOLib.cpp544 calls kernel_memory_allocate without KMA_KOBJECT for whole-page sizes, and vm_kern.c889 allocates a private object. Our explicit page_size alignment already follows this path; do not replace it solely on that review claim. Future NC implementation still needs canonical-VA-only access, checked runtime MAIR/PTE/cache attributes, queue barriers, and quiesced DMA lifetime. No NC mode added yet, no deliberate physmap stale-line hardware probe authorized/performed in this milestone.
- Prepared0130-sweet-gpu-memory-probe.patch and xnu/gpu/sweet_gpu_memory_probe.cpp: opt-in sweetgpumemory=1 + sweetk6a=1 call after existing UFS GPU-probe call; test boot must omit sweetgpuprobe so no GPU registers are touched. First real inactive HFI create/info/destroy, then two cycles separate cached3-page tables + Normal-NC5-page IOBufferMemoryDescriptor queues. AT S1E1R/PAR with IRQs disabled and saved PAR restored verifies CPU effective PA/attribute plus pmap_cache_attributes, logs physmap translation WITHOUT accessing alias data, verifies native-page separation and canonical-NC pattern read/write, then releases buffers never exposed to DMA. No SMMU/GMU/MMIO or partition writes. Actual target-header ARM64 assembly compile passed;0130 patch apply/reverse/source-equality passed. Full CI and Claude review pending; no device test yet.
- Claude review caught real highmem bug before hardware: pmap_sync_page_attributes_phys shifts32-bit ppnum_t before casting to vm_offset_t. At PA>=4GiB this truncates the flush address; physical flush then calls phystokv_range below DRAM and may panic. Independently confirmed pmap.c6884, ppnum_t uint32, ptoa_64 casts BEFORE shift, and non-coherent flush path. Added0131-sweet-pmap-highmem-cache-sync.patch using ptoa_64(pp). Regression compiles actual patched function with recording flush stub and passes addresses below/at/above4GiB and near36-bit limit.0131 applies/reverses against savedtree.0130 reviewed/updated to report CPU/alias attribute bytes, allocation/segment/readback failures; after NC writes zeroes then flushes both owned native pages before release (no WB data access/DMA). ARM64 compile of updated diagnostic passed before final alignment guard; source-only13KiB addition. Initial0130-only run42055576429 must NOT be booted; superseded by0130+0131 dispatch. No phone reboot yet.
- Confirmed highmem bug also in already-built old kernel xnu-smmu-snapshot-41188995207/kernel.development.sweet: disassembly of _pmap_sync_page_attributes_phys atfffffe0007471328 is lsl w0,w0,#0xe (32-bit truncation), then flush_dcache. Actual shim/out/sweet-k6a.adt reports dram-base0x100000000 and dram-size0xfcb00000. New helper build/inspect-memory-kernel.py will verify wide shift in0131 binary before boot. Updated0130+0131 build branch e3b90194de579244ae956c40b23cceb866e0a7d1, run42056391242 in progress; old0130-only42055576429 cancelled by concurrency. Final0130 target-header ARM64 compile passed. Pretest log saved sweetlog-before-memory-0130 with total268486/flush15. Target<TARGET_SERIAL> recovery; no device mutations.
- Read-only live poster metadata inspection saved poster-metadata-20261105.txt. PaperBoard and PosterBoard apps plus LegacyPoster.appex exist, minimumOS16.7; LegacyPoster advertises com.apple.posterkit.provider. DefaultWallpapers~iphone has generic default7400/23EC2CF1-0188-49FC-B214-EC1AB37FE5C4, so absence of a specific iPhone10 entry is not itself failure. Wallpaper Collections include iOS_16 and other sets. PaperBoard/PosterBoard capabilities list arm64+armv7, extension arm64; no claim that this is root cause. No edits to phone, FUSE inspection exited with cleanup. Existing empty poster registry remains unresolved.
- CI42056391242 SUCCESS for e3b90194de579244ae956c40b23cceb866e0a7d1 (0130+0131). Kernel downloaded selectively after unstable Azure transfers; resumable compressed cache onD, SHA256SUMS/CRC passed. Binary _pmap_sync_page_attributes_phys now ubfiz x0,x0,#14,#32 (wide), replacing old lsl w0. Built xnu-memory-probe-42056391242/shim-boot-memory-probe.img SHA256059dc254d5761b483ba5b80c9d4311bd3f0b071f835f759f1898212525922e44, cmdline sweetgpumemory=1 and no sweetgpuprobe=1. Recovery->fastboot->temporary boot Sending/Booting OKAY, no partition flashing. Phone subsequently returned to recovery.
- HARDWARE RESULT0130+0131: fresh sweetlog-memory-0130-0131.txt total242888/flush12 has inactive HFI=pass root0x10465c000 iova0x60010000; two allocation/access/release cycles pass and done result=pass. Nativepage16384, MAIR0xc08044f00bb44ff; cached pages effective PAR attrff /WIMG2; all5 queue pages in each cycle effective NC attr44 /WIMG6 with matching PA. Physmap aliases remain attrff, observed by AT only, no alias data loads. QueuePA pages0..3 contiguous within16K but page4 independentlyallocated (e.g104678000..10467b000 then104674000), confirming cannot assume32Kphysicalcontiguity. Log laterexecs SpringBoard andbackboardd; user visual screen not recorded. This validates CPU allocation/cache/access/free path and highmem fix in thisboot; NOT GMU DMA coherence, SMMU translation, GMU execution or graphics acceleration. Next integrate verified NC mode into owned HFI data pool while tables staycached and retain no-DMA contract until lifecycle/translation integration.
- Prepared0132-sweet-hfi-normal-nc-memory.patch: actual HFI data pool now create_nc, tables remaincached. New backend validates each effective CPU PA/NormalNC attribute and pmap WIMG before CPUzeroing; only canonicalNC accesses allowed. NC clean performs dsb; destroy flushes whole owned16Kpages before release only after initialization. Partial validation failure performs no NC writes and releases normally. Still no DMA ownership/SMMU setup/GMU release. Updated probe marker inactive HFI Normal-NC distinguishes this integration from0130 standalone buffers. HostASan/UBSan passes cached/NC allocation failures, perpage validation failures with no earlyflush, alignment rejection, nativeflushboundaries0/4 and HFI pool mode selection; target-headerARM64 memory+HFI compiles pass;0132 and revisedCI reverse checks/finalsource comparisons pass. Claude review no blocking issues; optional postfree PA check rejected as racy/unnecessary. FullCI/device0132 pending.
- Published0132 as53c69cef6f42a85613df16bcfa7d5141c99e6254, fullIntelCI https://github.com/nonrootus/ios-sweet/actions/runs/42073509204 in progress. Maincommit0fb7fc8. Workflow now checks final5memory/HFIsources plus reverse0132, reverse0131, and0130 excluding supersededprobeCPP; new kernel marker enforces inactive HFI Normal-NC. CPUcache callback source follow-up: cpu_data_init initializes cpu_cache_dispatch=NULL, ml_processor_register may copy platform_cache_dispatch; no explicit SWEET assignment found, not a runtimeNULLmeasurement. Phone remains recovery after successful0130+0131 test; no0132 boot yet.
- CI42073509204 for0132 completed SUCCESS, including required patch/final-source/kernel-marker verification. Selective kernel download started; no0132 hardware result yet. Pretest recovery log saved as sweetlog-before-memory-0132 (same total242888/flush12 as0130+0131). The user asked how long to GPU: explicitly explained that SMMU access, GMU execution, GPU command submission and iOS graphics integration remain substantial unfinished stages; no ETA claimed.
- Next-stage research only: observed SMMU ID0=0x48016605 has S1TS=1 and ATOSNS=0. Linux v4.19 drivers/iommu/arm-smmu.c lines1618-1621 treats this combination as supporting translation operations on SMMUv2; arm_smmu_iova_to_phys_hard lines1179-1216 uses an atomic64-bit ATS1PR write, bounded ATSR poll and PAR read. Source: https://raw.githubusercontent.com/torvalds/linux/v4.19/drivers/iommu/arm-smmu.c . This supports considering an isolated context translation test with CM3 held reset, not proof of Qualcomm access permission or working translations. Check downstream SM7150 quirks before implementing. Any failed teardown/TLB sync must not permit freeing memory still reachable by hardware; current prep-only destroy API is not sufficient for active mappings. Claude was consulted but returned no verified technical assessment on this question; no unsupported recommendations adopted. No new SMMU writes performed.
- Downloaded0132 kernel from42073509204 (6508474 compressed bytes) to D:\ios-sweet\build\xnu-memory-probe-42073509204; CRC/SHA256 passed, kernel SHA25678f4c6cd1bae813b28d38b204aa99b10f131fa3b80457b5a034461428ba38edc. Binary contains new inactive HFI Normal-NC and NC validation failure markers; disassembly confirms pmap_sync_page_attributes_phys uses wide ubfiz x0 before flush. Built temporary image SHA256cf42e491a1e14d99aa3779658b2bc8eb4c905f17b2d848d532e338b08c0a3a95; verified payload sweetgpumemory=1 and no sweetgpuprobe. Recovery->fastboot->boot returned Sending/Booting OKAY, no partitions flashed. Await visual boot result and return to recovery; pull fresh log as sweetlog-memory-0132 and require inactive HFI Normal-NC=pass plus done result=pass. Hardware test result NOT yet established. Wallpaper/apps/WiFi/BT/camera unchanged.
- HARDWARE RESULT0132: user confirmed iOS loaded and returned to recovery. Fresh sweetlog-memory-0132.txt total215380/flush10 reports inactive HFI Normal-NC=pass root0x10456c000 iova0x60010000; both standalone cycles and done result=pass. No NC validation failure or panic found; SpringBoard andbackboardd execute. This validates the integrated NC HFI allocation/CPU initialization/free path, still no SMMU translation or GMU DMA/execution. Phone recovery.
- IMPORTANT next-step correction: directly parsed saved live-fdt.dtb using tools/gpu-dt-info.py parse_fdt: GPU SMMU compatible qcom,smmu-v2 HAS qcom,disable-atos. Do not proceed with proposed isolated ATS1PR test solely on ID0 capability. Qualcomm source b6410c3f drivers/iommu/arm-smmu.c3194 normally suppresses ATOS when this property exists (selftest exception is not proof of suitability); qsmmuv2_iova_to_phys_hard3982 also uses Qualcomm halt/RESUME_TERMINATE/FSR/stall handling. No such writes performed. FDT has12 attach-impl-defs offset/value pairs; driver qsmmuv2_device_reset applies these under halt. gpu-dt-info.py previously omitted these flags and pairs; now reports them, verified on actual saved FDT. No dma-coherent property; retain explicit page-table cache maintenance. Next work is source-backed persistent SMMU context/lifetime integration honoring these board settings, not an ATOS-only probe. Updated docs/sweet-k6a-gpu.md with current hardware status and source links. Unknown reason for disable flag; do not claim ordinary translated DMA/GPU is prohibited.
- Prepared0133-sweet-smmu-context-lifetime.patch: new xnu/gpu/sweet_smmu_context.c/h programs one externally reserved bank/streamslot/ASID for SID4 or5 through callbacks, exact observed ID geometry,32-bitIOVA/36-bitPA, NC MAIR0, NC tablewalker, polled faults withoutIRQ/stall. No ATS/global initialization or runtime caller. Pin callback obtains published root and retains all backing pages before any MMIO write; ambiguous write/readback/sync failures latch POISONED with retention, no automatic retry/free. Removal routes faults, invalidatesSMR, disablesSCTLR, TLBIASID+boundedTLBSYNC, clearsTTBRs, rechecks quiescence, thenunpins. HFI memory gains serialized mapping references/deferred destroy; release contract requires provenhardwareinactivity. These interfaces do not establish ownership or drain transactions themselves. Caller still must initialize attach-impl-defs/power/clocks and own/reserve all resources.
- Claude reviewed0133 against downloaded pinned Qualcomm sources D:\ios-sweet\research\smmu-b6410c3f: no blocking internal defects reported. Independently confirmed and fixed missing S2CR SHCFG_NSH (0x300), extended 10ms syncbudget to reference500ms boundedbackoff, and added secondquiescence check. qcom,no-asid-retention is absent inactualFDT, supportingchosenTLBIASID; SID4/5 verifiedagain. Rejected any inference that DT groupindices selectphysicalbanks or that unpoweredMMIOautomaticallyreturnsanerror: callbackadapterfault/powerhandling remainsunimplemented. HostASan/UBSan passes all73install/29remove callbackfailures (includingstoresacceptedbeforeerror), timeoutspreservepins, readbackmismatch, conflicts,25bank/slotpairs. HFIactualcomposition/refcounttests pass; target-headerARM64 HFI andfreestandingARM64contextcompilepass. Full126-133 patchseries onverified125fixture, requiredreversechecks andsevenfinalsourcecomparisons pass. 0133 addsBSDbuildentry andCI source/objectchecks. No newphoneboot; latesthardware remains0132pass/recovery.
- 2026-11-05: Full XNU CI 42083130915 SUCCESS for published0133 head71d579a27f4633cf151d1b6513764b1b8df1f27e (main implementation c0ca823). Build, required source/object checks and artifact upload passed. No0133 phone boot because the helper alone had no caller. Phone remains recovery; latest hardware evidence is0132 CPU-memory pass.
- Prepared0134-sweet-k6a-smmu-register-probe.patch: sweet_smmu_k6a.c/h performs exact-ID/all-five-unused-bank preflight, global invalidation/sync, polled CR0 configuration, Qualcomm halt+IDLE and twelve captured attach pairs. Independently compared all12 pairs to actual live-fdt.dtb: exact match. Final sequence matches literal vendor writes: first MICRO=2378 clearsHALT; masters must remain stopped. Removed unproven full readback of other implementation-defined registers; READY does not prove those writes took effect or DMA works. Board model ASan/UBSan passed114 callback failures,500msglobal/30mshalt timeouts, read-onlyIDLE, literalattach/resume and no undocumented reads. FreestandingARM64 board compilation passed.
- New sweet_gpu_smmu_probe.cpp composes board+context with realHFI retained memory. One-shot opt-in sweetgpusmmuinit=1 inside existing CX/memnoc/GMUclock/reset-success branch, mutually exclusive sweetgmuload=1. Requires never-startedCM3/reset1 and GXoff sinceboot, sole earlyboot ownership, freshclock/power/resetchecks; callbacks cannot prove arbitrary DMA drain or catch an external abort/hungMMIO. Captured GX node qcom,poll-cfg-gdscr requires completion at5091010; added POWER_DOWN_COMPLETE bit15 and rejectPOWER_UP_COMPLETE bit16, plus GDSCR softwarecollapse and noHW/SWoverride. Field definitions cross-checked Qualcomm common9af93db gdsc.c; earlier b6410c3f gdsc-regulator lacks this newer poll option and is not evidence for that check. GX reads untested onphone. All allocations/source/artifacts stayD.
- Adapter reservesbank0/slot0/ASID1/SID4/diagnosticIOVA60010000 only after fullboardpreflight, retainsHFI beforeTTBR, installs/checksfaults/removes/syncs, thenreleases. Unexpectedfault/readback/syncfailure keepsmemory indefinitely; noretry, rollback, ATS, firmwarestart or DMAcommands. Stable callbackstorage isstatic. Target-headerARM64 adapter assembly generation passed (added internal ml_io_map declaration because exportedIOKit view hides it). HostASan/UBSan adapter+actualboard/context tests passed27 power/resetrejections, once-onlyexecution, install/remove, allocation/pinfailure, global/contexttimeout andfaultretention; reset-loss tests before removal and after clearing TTBRs also passed with retained memory. Full126-134 patchsequence/requiredreversechecks/tenfinalsourcecomparisons/YAML passed (fixture build/gpu-context-series-g7rrpvyz). New workflow excludes superseded0130iokitconfig/0133bsdconfig reversehunks and checks exactbuildentries separately.
- Claude board-helper review informed removal of undocumented readbacks and literal attachorder. Later runtime-adapter review was NOT completed: Claude service reported its safety classifier halted response; no approval/verdict obtained, do not claim reviewed. Independent source analysis/compiler/model checks above remain the evidence. 0134 not yet published/full-built/booted at this checkpoint. User away, no physical action requested. tools/mkiosroot.sh dirty user change preserved untouched. Wallpaper/apps/WiFi/Bluetooth/camera unchanged and GPU acceleration absent.
- Published0134 as e35d707132b9881221475c108fdc6e532af8ab69 (main575c824); Intel XNU CI https://github.com/nonrootus/ios-sweet/actions/runs/42089630500 started2026-11-05T19:00UTC. Runtimeadapter tests including resetloss before removal/afterTTBRclear passed with pinsretained. Prepared build/build-smmu-probe-image.py and boot-smmu-probe.py; temporaryimage enables acquiredpower/clocks/status+smmuinit only, noTCMload/ATS/GMUstart. CI/result/download/boot pending.
- CI0134 run42089630500 SUCCESS (head e35d707): Build19:00:32-19:12:18UTC; final-source/linked-marker checks passed19:12:25. Selectively downloaded onlykernel6511949compressedbytes +SHA file to D:/ios-sweet/build/xnu-memory-probe-42089630500. CRC+SHA passed; kernel SHA256 ec0084b875cc0f363749e1c09fea7db08424ca4cf632f0bb846be4fcfaae68b9. Actualkernel has _sweet_gpu_smmu_probe andbothentry/retentionmarkers; pmap highmemorycachefix disassembles UBFIZ x0,x0,#14,#32. Temporary image419db042ca74323109b67cc5ba06a7e996bf95b8edb13fcee6c0f2fcd8641964 (16860KB) built onD with build-smmu-probe-image.py. Recovery->fastboot->temporaryboot succeeded: Sending0.396sOKAY/Booting0.153sOKAY,total0.560s. No partition flash. Device iOS/SMMU outcome NOT observed yet. Asked user viaasync toreturnrecovery afterboot and reportscreen; they are away. Next: verify recoveryserial, run pull-memory-probe-log.py smmu-0134, inspect SWEET GPU SMMU prepare/install/remove/done plusGXFSM/precondition/errorlines, do not equate iOSboot withSMMUpass.
- Read-only live filesystem follow-up whileCIbuilt: research/sweet-k6a-live-capture-20261027/app-registry-20261106.txt. pkd/lsd/installd launchd declarations exist and no matching disabled overrides. MobileInstallation MigrationInfo matches20H392; LinkedParentBundles has emptylinkedParentBundles. No PlugInKit/LaunchServices registry names found in scopedvar/db/mobileCaches and boundedvar/folders search; absence in these paths is notproofnoneexists. FUSE+loopmountedro, phoneuserdataopenedO_RDONLY, inspectioncleanupcompleted beforeboot. Only578-byte reader pushed to recovery/tmp (RAM). No apps/wallpaper/filesystem edits. Plan stages32apps aspreviouslydocumented; actualpromotion remainsundeployed.
- Additional source check fornextGMUstep: Linuxv6.12 a6xx_gmu.c memory_alloc uses uncached0x60000000+PAGE_SIZE..0x80000000 fornonfixedbuffers andfixed dummy0x60000000; legacyinitialization alsoallocatesdebug/log beforeHFI. CurrentHFIobject maps onlyfivequeuepages, so cannot startfirmware bymerelykeeping0134contextactive. Need ownedadditionalbuffers, disjointIOVAs, commonpinlifetime, correctSID/privilegeandRPMh/powerinitialization plusactualdevicevisibility validation. NoGMUstartimplemented. RawGitHublocaldownload hitHTTP429; webprimarysourceavailable, empty research/linux-v6.12-gmu directory doesnotcontainverifiedsavedfiles.
- 2026-11-06 local: user confirmed0134 iOSloaded andphonebackinrecovery. Pulled fresh smmu-0134.bin/.txt viaread-only tailcapture, ringtotal218729flush10. CXenable0/memnocowned1/GMUclock200stage3 allpass; CM3reset1,busy/init/retention0. NewGXread00222001, completion00088400 satisfiedcollapse/softwarecontrol/down-complete guards. Actualtest stopped BEFORE anyTTBR/rootinstallation: prepare rc=-5 state2 stage1 offc00 value000200ff afterattemptedS2CR0=00020300. No panicseen;execSpringBoard/backboardd. Hence0134 delivery/iOSboot PASS, SMMUpreparation FAIL, DMA/GPU unstarted. Phone recovery.
- Root-cause work: Linuxv6.12 arm-smmu-qcom.c qcom_smmu_cfg_probe describes firmware ignoringFAULTwrites, but qcom_adreno_smmuv2_cfg_probe doesnot use that genericquirk. This is a hypothesis, not diagnosed firmware behavior; do not claimallwritesblocked/securitylock. InitialallSMRinvalid/allS2CRFAULT already satisfyboardprecondition, so normalizingunusedCBNDX/shareability was unnecessary. Preparing0135 toleavealreadyfaultingS2CRsunchanged. NoBYPASSwrite/securitycall. Keepstrictlatertranslationinstall/removalchecks; model willensureignoredFAULTduringremoval stillpoisonsandretainsmemory.
- 0135 local validation passed: boardASan/UBSan99callbackfailures; adaptermodel27powerguardsplusignoredFAULTduringremoval keepsrootpinned/statePOISONED (not treated as successfulisolation); freestandingARM64boardcompile; full126-135 apply/reverse/final10sources/YAML in build/gpu-context-series-nhnupr5i. OnlyinitialredundantFAULTwritesremoved, noBYPASS orlooseningruntimeinstall/remove. Docsupdatedwithactual0134failure.
- 2026-11-06: published0135 head ebba5457410f9cb7c4df57507a53be2858a9dcef (main e516686). Full Intel XNU CI https://github.com/nonrootus/ios-sweet/actions/runs/42190567655 started08:50:29UTC. Device test pending; lastconfirmedphone0134 iOSboot/recovery, S2CRinitializationfailure recorded above.
- While0135CIran, installed qemu-utils with3smallruntime dependencies inD-backedWSL (2.273MBdownload,11.5MBinstalled) totrycompactoffline appoverlay. build/prepare-apps-overlay.py created build/apps-overlay-tf54tpmg/apps-repair-base-prototype.qcow2 (196864bytes) backed byexisting repair.img, QEMUbasefdverifiedO_RDONLY. HFSforcedread-only despite requestedrw; assertionstopped BEFOREpromotion, noapps/fileschanged. Didnotforcewritablemount. Cleanup initiallyreportedFUSEbusy, butsubsequentfindmnt/losetup/pgrep showednooverlaymount,loop,orqemudaemon remaining. Treat this asFAILEDprototype, notbootableappfix; repairbaselineisolderthancurrentmg-nowait phoneimage. NeedproperHFSimageediting/reconstruction beforeanydeployment; phoneuntouched.
- 0135 fullXNU CI42190567655 SUCCESS (Build completed2026-11-06T09:04:18UTC, finalsource/kernelchecks09:04:21). Selectivekerneldownload6512140compressedbytes CRC/SHAverified fromhead ebba5457410f9cb7c4df57507a53be2858a9dcef. KernelSHA256 6afb78995f22644d1797029c8e3b1c65b2fdd0883b6dea1ad76cf155a038792d. Built D:/ios-sweet/build/xnu-memory-probe-42190567655/shim-boot-smmu-register.img SHA256 97e5e947b4d10da4f906b3e1674e366c2cb5c9e0416f3b89f374206587d68b61. Phoneconfirmedrecoveryviaadb; temporaryfastbootboot Sending0.404sOKAY/Booting0.152sOKAY,total0.569s. No partitionflash. Askeduser toreturnrecovery after1-2min andreportiOS. Deviceoutcome pending. NEXT: pull-memory-probe-log.py smmu-0135, then inspect SWEET GPU SMMU prepare/install/remove/done/lastoffset lines. Do notclaim0135hardwarepass justbecauseiOSboots. No externalreview verdictfornewadapter; currentevidencecompiler/models/CI and0134actualfailure.

- 2026-11-06: user confirmed0135 iOSloaded/recovery. Fresh read-only smmu-0135.bin/.txt ringtotal212882flush8: boardprepare rc0 state1 stage5 MICRO2378; contextinstall rc0 state1 root10465c000 SMR80000004. GFSR0/CB_FSR400 was wrongly classified as fault; no removal attempted, pagesretained, done-3. ARM IHI0062D.c16.5.9 pp299-301 confirms FORMAT[10:9]=2 is readonly AArch64 metadata generated from CBA2R.VA64/TCR.EAE, notfault. Corrected earlier user-facing fault interpretation. This proves observed register preparation/install, not translatedDMA/rendering. Phone recovery.
- Prepared0136-sweet-smmu-fsr-format.patch: adapter separates FORMAT600 from fault/stall maskc00001fe, conservatively rejects unexpectedreservedbits and globalfault/readerrors, logsraw/format/fault/unknown. Strictremove/retention unchanged. Model now derivesFORMAT fromCBA2R/TCR; defaultsuccessreads400, all30nonFORMATbits plusglobalfault retainmemory; old injectedbit0 wasreserved, nowcoversactualTF/PF/etc. ASan/UBSan model passed including27powerguards/timeouts/ignoredFAULTremoval; target-headerARM64assemblycompile passed; full126-136 apply/reverse/tenfinalsourcechecks/YAML passed fixturegpu-context-series-y7yvd5hb. Workflow excludes superseded0134adapter reversehunk, checks0136fully andfinaladaptercmp. No0136fullCI/device testyet. Userdirtytools/mkiosroot.sh untouched. Noapps/wallpaperfix deployed.
- Published0136 main461da4d/build69cd66edd6558841e9590ce9eb3e915002bb58dd, CI42194071074. Before device test, primary ARM IHI0062D.c9.6.23 pp225-226 established a second independent readback bug: S2CR TYPE2 has noCBNDX/SHCFG, so wholeword20300 equality is unjustified. Prepared0137: request20000, require TYPEexact2 andnotallones; TRANS/BYPASS/reservedTYPE3 still fail beforeSMR/TTBRchanges. No bypass/securitycalls. All subsequentdisable/sync/TTBRclear/quiescentguards unchanged. Model defaultFAULTreadback200ff, acceptedreservedlowbitvariants; ignoredFAULTleavingTRANS retainsmemory. ContextASan/UBSan73install/29removalfailurepoints+25bank/slotpairs/newTYPEcases passed; composedadapterASan/UBSan passed; ARM64freestandingcontextcompile passed; full126-137 apply/reverse/tenfinalsources/YAML passedgpu-context-series-xuy6iyjs. Combining0136+0137 fornextphoneboot toavoidextrauserreboot; 0136-onlyCI maybesuperseded.
- Publishedcombined0136+0137 main d892239/build723c9bcf1fdcea7a45cb2059524eae1e4379537d; CI42194748065 started09:25:43UTC on2026-11-06. Older0136-onlyrun42194071074 cancelled withgh toavoidwastedrunner. Phoneconfirmedrecovery. Awaitfullbuild/sourcechecks thenselectivedownload/buildtemporaryimage/fastbootboot.
- Claude completed NEW0136/0137 register-mask/lifetime review: agreesFORMAT600/faultc00001fe masks and S2CRTYPE-only checkwithEXIDS0; no failed-disablepathunpins. IndependentARMspec/localtests confirm. SuggestedcheckingFORMATexact2, rereadingfaults beforeunpin and globalTLBsync forstrongerfutureteardown. Notimplementedinthisregister-onlynever-started-mastertest; currentquiescentcontractcannotbeusedasgenericDMA-drainproof. Earlier0134adapterreview remainsincomplete, notretroactivelyapproved.
- Offlineappsprototype SUCCEEDED using D/build/prepare-apps-overlay.py revisedcleanup/explicitloopdetach. Base repair.imgheaderHXv5 attributes80002100 cleanunmounted/notinconsistent,lastH+Lx; journalflags5(inFS+needsinit), all8MiBjournalzero. Only thispristineneverbootedbase permittedLinuxforcewrite INSIDEQCOWoverlay withverifiedbaseO_RDONLY; fsck-f-n passedbefore/after. D/build/apps-overlay-0m05oump/apps-repair-base-prototype.qcow2 2424832bytes: all32stagedbundlesrenamedintoApplications, inode/uid/gid/mode/InfoSHA preserved; qemu-imgcheckpassed, cleanupcompleted, basemetadataunchanged. This isstillOLDERrepairbaseline, NOTcurrentworkingmg-nowaitphoneimage, noLaunchServicesregistration/devicebootvalidated. Neverapplyasdiffagainstmutatedphone. Originalfailedtf54tpmgprototypeunchanged. Toavoid16GBcopyforusableworkingbase, futureoptionreadonlyAndroidsparseFUSEviewofexistingmg-nowait.simg+QCOWoverlay; notimplemented.
- Working-baseappsprototype alsoSUCCEEDED: build/sparse-view.py exposesoriginal D/artifacts/ios16-root-sweet-k6a-20H392-mg-nowait.simg O_RDONLY as16GBrawviewwithoutcopy (27826RAW/FILLsegments,physical12145201660). ParserfollowsAOSP sparse_format.h; onlyv1zeroimagechecksum/noCRCchunks supported, DONT_CAREzero forofflineexpansion, bounds/headerchecks, source size/mtimemonitor, readonlyFUSE. Syntheticboundary/unalignedcrosschunk/extendedheader/malformedtests passed. No fullcontentchecksumverificationclaim. build/prepare-working-apps-overlay.py mountswrapperandcallsrestrictedpristinejournalprototype. Result build/apps-overlay-mz0jpra4/apps-nowait-base-prototype.qcow2 2424832bytes; same32bundlespromoted, metadata/InfoSHA preserved, fsckbefore/after andqemucheckpassed. Baseunchanged; no16GBrawcopy/newdownload; phoneuntouched. QCOWbacking isvirtual /mnt/d/ios-sweet/build/sparse-nowait-base/root.img: MUSTremountsameoriginalsparseview beforeopeningoverlay; wrapperaswrittencreatesnewprototype, notreaderofexistingoverlay. NoLaunchServicesregistration/bootvalidation; NOTanappfixinstalledonphone. DoNOTflashoverlayasdeltaagainstcurrentphone (currentuserdatahaschanged).

- 0136+0137 CI42194748065 SUCCESS: Build09:26:13-09:42:08UTC, requiredsource/kernelchecks09:42:13. Selective6512909compressedbytes CRC/SHAverified forhead723c9bcf1fdcea7a45cb2059524eae1e4379537d. Kernelbf0bca5a5069dd86399de807e4b533bfbf77deb3b0890c2d7de1513458a5230a; newraw/format/fault/unknownstatusmarker andremove/retentionstringspresent. Temporaryimage3297da124ce539cfc1b78b12893b09a908f18e90d00fe7e2c6e88a090fc4baea builtandbooted viaexplicitserial: Sending16860KB0.406sOKAY/Booting0.151sOKAY,total0.568s. No partitionflash. Userasked toreturnrecoveryafter1-2minutes/reportiOS; resultpending. Nextpull smmu-0137 log, donotclaimDMA/GPUaccelerationsuccess.

- 0137 freshhardwarelog captured read-only afteruseriOS/recoveryconfirmation: total231899flush32, prepare0/install0, global0/context400format2faults0unknown0; removal-5state3retained1offc00value300. Confirms TYPEFAULTrequest20000 didnotchange activeTRANS inthisboot. Existingstrictretentionworked. No automaticrollback/retry; phone recovery. Investigating explicitfresh-boot inactiveSMR invalidation withverifiedUSFCFG1/CLIENTPD0/EXIDENABLE0+global/local sync andfaultchecks; requestedClaudeplanreview. NoactualnewMMIOyet.

- Prepared0138-sweet-smmu-inactive-unmatched-teardown.patch as a NEW API, notfallback/retryofPOISONEDcontext. ExistingFAULTremove staysstrict. Earlybootprobe selectsremove_unmatched beforewrites, requiringnever-startedmasters/fullcontrollerownership. VerifyexactIDs, CR0mask40b=402 (clientenabled,EXIDoff,unmatchedfault+abort), onlyownSMRvalid, ownS2CRTRANSbank/SCTLRexpected, global/CBfaultsabsentexcludingFORMAT. MarkPOISONED; SMR0exactreadback->globalTLBSYNC bounded500ms->verifyallSMR0/policy->SCTLR0->TLBIASID/local sync->TTBRs0->freshquiescent/allSMR0/policy/faults/barrier->unpin. NoS2CR/BYPASS/securitycall/firmwarestart. S2CRremainsTRANSbehindinvalidSMR; controller/slotreserveduntilreset, notgeneralDMAteardown. HostASan/UBSan73install/29FAULTremove/68unmatchedremovecallbackfailures,25bank-slotcombos,preconditionerrors,ignoredSMR,global/localtimeouts,latefault/policy/newstreamretentionpassed. Composedadaptertests27powerguards/all30nonFORMATbits/resetloss/newteardown/ignoredFAULTwithoutwritingFAULT passed. ARM64contextcompileandtarget-headeradaptercompilepassed. Full126-138 patchapply/reverse/10finalsource/YAMLpassed;0136reversechecksupersededby0138+finaladaptercmp;0133headerreversehunkexcludedandfinalheadercmpretained. Claudeplanreview DIDNOTcomplete: serviceclassifierstoppedresponse, noverdict; noretry. No0138phoneactionyet.

- Published0138 main23130e9/build777f02f26dde3f940da3e9a3b35ffbd99e78ed8b; CI42199702714 started2026-11-06T10:03:32Z. Fullbuild/deviceoutcome pending. Final localpatchfixturegpu-context-series-5sxypkre.

- While0138CIruns, saved primary Linuxv6.12 a6xx_gmu.c/h,a6xx_hfi.c/h,adreno_gpu.h viaKernelGooglesource into research/linux-v6.12-gmu (previouslyempty). Saved pinnedmsm b6410c3f kgsl_gmu.c/h,kgsl_hfi.c/h,adreno_a6xx_gmu.c,adreno.h into research/smmu-b6410c3f. adreno_a615_family explicitlyincludesA618. kgsl_gmu allocatesHFI/dump/log/caches/dummy inGMU_CONTEXT_KERNEL; re-parsedactualFDT gmu_kernel iommus[461,5],gmu_user[461,4]. Thus currentSID4diagnosticmustnotbecomeactualGMUfirmwaremapping. Legacyfallbackno-prealloc: caches240KiB@4000/44000, dummy4Kpriv, HFI5pages, dump16K, log4Kpriv; currentPTEalwaysUNPRIVcannotexpressallreferenceattrs. gmu_init load_firmware/cache_finalize precedesmemory_probe, so firstuncachedallocdummy60000000 absentprealloc. Linuxv6.12differentrecipe: do not blindlymix. PinnedKGSLfourqueueheader matcheslocalIDs/sizes/offset224, butKGSLleaveswatermarks/RXrequest0 whilelocalhelperputs1 likeLinux2queuerecipe. Resolveprofilebeforeexecution; nosuchfieldsusedby0138inactiveSMMUtest. Docsupdated, noadditionalruntimechange.

- Exact stock source follow-up during0140CI: adreno-gpulist.h A618 uses a618_gmu.bin and GMU major1/minor8 (not newer Qualcomm1.7). Existing offline sweet_hfi_v1_version encoder currently emits0x100a0000 (1.10); before any HFI exchange, make this explicit target profile/1.8 and test response handling. It is NOT called by0140. Stock kgsl_gmu_core.h GMU_VERSION encodes major<<28/minor<<16. Stock memory probe itself allocates the fixed map before firmware load; it does not use the newer metadata-preallocation recipe. Additional pinned headers saved by read-stock-gmu-source.py: kgsl_gmu_core.h,a6xx_reg.h,adreno_a6xx.h,adreno.h. Before first CM3 release, source a6xx_gmu_fw_start needs TCM retention, GPU PDC/RSC sequences, TCM image, fresh init-result clear, bootmode, HFI QTABLE address/info, fence/config/chipid/log and power configuration. Firmware readiness is exact BABEFACE, then separate HFI_CTRL_INIT/STATUS handshake. Actual register access/owned mappings/power and post-start stop/drain still need implementation and validation; 0138 inactive teardown contract must NOT be used after a producer has run. Keep allocations retained through any ambiguous start result. Current test never invokes these paths.
