$ErrorActionPreference = "Stop"

$caseDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Resolve-Path (Join-Path $caseDirectory "..\..\..")
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$resultDirectory = Join-Path $caseDirectory "results"
$resultFile = Join-Path $resultDirectory "DEF-IMG-002_reproduction.txt"

if (-not (Test-Path -LiteralPath $python)) { throw "未找到项目 Python 环境：$python" }
New-Item -ItemType Directory -Force -Path $resultDirectory | Out-Null

Push-Location $projectRoot
try {
    & $python (Join-Path $caseDirectory "generate_input.py") | Out-Null
    $testOutput = & $python -m unittest tests.defect_tests.exif_orientation_not_applied.expected_behavior_checks -v 2>&1
    $testExitCode = $LASTEXITCODE
    @(
        "DEF-IMG-002 JPEG EXIF 方向未应用"
        "执行时间：$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')"
        "被测函数：load_and_preprocess_images；load_and_preprocess_images_square"
        "输入：存储尺寸 40×20、EXIF Orientation=6 的 JPEG；无 EXIF 对照 JPEG"
        ""
        $testOutput
        ""
        "退出码：$testExitCode"
        "判定：无 EXIF 对照通过，而两个方向期望检查失败时，缺陷已复现。"
    ) | Set-Content -LiteralPath $resultFile -Encoding UTF8
    $testOutput | ForEach-Object { Write-Host $_ }
    Write-Host "复现记录已保存：$resultFile"
}
finally { Pop-Location }

exit $testExitCode
