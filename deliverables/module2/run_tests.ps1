<#
.SYNOPSIS
    VGGT 模块二（AI 输出 · 方案 1 测 AI）单元测试一键驱动。

.DESCRIPTION
    依次完成：探测 Python 解释器 → 检查测试工程完整性 → 注入导入路径 →
    运行 m2_tests 下全部 M2-AI-* 用例（单次运行同时产出 JUnit XML 与 UTF-8 日志）。

    用例共 15 条（M2-AI-001 ~ M2-AI-015），来源《VGGT 模块二测试用例清单》。
    其中帧数扫描、扰动矩阵与补白变体需要 GPU 推理产物；产物缺失时，
    默认自动调用 run_vggt_inference.py 现场生成（需 CUDA 与模型权重）。
    用 -Prepare:$false 可关闭自动生成，此时相关用例会被标记为「跳过」并给出生成办法。

.PARAMETER PythonExecutable
    显式指定 Python 解释器；留空则按内置顺序自动探测。

.PARAMETER TestPattern
    unittest 发现模式，默认 test_m2_ai*.py。

.PARAMETER Prepare
    数据缺失时是否自动生成 GPU 产物，默认 $true。

.PARAMETER NoLog
    只打印到控制台，不写归档日志与 JUnit XML。

.EXAMPLE
    .\run_tests.ps1
    跑全部 15 条用例（缺失数据自动生成）。

.EXAMPLE
    .\run_tests.ps1 -Prepare:$false
    在无 GPU 环境下只跑不依赖新推理的用例，其余标记跳过。

.EXAMPLE
    .\run_tests.ps1 -PythonExecutable "D:\anaconda3\envs\Pytorch_Vggt\python.exe"
    显式指定解释器。

.NOTES
    退出码：0=全部通过；1=存在失败或错误；2=测试工程不完整；3=无法导入被测模块。
#>

param(
    [string]$PythonExecutable = "",
    [string]$TestPattern = "test_m2_ai*.py",
    [bool]$Prepare = $true,
    [switch]$NoLog
)

$ErrorActionPreference = "Stop"

$module2Root = $PSScriptRoot
$repoRoot = Split-Path -Parent (Split-Path -Parent $module2Root)
$testsDir = Join-Path $module2Root "m2_tests"
$resultDir = Join-Path $repoRoot "test_results\module2"
$vggtMain = Join-Path $repoRoot "vggt-main"

function Write-Banner {
    param([string]$Color = "Cyan")
    Write-Host ""
    Write-Host ("=" * 76) -ForegroundColor $Color
    Write-Host "  VGGT 模块二：AI 输出（深度图 + npz 点云）· 单元测试" -ForegroundColor $Color
    Write-Host "  用例范围：M2-AI-001 ~ M2-AI-015（共 15 条）" -ForegroundColor $Color
    Write-Host ("=" * 76) -ForegroundColor $Color
}

# ---------------------------------------------------------------- 1. 解释器探测
function Resolve-Python {
    param([string]$Explicit)

    $candidates = New-Object System.Collections.ArrayList
    if ($Explicit) { [void]$candidates.Add($Explicit) }
    [void]$candidates.Add((Join-Path $repoRoot "vggt-main\.venv\Scripts\python.exe"))
    [void]$candidates.Add((Join-Path $repoRoot ".venv\Scripts\python.exe"))
    [void]$candidates.Add("D:\anaconda3\envs\Pytorch_Vggt\python.exe")

    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate)) { return $candidate }
    }
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return $null
}

Write-Banner

$python = Resolve-Python -Explicit $PythonExecutable
if (-not $python) {
    Write-Host "[错误] 未找到可用的 Python 解释器。" -ForegroundColor Red
    Write-Host "       请用 -PythonExecutable 指定，例如：" -ForegroundColor Yellow
    Write-Host '       .\run_tests.ps1 -PythonExecutable "D:\anaconda3\envs\Pytorch_Vggt\python.exe"' -ForegroundColor Yellow
    exit 3
}

# ---------------------------------------------------------------- 2. 工程完整性
$required = @(
    (Join-Path $repoRoot "metrics.py"),
    (Join-Path $repoRoot "run_vggt_inference.py"),
    (Join-Path $testsDir "__init__.py"),
    (Join-Path $testsDir "common.py"),
    (Join-Path $testsDir "junit_report.py")
)
$missing = @()
foreach ($path in $required) {
    if (-not (Test-Path -LiteralPath $path)) { $missing += $path }
}
if ($missing.Count -gt 0) {
    Write-Host "[错误] 测试工程不完整，缺少以下文件：" -ForegroundColor Red
    foreach ($path in $missing) { Write-Host "       - $path" -ForegroundColor Red }
    exit 2
}

# ---------------------------------------------------------------- 3. 运行环境
$env:PYTHONPATH = "$repoRoot;$vggtMain"
$env:M2_PYTHON = $python
$env:M2_PREPARE = if ($Prepare) { "1" } else { "0" }

