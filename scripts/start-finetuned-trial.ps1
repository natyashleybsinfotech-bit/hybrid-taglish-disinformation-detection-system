param([switch]$RawModelOnly)
$ErrorActionPreference = 'Stop'
$env:SURI_SPEECH_PROVIDER = 'local'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
$artifactPath = Join-Path $projectRoot 'backend-api\models\local-trials\suriph-finetune-6a35c6d4a2a0'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'The verified model Python environment is missing.' }
$env:SURI_MODEL_PROFILE = 'suriph-finetune-6a35c6d4a2a0'
$env:SURI_MODEL_ARTIFACT_DIR = $artifactPath
$env:SURI_MODEL_DEVICE = 'cpu'
$env:SURI_MODEL_WARMUP = 'true'
$env:SURI_SCREENING_MODE = 'model'
$env:SURI_MODEL_AUTHORITATIVE = $RawModelOnly.IsPresent.ToString().ToLowerInvariant()
$env:SURI_MEDIA_WARMUP = 'true'
Push-Location (Join-Path $projectRoot 'backend-api')
try {
    & $pythonPath -m uvicorn src.app:app --host 127.0.0.1 --port 8000 --workers 1 --no-access-log
    if ($LASTEXITCODE -ne 0) { throw "API exited with code $LASTEXITCODE" }
} finally { Pop-Location }
