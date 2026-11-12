param([string]$Version, [int]$WaitMinutes = 10)
# Waits for exactly one sweet in recovery, starts the USB reader, then boots the temporary image. No flashing.
$ErrorActionPreference = 'Stop'
$Sdk = (Join-Path $env:LOCALAPPDATA 'Android\Sdk\platform-tools')
$dir = "D:\ios-sweet\build\a618-$Version-device"
$end = [DateTime]::UtcNow.AddMinutes($WaitMinutes)
$serial = $null
while ([DateTime]::UtcNow -lt $end) {
    $rec = @(& "$Sdk\adb.exe" devices | Where-Object { $_ -match '\srecovery$' } | ForEach-Object { ($_ -split '\s+')[0] })
    if ($rec.Count -eq 1) { $serial = $rec[0]; break }
    if ($rec.Count -gt 1) { 'more than one recovery target: not choosing'; exit 3 }
    Start-Sleep -Seconds 3
}
if (-not $serial) { 'no recovery target appeared'; exit 2 }
$product = (& "$Sdk\adb.exe" -s $serial shell getprop ro.product.device).Trim()
if ($product -ne 'sweet') { "recovery target is $product, not sweet"; exit 4 }
"sweet in recovery at $([DateTime]::UtcNow.ToString('HH:mm:ss'))"
Start-Process -WindowStyle Hidden -FilePath powershell.exe -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "$dir\read-usb.ps1", '-Minutes', '15')
Start-Sleep -Seconds 5
python "$dir\boot.py" $Version
"boot exit=$LASTEXITCODE"
