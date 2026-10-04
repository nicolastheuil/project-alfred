param(
    [Parameter(Mandatory)][string]$SshHost,
    [Parameter(Mandatory)][string]$SshUser,
    [Parameter(Mandatory)][string]$IdentityFile,
    [Parameter(Mandatory)][string]$KnownHostsFile,
    [ValidateRange(1,65535)][int]$SshPort = 22,
    [ValidateRange(1024,65535)][int]$LocalPort = 9119,
    [switch]$CopySessionToken
)
$ErrorActionPreference = 'Stop'
if ($SshHost -notmatch '^[A-Za-z0-9._:-]+$' -or $SshUser -notmatch '^[A-Za-z0-9._-]+$') {
    throw 'Invalid SSH host or user.'
}
$keyPath = (Get-Item -LiteralPath $IdentityFile).FullName
$hostKeysPath = (Get-Item -LiteralPath $KnownHostsFile).FullName
$sshExe = (Get-Command ssh -CommandType Application).Source
$sshArguments = @('-i', $keyPath, '-o', "UserKnownHostsFile=$hostKeysPath", '-o', 'StrictHostKeyChecking=yes',
    '-o', 'IdentitiesOnly=yes', '-o', 'BatchMode=yes', '-o', 'ServerAliveInterval=30',
    '-o', 'ServerAliveCountMax=3', '-o', 'ExitOnForwardFailure=yes', '-p', "$SshPort", '-l', $SshUser)
if ($CopySessionToken) {
    $tokenText = & $sshExe @sshArguments $SshHost 'sudo -n /usr/bin/cat /etc/alfred/desktop.env'
    if ($LASTEXITCODE -ne 0) { throw 'Could not read the private session token through SSH.' }
    $match = [regex]::Match(($tokenText -join "`n"), '(?m)^HERMES_DASHBOARD_SESSION_TOKEN=([^\r\n]+)$')
    if (-not $match.Success) { throw 'Session token is unavailable.' }
    Set-Clipboard -Value $match.Groups[1].Value
    $tokenText = $null
    $match = $null
    Write-Output 'Session token copied to the clipboard; paste it only into Hermes Desktop.'
}
$processInfo = [System.Diagnostics.ProcessStartInfo]::new()
$processInfo.FileName = $sshExe
$processInfo.UseShellExecute = $false
$processInfo.CreateNoWindow = $true
foreach ($arg in ($sshArguments + @('-N', '-L', "127.0.0.1:${LocalPort}:127.0.0.1:9119", $SshHost))) {
    $processInfo.ArgumentList.Add($arg)
}
$tunnelProcess = [System.Diagnostics.Process]::Start($processInfo)
Start-Sleep -Milliseconds 800
if ($tunnelProcess.HasExited) { throw 'SSH tunnel failed; check the local port and host key.' }
Write-Output "SSH tunnel PID $($tunnelProcess.Id); Desktop URL http://127.0.0.1:$LocalPort"
Write-Output 'Closing Desktop leaves the server running. Stop this local SSH PID to close the transport.'
