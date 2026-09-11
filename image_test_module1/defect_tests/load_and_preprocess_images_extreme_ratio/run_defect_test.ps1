$ErrorActionPreference = "Stop"

$caseDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Resolve-Path (Join-Path $caseDirectory "..\..\..")
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$resultDirectory = Join-Path $caseDirectory "results"
$resultFile = Join-Path $resultDirectory "DEF-IMG-001_reproduction.txt"

if (-not (Test-Path -LiteralPath $python)) {
    throw "未找到项目 Python 环境：$python"
}

New-Item -ItemType Directory -Force -Path $resultDirectory | Out-Null

Push-Location $projectRoot
try {
    & $python (Join-Path $caseDirectory "generate_input.py") | Out-Null
    $testOutput = & $python -m unittest `
        tests.defect_tests.load_and_preprocess_images_extreme_ratio.expected_behavior_checks `
        -v 2>&1
    $testExitCode = $LASTEXITCODE

    @(
        "DEF-IMG-001 极端宽高比图片缺陷复现"
        "执行时间：$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')"
        "被测函数：vggt.utils.load_fn.load_and_preprocess_images"
        "被测输入：518×1 RGB PNG；对照输入：518×14 RGB PNG"
        ""
        $testOutput
        ""
        "退出码：$testExitCode"
        "判定：退出码非零且两个极端宽高比用例抛出 ValueError 时，缺陷已复现。"
    ) | Set-Content -LiteralPath $resultFile -Encoding UTF8

    $testOutput | ForEach-Object { Write-Host $_ }
    Write-Host "复现记录已保存：$resultFile"
}
finally {
    Pop-Location
}

exit $testExitCode
