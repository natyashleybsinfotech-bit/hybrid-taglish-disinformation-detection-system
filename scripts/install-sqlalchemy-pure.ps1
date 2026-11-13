param([string]$ProjectPython = '')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
if (-not $ProjectPython) { $ProjectPython = Join-Path $projectRoot '.venv-candidate-20261023-isolated\Scripts\python.exe' }
if (-not (Test-Path -LiteralPath $ProjectPython)) { throw 'The project Python environment was not found.' }
$wheelDirectory = Join-Path $projectRoot 'tmp\sqlalchemy-pure-wheel'
New-Item -ItemType Directory -Path $wheelDirectory -Force | Out-Null
$oldBuildSetting = $env:DISABLE_SQLALCHEMY_CEXT
try {
    $env:DISABLE_SQLALCHEMY_CEXT = '1'
    & $ProjectPython -m pip wheel --no-cache-dir --no-deps --no-binary=sqlalchemy --wheel-dir $wheelDirectory 'SQLAlchemy==2.1.2'
    if ($LASTEXITCODE -ne 0) { throw 'The official pure-Python package build failed.' }
    $wheel = Join-Path $wheelDirectory 'sqlalchemy-2.1.2-py3-none-any.whl'
    if (-not (Test-Path -LiteralPath $wheel)) { throw 'The expected pure-Python wheel was not produced.' }
    & $ProjectPython -m pip install --no-deps --force-reinstall $wheel
    if ($LASTEXITCODE -ne 0) { throw 'Package installation failed. Stop the API before retrying.' }
    & $ProjectPython -c "import sqlalchemy,sqlalchemy.util._collections_cy as c; assert sqlalchemy.__version__ == '2.1.2'; assert c.__file__.endswith('.py'); print('SQLAlchemy 2.1.2 pure-Python import verified')"
    if ($LASTEXITCODE -ne 0) { throw 'The pure-Python import check failed.' }
} finally {
    $env:DISABLE_SQLALCHEMY_CEXT = $oldBuildSetting
}
