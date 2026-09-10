[CmdletBinding()]
param(
    [string]$PythonExecutable = ""
)

$ErrorActionPreference = "Stop"

$repositoryRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$vggtDirectory = Join-Path $repositoryRoot "vggt-main"
$demoScript = Join-Path $vggtDirectory "demo_gradio_cn.py"
$modelFile = Join-Path (Split-Path -Parent $repositoryRoot) "model.pt"
$preferredPython = "D:\anaconda3\envs\Pytorch_Vggt\python.exe"

if (-not (Test-Path -LiteralPath $demoScript -PathType Leaf)) {
    throw "VGGT demo script was not found: $demoScript"
}

if (-not (Test-Path -LiteralPath $modelFile -PathType Leaf)) {
    throw "VGGT model checkpoint was not found: $modelFile"
}

if ([string]::IsNullOrWhiteSpace($PythonExecutable)) {
    if (Test-Path -LiteralPath $preferredPython -PathType Leaf) {
        $PythonExecutable = $preferredPython
    }
    else {
        $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
        if ($null -eq $pythonCommand) {
            throw "Python was not found. Use -PythonExecutable to select the Pytorch_Vggt environment."
        }
        $PythonExecutable = $pythonCommand.Source
    }
}

if (-not (Test-Path -LiteralPath $PythonExecutable -PathType Leaf)) {
    throw "The selected Python executable does not exist: $PythonExecutable"
}

Write-Host "VGGT working directory: $vggtDirectory"
Write-Host "Python: $PythonExecutable"
Write-Host "Open the local Gradio URL printed below. Press Ctrl+C to stop the service."

Push-Location -LiteralPath $vggtDirectory
try {
    & $PythonExecutable $demoScript
    if ($LASTEXITCODE -ne 0) {
        throw "demo_gradio_cn.py exited with code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}
