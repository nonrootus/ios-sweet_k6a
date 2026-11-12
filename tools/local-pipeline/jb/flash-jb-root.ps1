param([string]$BootVersion, [int]$WaitMinutes = 30)
# Flashes the jailbroken iOS root into userdata (owner approved, 2026-11-11), then boots image
# a618-$BootVersion-device temporarily. Only userdata is written. Run with the phone in recovery.
$ErrorActionPreference = 'Stop'
$Sdk = (Join-Path $env:LOCALAPPDATA 'Android\Sdk\platform-tools')
$image = 'D:\ios-sweet\work\jb-root\ios16-root-sweet-k6a-20H392-jb1.simg'
$expected = (Get-Content "$image.sha256" -Raw).Split(' ')[0].Trim()
$boot = "D:\ios-sweet\build\a618-$BootVersion-device"
if (-not (Test-Path "$boot\boot.py")) { "no boot image $BootVersion"; exit 5 }
"checking image hash..."
$actual = (Get-FileHash -Algorithm SHA256 $image).Hash.ToLower()
if ($actual -ne $expected) { "image hash $actual != $expected"; exit 6 }
$end = [DateTime]::UtcNow.AddMinutes($WaitMinutes)
$serial = $null
$inFastboot = $false
while ([DateTime]::UtcNow -lt $end) {
    # Already in fastboot (exactly one target): the product and size checks below still decide.
    $fbNow = @(& "$Sdk\fastboot.exe" devices | Where-Object { $_ -match '\sfastboot$' } | ForEach-Object { ($_ -split '\s+')[0] })
    if ($fbNow.Count -gt 1) { 'more than one fastboot target: not choosing'; exit 3 }
    if ($fbNow.Count -eq 1) { $serial = $fbNow[0]; $inFastboot = $true; break }
    $rec = @(& "$Sdk\adb.exe" devices | Where-Object { $_ -match '\srecovery$' } | ForEach-Object { ($_ -split '\s+')[0] })
    if ($rec.Count -eq 1) { $serial = $rec[0]; break }
    if ($rec.Count -gt 1) { 'more than one recovery target: not choosing'; exit 3 }
    Start-Sleep -Seconds 3
}
if (-not $serial) { 'no recovery or fastboot target appeared'; exit 2 }
if ($inFastboot) {
    "target already in fastboot"
} else {
    $product = (& "$Sdk\adb.exe" -s $serial shell getprop ro.product.device).Trim()
    if ($product -ne 'sweet') { "recovery target is $product, not sweet"; exit 4 }
    "sweet in recovery; rebooting to the bootloader"
    & "$Sdk\adb.exe" -s $serial reboot bootloader
    $ok = $false
    for ($i = 0; $i -lt 60; $i++) {
        Start-Sleep -Seconds 2
        $fb = @(& "$Sdk\fastboot.exe" devices | Where-Object { $_ -match "^$serial\s+fastboot" })
        if ($fb.Count -eq 1) { $ok = $true; break }
    }
    if (-not $ok) { 'phone did not appear in fastboot'; exit 7 }
}
# fastboot prints getvar answers and progress on stderr; under 'Stop' PowerShell 5.1 turns that into
# a terminating error, so from here on exit codes decide.
$ErrorActionPreference = 'Continue'
$prod = (cmd /c "`"$Sdk\fastboot.exe`" -s $serial getvar product 2>&1" | Select-String 'product:' | Select-Object -First 1).ToString()
$size = (cmd /c "`"$Sdk\fastboot.exe`" -s $serial getvar partition-size:userdata 2>&1" | Select-String 'partition-size' | Select-Object -First 1).ToString()
"$prod / $size"
if ($prod -notmatch 'product:\s*sweet' -or $size -notmatch '0x38405FB000') { 'unexpected product or userdata size: not flashing'; exit 8 }
"flashing userdata (about 7 minutes; do not unplug)"
& "$Sdk\fastboot.exe" -s $serial -S 512M flash userdata $image
"flash exit=$LASTEXITCODE"
if ($LASTEXITCODE -ne 0) { exit 9 }
"booting $BootVersion"
Start-Process -WindowStyle Hidden -FilePath powershell.exe -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "$boot\read-usb.ps1", '-Minutes', '20')
Start-Sleep -Seconds 3
& "$Sdk\fastboot.exe" -s $serial boot "$boot\shim-boot-sweet-a618-gpu.img"
"boot exit=$LASTEXITCODE (if it hangs at Sending: re-enter fastboot by hand, Power + Volume down, then run boot.py)"
