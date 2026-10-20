$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$client = Join-Path $projectRoot 'tools\mariadb-11.4.13-winx64\bin\mariadb-admin.exe'
$localEnv = Join-Path $projectRoot 'backend-api\.env.local'
$passwordLine = Get-Content -LiteralPath $localEnv | Where-Object { $_ -like 'SURI_LOCAL_DB_ROOT_PASSWORD=*' } | Select-Object -Last 1
if (-not $passwordLine) { throw 'Local MariaDB root password is not configured.' }
$password = $passwordLine.Substring($passwordLine.IndexOf('=') + 1)
& $client --host=127.0.0.1 --port=3306 --protocol=tcp --skip-ssl --user=root "--password=$password" shutdown
if ($LASTEXITCODE -ne 0) { throw 'MariaDB shutdown failed.' }
Write-Output 'MariaDB stopped.'
