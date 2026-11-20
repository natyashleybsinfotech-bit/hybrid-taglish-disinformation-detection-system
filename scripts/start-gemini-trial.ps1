$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$env:SURI_SCREENING_MODE = 'gemini'
$env:SURI_MODEL_WARMUP = 'false'
$env:SURI_MEDIA_WARMUP = 'true'
Write-Output 'Preparing speech and image-text engines before accepting survey checks...'
Push-Location (Join-Path $projectRoot 'backend-api')
try { & (Join-Path $projectRoot '.venv\Scripts\python.exe') -m uvicorn src.app:app --host 127.0.0.1 --port 8000 --workers 1 --no-access-log }
finally { Pop-Location }
