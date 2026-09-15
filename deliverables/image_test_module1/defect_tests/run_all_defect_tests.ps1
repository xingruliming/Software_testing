$ErrorActionPreference = "Continue"

$defectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Resolve-Path (Join-Path $defectRoot "..\..")
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$resultDirectory = Join-Path $defectRoot "results"
$resultFile = Join-Path $resultDirectory "all_defects_fix_verification.txt"

if (-not (Test-Path -LiteralPath $python)) {
    throw "未找到项目 Python 环境：$python"
}

New-Item -ItemType Directory -Force -Path $resultDirectory | Out-Null

$generators = @(
    "tests\defect_tests\load_and_preprocess_images_extreme_ratio\generate_input.py",
    "tests\defect_tests\exif_orientation_not_applied\generate_input.py",
    "tests\defect_tests\palette_transparency_not_composited\generate_input.py"
)
$modules = @(
    "tests.defect_tests.load_and_preprocess_images_extreme_ratio.expected_behavior_checks",
    "tests.defect_tests.exif_orientation_not_applied.expected_behavior_checks",
    "tests.defect_tests.palette_transparency_not_composited.expected_behavior_checks"
)

Push-Location $projectRoot
try {
    foreach ($generator in $generators) {
        & $python $generator | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "输入数据生成失败：$generator"
        }
    }

    $testOutput = & $python -m unittest $modules -v 2>&1
    $testExitCode = $LASTEXITCODE

    @(
        "VGGT 图像预处理模块 3 个有效缺陷修复验证汇总"
        "执行时间：$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')"
        "缺陷编号：DEF-IMG-001、DEF-IMG-002、DEF-IMG-003"
        "检查数量：9（3 条对照检查，6 条缺陷期望行为检查）"
        "说明：DEF-IMG-001、DEF-IMG-002、DEF-IMG-003 均已修复并进入回归验证。"
        ""
        $testOutput
        ""
        "退出码：$testExitCode"
        "判定：退出码为 0 且 9 条检查全部通过时，三个缺陷的修复验证通过。"
    ) | Set-Content -LiteralPath $resultFile -Encoding UTF8

    $testOutput | ForEach-Object { Write-Host $_ }
    Write-Host "汇总修复验证记录已保存：$resultFile"
}
finally {
    Pop-Location
}

exit $testExitCode
