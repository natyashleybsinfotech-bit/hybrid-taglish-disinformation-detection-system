$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$server = Join-Path $projectRoot 'tools\mariadb-11.4.13-winx64\bin\mariadbd.exe'
$dataDir = Join-Path $projectRoot 'tools\mariadb-data'
$configFile = Join-Path $dataDir 'my.ini'

if (-not (Test-Path -LiteralPath $server) -or -not (Test-Path -LiteralPath $configFile)) {
    throw 'The local MariaDB portable instance has not been initialized.'
}
if (Get-Process mariadbd -ErrorAction SilentlyContinue) {
    Write-Output 'MariaDB is already running.'
    exit 0
}

$arguments = "--defaults-file=`"$configFile`" --bind-address=127.0.0.1 --skip-name-resolve"
$process = Start-Process -FilePath $server -ArgumentList $arguments -WorkingDirectory $dataDir `
    -RedirectStandardError (Join-Path $dataDir 'server-stderr.log') `
    -RedirectStandardOutput (Join-Path $dataDir 'server-stdout.log') `
    -WindowStyle Hidden -PassThru
Set-Content -LiteralPath (Join-Path $dataDir 'server.pid') -Value $process.Id
Write-Output "MariaDB started with PID $($process.Id)."
