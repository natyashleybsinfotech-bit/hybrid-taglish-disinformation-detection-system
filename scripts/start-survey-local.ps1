$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$surveyVersion = (Get-Content -LiteralPath (Join-Path $projectRoot 'chrome-extension\manifest.json') -Raw | ConvertFrom-Json).version
& (Join-Path $PSScriptRoot 'start-mariadb.ps1')
try { $surveyReady = Invoke-RestMethod 'http://127.0.0.1:8000/ready' -TimeoutSec 3 } catch { $surveyReady = $null }
if ($surveyReady -and $surveyReady.ready -and $surveyReady.model.profile -eq 'suriph-finetune-6a35c6d4a2a0' -and $surveyReady.screening_policy.evidence_assistance_enabled -and -not $surveyReady.screening_policy.model_authoritative) {
    Write-Output ('SuriPH local API and MariaDB are running with optional evidence assistance. Reload extension {0} and refresh Facebook before a new check.' -f $surveyVersion)
    exit 0
}
$projectPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
$surveyPidFile = Join-Path $projectRoot '.run\api-finetuned.pid'
$surveyProcesses = @()
if (Test-Path -LiteralPath $surveyPidFile) {
    $savedSurveyProcessId = 0
    if ([int]::TryParse((Get-Content -LiteralPath $surveyPidFile -Raw).Trim(), [ref]$savedSurveyProcessId)) {
        $surveyProcesses = @(Get-Process -Id $savedSurveyProcessId -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -eq 'python' })
    }
}
if ($surveyProcesses.Count) {
    throw 'An API is already running with a different result policy or is still preparing. Stop the existing API before starting the updated evidence-assisted mode; do not start a second API.'
}
& (Join-Path $PSScriptRoot 'start-finetuned-trial.ps1')
