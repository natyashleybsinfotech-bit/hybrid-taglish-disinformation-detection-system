$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
$artifactPath = Join-Path $projectRoot 'backend-api\models\TRAINING RESULTS'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'The original model Python environment is missing.' }
$classifierPath = Join-Path $artifactPath 'models\model_4.joblib'
$expectedHash = '72d87971ee2af7fca1f6f0a9b94bbe92618bd92ce8c5e48e35b80882e1321c7c'
if ((Get-FileHash -LiteralPath $classifierPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expectedHash) {
    throw 'Original classifier hash mismatch. API was not started.'
}
$env:SURI_MODEL_PROFILE = '20261011T235112Z'
$env:SURI_MODEL_ARTIFACT_DIR = $artifactPath
$env:SURI_MODEL_DEVICE = 'cpu'
$env:SURI_MODEL_WARMUP = 'true'
$env:SURI_SCREENING_MODE = 'model'
Push-Location (Join-Path $projectRoot 'backend-api')
try {
    & $pythonPath -m uvicorn src.app:app --host 127.0.0.1 --port 8000 --workers 1 --no-access-log
    if ($LASTEXITCODE -ne 0) { throw "API exited with code $LASTEXITCODE" }
} finally { Pop-Location }
