param([string]$File, [string]$Remote = '/var/mobile/Documents', [int]$PieceMB = 5, [int]$WaitMinutes = 40)
# Copy a big file to the phone over USB SSH in pieces, retrying each piece until it gets through
# (the RNDIS link drops now and then and comes back), then join and check it on the phone.
$ErrorActionPreference = 'Continue'
$k = 'D:\ios-sweet\keys\sweet_ed25519'
$name = Split-Path $File -Leaf
$parts = Join-Path (Split-Path $File) ("$name.parts")
New-Item -ItemType Directory -Force $parts | Out-Null
$bytes = [IO.File]::ReadAllBytes($File)
$size = $PieceMB * 1MB
$n = [int][Math]::Ceiling($bytes.Length / $size)
for ($i = 0; $i -lt $n; $i++) {
    $len = [Math]::Min($size, $bytes.Length - $i * $size)
    $chunk = New-Object byte[] $len
    [Array]::Copy($bytes, $i * $size, $chunk, 0, $len)
    [IO.File]::WriteAllBytes((Join-Path $parts ('p{0:D3}' -f $i)), $chunk)
}
$sha = (Get-FileHash -Algorithm SHA256 $File).Hash.ToLower()
"$name : $($bytes.Length) bytes, $n pieces, sha256 $sha"
$end = (Get-Date).AddMinutes($WaitMinutes)
function Wait-Link {
    while ((Get-Date) -lt $end) {
        if (Test-NetConnection 192.168.137.2 -Port 22 -InformationLevel Quiet -WarningAction SilentlyContinue) { return $true }
        Start-Sleep 5
    }
    return $false
}
for ($i = 0; $i -lt $n; $i++) {
    $p = Join-Path $parts ('p{0:D3}' -f $i)
    $done = $false
    for ($try = 1; $try -le 20 -and -not $done; $try++) {
        if (-not (Wait-Link)) { 'link did not come back'; exit 3 }
        & scp -q -i $k -o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=5 $p ("root@192.168.137.2:$Remote/$name.p" + ('{0:D3}' -f $i))
        $done = ($LASTEXITCODE -eq 0)
        if (-not $done) { "piece $i try $try failed"; Start-Sleep 5 }
    }
    if (-not $done) { "piece $i never got through"; exit 4 }
    if ($i % 4 -eq 3 -or $i -eq $n - 1) { "piece $($i + 1)/$n done at $(Get-Date -Format HH:mm:ss)" }
}
if (-not (Wait-Link)) { 'link did not come back'; exit 3 }
$check = & ssh -i $k -o BatchMode=yes root@192.168.137.2 "cd $Remote && cat $name.p[0-9][0-9][0-9] > $name && rm -f $name.p[0-9][0-9][0-9] && (shasum -a 256 $name 2>/dev/null || sha256sum $name)"
"phone: $check"
if ("$check" -notmatch $sha) { 'checksum MISMATCH'; exit 5 }
'checksum ok'
Remove-Item -Recurse -Force $parts
