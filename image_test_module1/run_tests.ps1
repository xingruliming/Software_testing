$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "VGGT Python environment was not found: $pythonPath"
}

Push-Location $projectRoot
try {
    & $pythonPath -m unittest discover -s tests -v
    $testExitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}

exit $testExitCode
