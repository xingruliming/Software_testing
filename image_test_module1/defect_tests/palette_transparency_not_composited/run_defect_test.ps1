$ErrorActionPreference = "Stop"

$caseDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Resolve-Path (Join-Path $caseDirectory "..\..\..")
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$resultDirectory = Join-Path $caseDirectory "results"
$resultFile = Join-Path $resultDirectory "DEF-IMG-003_reproduction.txt"

if (-not (Test-Path -LiteralPath $python)) { throw "未找到项目 Python 环境：$python" }
New-Item -ItemType Directory -Force -Path $resultDirectory | Out-Null

Push-Location $projectRoot
try {
    & $python (Join-Path $caseDirectory "generate_input.py") | Out-Null
    $testOutput = & $python -m unittest tests.defect_tests.palette_transparency_not_composited.expected_behavior_checks -v 2>&1
    $testExitCode = $LASTEXITCODE
    @(
        "DEF-IMG-003 调色板 PNG 透明区域未合成到白色背景"
        "执行时间：$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')"
        "被测函数：load_and_preprocess_images；load_and_preprocess_images_square"
        "输入：全透明 P 模式 PNG；全透明 RGBA PNG 对照"
        ""
        $testOutput
        ""
        "退出码：$testExitCode"
        "判定：RGBA 对照通过，而两个 P 模式透明度检查失败时，缺陷已复现。"
    ) | Set-Content -LiteralPath $resultFile -Encoding UTF8
    $testOutput | ForEach-Object { Write-Host $_ }
    Write-Host "复现记录已保存：$resultFile"
}
finally { Pop-Location }

exit $testExitCode
