param([int]$Minutes = 20)
$ErrorActionPreference = 'Stop'
$out = 'D:\ios-sweet\build\a618-0181-device'
[IO.Directory]::CreateDirectory($out) | Out-Null
$stamp = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')
$path = Join-Path $out ('live-' + $stamp + '.log')
$end = [DateTime]::UtcNow.AddMinutes($Minutes)
$match = 'SWEET CA: renderer RAM disk|XR10|w30r|packing=|SWEET SURF: b3a8|b3a8 readback|b3a8 IOSurface|b3a8 visible pixels|SWEET CA: (hardware submit|BO recycle|BO pool|submit disabled)|CRASH backboardd|panic\(cpu|FD618|exec SpringBoard'
$buffer = [byte[]]::new(8192)
$stream = [IO.File]::Open($path, 'CreateNew', 'Write', 'Read')
Write-Output "Waiting for Sweet USB console. Log: $path"
try {
    while ([DateTime]::UtcNow -lt $end) {
        $devices = @(Get-PnpDevice -PresentOnly -Class Ports -ErrorAction SilentlyContinue | Where-Object {
            $_.InstanceId -match '^USB\\VID_1209&PID_000(?:2(?:&|\\)|3&MI_00\\|4&MI_02\\)' -and $_.FriendlyName -match '\(COM\d+\)$'
        })
        if ($devices.Count -ne 1) {
            Start-Sleep -Seconds 2
            continue
        }
        $port = [regex]::Match($devices[0].FriendlyName, '\((COM\d+)\)$').Groups[1].Value
        $reader = [IO.Ports.SerialPort]::new($port,115200,[IO.Ports.Parity]::None,8,[IO.Ports.StopBits]::One)
        $reader.ReadTimeout = 1000
        $reader.DtrEnable = $true
        $pending = ''
        try {
            $reader.Open()
            Write-Output "Reading Sweet console on $port"
            while ([DateTime]::UtcNow -lt $end) {
                try { $n = $reader.Read($buffer, 0, $buffer.Length) }
                catch [TimeoutException] { continue }
                if ($n -eq 0) { continue }
                $stream.Write($buffer, 0, $n)
                $stream.Flush()
                $pending += [Text.Encoding]::ASCII.GetString($buffer, 0, $n)
                $rows = $pending.Split([char]10)
                $pending = $rows[$rows.Length - 1]
                for ($i = 0; $i -lt $rows.Length - 1; $i++) {
                    if ($rows[$i] -match $match) {
                        $line = $rows[$i].TrimEnd()
                        Write-Output $line.Substring(0,[Math]::Min($line.Length,300))
                    }
                }
                if ($pending.Length -gt 65536) { $pending = '' }
            }
        } catch [IO.IOException] {
            Write-Output 'Sweet console disconnected. Waiting for reconnect.'
            Start-Sleep -Seconds 2
        } finally {
            $reader.Dispose()
        }
    }
} finally {
    $stream.Dispose()
}