$caseFiles = @(Get-ChildItem -LiteralPath $testsDir -Filter "test_m2_ai*.py" -File -ErrorAction SilentlyContinue)
$expRoot = Join-Path $repoRoot "vggt_output\exp"
$expReady = Test-Path -LiteralPath $expRoot

Write-Host ("  仓库根目录   : {0}" -f $repoRoot)
Write-Host ("  Python 解释器: {0}" -f $python)
Write-Host ("  测试文件     : {0} 个（模式 {1}）" -f $caseFiles.Count, $TestPattern)
Write-Host ("  归档目录     : {0}" -f $resultDir)
if ($Prepare) {
    if ($expReady) {
        Write-Host "  数据策略     : 复用 vggt_output\exp 既有产物，缺失的变体现场生成" -ForegroundColor DarkGray
    } else {
        Write-Host "  数据策略     : vggt_output\exp 不存在，需现场生成帧数/扰动变体（约 6-10 分钟，需 CUDA）" -ForegroundColor Yellow
    }
} else {
    Write-Host "  数据策略     : 已禁用自动生成（-Prepare:`$false），缺失数据的用例将标记为跳过" -ForegroundColor DarkGray
}
Write-Host ""

# 导入探针：确认标准库、numpy、metrics 均可用
& $python -c "import numpy, metrics; print('[check] metrics module OK:', metrics.__file__)" 2>&1 | ForEach-Object { Write-Host "  $_" }
if ($LASTEXITCODE -ne 0) {
    Write-Host "[错误] 无法导入 metrics.py，请检查 PYTHONPATH 与 numpy 安装。" -ForegroundColor Red
    exit 3
}

# ---------------------------------------------------------------- 4. 执行用例
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$headerFile = $null
$xmlPath = $null
$logPath = $null
$arguments = @(
    (Join-Path $testsDir "junit_report.py"),
    "--start-dir", "m2_tests",
    "--pattern", $TestPattern,
    "--top-level", "."
)

if (-not $NoLog) {
    New-Item -ItemType Directory -Force -Path $resultDir | Out-Null
    $xmlPath = Join-Path $resultDir ("run_{0}.xml" -f $timestamp)
    $logPath = Join-Path $resultDir ("run_{0}.log" -f $timestamp)
    $headerFile = Join-Path $resultDir ("run_{0}.header.txt" -f $timestamp)

    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss zzz"
    $banner = @(
        "VGGT 模块二：AI 输出单元测试"
        ("执行时间：{0}" -f $stamp)
        ("Python  : {0}" -f $python)
        ("仓库根  : {0}" -f $repoRoot)
        "用例范围：M2-AI-001 ~ M2-AI-015（共 15 条）"
        ""
    ) -join "`n"
    [System.IO.File]::WriteAllText($headerFile, $banner, (New-Object System.Text.UTF8Encoding $false))

    $arguments += @("--output", $xmlPath, "--log", $logPath, "--header-file", $headerFile)
} else {
    $arguments += @("--output", (Join-Path $env:TEMP "m2_run_$timestamp.xml"))
}

Push-Location $module2Root
try {
    & $python @arguments
    $testExit = $LASTEXITCODE
} finally {
    Pop-Location
}

# ---------------------------------------------------------------- 5. 结果摘要
Write-Host ""
Write-Host ("=" * 76)
if ($xmlPath -and (Test-Path -LiteralPath $xmlPath)) {
    try {
        [xml]$xml = Get-Content -LiteralPath $xmlPath -Encoding UTF8
        $suite = $xml.testsuite
        Write-Host ("  执行 {0} 项：失败 {1}、错误 {2}、跳过 {3}" -f $suite.tests, $suite.failures, $suite.errors, $suite.skipped)
        $passed = [int]$suite.tests - [int]$suite.failures - [int]$suite.errors - [int]$suite.skipped
        Write-Host ("  通过 {0} 项" -f $passed)
    } catch {
        Write-Host "  （JUnit XML 解析失败，请查看归档文件）" -ForegroundColor Yellow
    }
    Write-Host ("  JUnit XML : {0}" -f $xmlPath)
    Write-Host ("  运行日志  : {0}" -f $logPath)
}

switch ($testExit) {
    0 { Write-Host "  结论：全部用例通过。" -ForegroundColor Green }
    1 { Write-Host "  结论：存在失败/错误用例，请查看上方明细与归档日志。" -ForegroundColor Yellow }
    default { Write-Host ("  结论：测试进程异常退出（退出码 {0}）。" -f $testExit) -ForegroundColor Red }
}
Write-Host "  说明：单帧变体（G4 无帧对）预期报告「不可用」；M2-AI-010 与 M2-AI-015" -ForegroundColor DarkGray
Write-Host "        对应当前未修复缺陷 DEF-M2-003 与 DEF-M2-001，预期为失败。" -ForegroundColor DarkGray
Write-Host ("=" * 76)

exit $testExit
