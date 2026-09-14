<#
.SYNOPSIS
    模块一（算法坐标转换系统）一键测试入口。

.DESCRIPTION
    在仓库根目录一次运行模块一坐标转换的全部自动化测试用例，并把控制台日志与
    JUnit XML 结果归档到 test_results/module1/。

    被测对象：vggt-main/vggt/utils/geometry.py
    用例编号：M1-GEO-001 ~ M1-GEO-032
    测试框架：Python 标准库 unittest

    本脚本只负责模块一坐标转换系统。模块二（AI 融合实践）与图像预处理
    （image_test_module1/）不在本入口的范围内。

    结果文件：
      test_results/module1/run_<时间戳>.log   控制台完整输出
      test_results/module1/run_<时间戳>.xml   JUnit XML，供报告统计用例数/通过数

    日志由 tests/junit_report.py 以 UTF-8 直接落盘，不经过 PowerShell 的
    子进程输出捕获 —— PowerShell 5.1 会用控制台 ANSI 码页解码原生进程的
    stderr，从而把中文用例名双重编码成乱码。

.PARAMETER PythonExecutable
    用于执行测试的 Python 解释器。默认按以下顺序探测：
      1. 显式传入的 -PythonExecutable
      2. vggt-main\.venv\Scripts\python.exe
      3. conda 环境 Pytorch_Vggt（D:\anaconda3\envs\Pytorch_Vggt\python.exe 或 PATH 中的 python）

.PARAMETER TestPattern
    unittest 的发现模式，默认按 M1-GEO 用例文件命名匹配。

.PARAMETER NoLog
    只打印到控制台，不写入 test_results/module1/。

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\run_tests.ps1

.EXAMPLE
    .\run_tests.ps1 -PythonExecutable "D:\anaconda3\envs\Pytorch_Vggt\python.exe"

.NOTES
    退出码：0 表示全部用例通过；非 0 表示存在失败/错误，或前置条件不满足。
#>

[CmdletBinding()]
param(
    [string]$PythonExecutable,
    [string]$TestPattern = "test_m1_geo*.py",
    [switch]$NoLog
)

$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# 路径与常量
# ---------------------------------------------------------------------------

$projectRoot      = $PSScriptRoot
$baselineDirectory = Join-Path $projectRoot "vggt-main"     # 被测软件基线
$testsDirectory    = Join-Path $projectRoot "tests"          # 模块一坐标转换测试工程
$internalTestsDir  = Join-Path $testsDirectory "module1_coordinate"
$resultDirectory   = Join-Path $projectRoot "test_results\module1"

$testTargetRelative = "vggt-main/vggt/utils/geometry.py"
$caseIdRange        = "M1-GEO-001 ~ M1-GEO-032"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Write-Info {
    param([string]$Message)
    Write-Host "    $Message" -ForegroundColor Gray
}

# ---------------------------------------------------------------------------
# 1. 解析 Python 解释器
# ---------------------------------------------------------------------------

function Resolve-PythonExecutable {
    param([string]$Explicit)

    if ($Explicit) {
        if (-not (Test-Path -LiteralPath $Explicit)) {
            throw "指定的 Python 解释器不存在：$Explicit"
        }
        return (Resolve-Path -LiteralPath $Explicit).Path
    }

    $candidates = @(
        (Join-Path $baselineDirectory ".venv\Scripts\python.exe"),
        (Join-Path $projectRoot     ".venv\Scripts\python.exe"),
        "D:\anaconda3\envs\Pytorch_Vggt\python.exe"
    )

    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }

    $onPath = Get-Command python -ErrorAction SilentlyContinue
    if ($onPath) {
        return $onPath.Source
    }

    throw "未找到可用的 Python 解释器。请用 -PythonExecutable 显式指定，例如：-PythonExecutable ""D:\anaconda3\envs\Pytorch_Vggt\python.exe"""
}

# ---------------------------------------------------------------------------
# 2. 前置检查
# ---------------------------------------------------------------------------

function Assert-Prerequisites {
    param([string]$Python)

    if (-not (Test-Path -LiteralPath $baselineDirectory)) {
        throw "未找到被测软件基线目录：$baselineDirectory"
    }

    $geometryFile = Join-Path $baselineDirectory "vggt\utils\geometry.py"
    if (-not (Test-Path -LiteralPath $geometryFile)) {
        throw "未找到被测模块文件：$geometryFile"
    }

    if (-not (Test-Path -LiteralPath $testsDirectory)) {
        Write-Host "未找到模块一测试工程目录：$testsDirectory" -ForegroundColor Yellow
        Write-Host "请先按 tests/README.md 的约定在 tests\ 下实现 M1-GEO-001 ~ M1-GEO-032 的 pytest/unittest 用例。" -ForegroundColor Yellow
        exit 2
    }

    # 从外层确认能导入被测模块，且不依赖 demo_gradio_cn.py（该脚本导入即加载模型）。
    # PYTHONPATH 传基线路径；探针必须写成单行、且不含引号 ——
    # Windows PowerShell 5.1 向原生程序传参时会改写多行与引号，多行 -c 会被破坏。
    $probeCode = "import vggt.utils.geometry as g; print(g.__file__)"

    $previousPythonPath = $env:PYTHONPATH
    $env:PYTHONPATH = $baselineDirectory
    try {
        $probeOutput = & $Python -c $probeCode 2>&1
        $probeExitCode = $LASTEXITCODE
    }
    finally {
        $env:PYTHONPATH = $previousPythonPath
    }

    if ($probeExitCode -ne 0) {
        Write-Host "无法从测试工程导入被测模块 $testTargetRelative 。" -ForegroundColor Red
        Write-Host ($probeOutput -join [Environment]::NewLine) -ForegroundColor Red
        exit 3
    }
    Write-Info "被测模块导入检查通过：$testTargetRelative"
}

# ---------------------------------------------------------------------------
# 3. 选择测试发现起点
# ---------------------------------------------------------------------------

function Resolve-DiscoveryStart {
    if (Test-Path -LiteralPath $internalTestsDir) {
        return $internalTestsDir
    }
    return $testsDirectory
}

# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

Write-Host ""
Write-Host "VGGT 模块一：算法坐标转换系统 · 一键测试" -ForegroundColor White
Write-Host "被测对象：$testTargetRelative" -ForegroundColor Gray
Write-Host "用例范围：$caseIdRange" -ForegroundColor Gray
Write-Host "执行时间：$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')" -ForegroundColor Gray

$python = Resolve-PythonExecutable -Explicit $PythonExecutable
Write-Info "Python 解释器：$python"

Assert-Prerequisites -Python $python

$discoveryStart = Resolve-DiscoveryStart
$timestamp      = Get-Date -Format "yyyyMMdd_HHmmss"

if (-not $NoLog) {
    New-Item -ItemType Directory -Force -Path $resultDirectory | Out-Null
}

# 归档后写入 test_results/module1/；请注意 .gitignore 默认忽略该目录下的运行产物，
# 只有 README.md 会被跟踪。需要提交结果时请显式检出或在 README 中登记。

$junitXml  = Join-Path $resultDirectory "run_$timestamp.xml"
$consoleLog = Join-Path $resultDirectory "run_$timestamp.log"
$headerFile = Join-Path $resultDirectory "run_$timestamp.header.txt"

Write-Step "发现并执行用例"
Write-Info "发现起点：$discoveryStart"
Write-Info "匹配模式：$TestPattern"

# 运行横幅先写入独立的 UTF-8 头文件，再由 junit_report.py 拼到日志开头 ——
# 这样横幅与测试输出都由 Python 统一以 UTF-8 落盘，中文不会失真。
if (-not $NoLog) {
    $bannerLines = @(
        "VGGT 模块一：算法坐标转换系统 测试执行日志",
        "======================================================================",
        "执行时间      ：$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')",
        "被测对象      ：$testTargetRelative",
        "用例范围      ：$caseIdRange",
        "发现起点      ：$discoveryStart",
        "匹配模式      ：$TestPattern",
        "Python 解释器 ：$python",
        "工作目录      ：$projectRoot",
        "======================================================================",
        ""
    )
    Set-Content -LiteralPath $headerFile -Value $bannerLines -Encoding UTF8
}

# 统一通过外层插入 vggt-main 导入路径：不为可测性修改被测源码。
$env:PYTHONPATH = $baselineDirectory
if ($env:PYTHONPATH -and $env:PYTHONPATH -ne $baselineDirectory) {
    $env:PYTHONPATH = "$baselineDirectory;$env:PYTHONPATH"
}

$unittestArgs = @(
    "-m", "unittest", "discover",
    "-s", $discoveryStart,
    "-p", $TestPattern,
    "-t", $projectRoot,
    "-v"
)

$testExitCode = 0
$testOutput   = @()
$xmlWritten   = $false

Push-Location $projectRoot
try {
    # 先收集输出再统一打印：避免 Tee-Object + Write-Host 管线在 5.1 下丢输出。
    # 关键：unittest 的进度写到 stderr；在本脚本 *> 重定向 + ErrorActionPreference=Stop 下，
    # 原生 stderr 会以 ErrorRecord 形式出现并触发终止错误。这里临时放宽为 Continue 再恢复。
    $junitHelper = Join-Path $testsDirectory "junit_report.py"
    $useJUnitHelper = (-not $NoLog) -and (Test-Path -LiteralPath $junitHelper)

    $savedErrorAction = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        if ($useJUnitHelper) {
            # 由生成器统一执行一次，并同时产出 XML 与 UTF-8 文本日志，避免重复跑测试。
            # 日志交给 Python 写：PowerShell 捕获子进程 stderr 会把中文双重编码。
            $testOutput = & $python $junitHelper `
                --output $junitXml `
                --log $consoleLog `
                --header-file $headerFile `
                --start-dir $discoveryStart `
                --pattern $TestPattern `
                --top-level $projectRoot 2>&1
        }
        else {
            $testOutput = & $python @unittestArgs 2>&1
        }
        $testExitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $savedErrorAction
    }
    $testOutput | ForEach-Object { Write-Host $_ }

    if ($useJUnitHelper) {
        $xmlWritten = Test-Path -LiteralPath $junitXml
    }
}
finally {
    Pop-Location
}

# ---------------------------------------------------------------------------
# 归档日志
# ---------------------------------------------------------------------------

if (-not $NoLog) {
    if ($xmlWritten) {
        $junitLabel = $junitXml
    }
    else {
        $junitLabel = "(未生成，工程未提供 tests/junit_report.py)"
    }

    if (Test-Path -LiteralPath $consoleLog) {
        # 正常路径：junit_report.py 已写好 UTF-8 日志。仅追加退出码与 XML 路径，
        # 这两项只有脚本跑完才知道。
        $footer = @(
            "",
            "======================================================================",
            "退出码        ：$testExitCode",
            "JUnit XML     ：$junitLabel",
            "======================================================================"
        )
        Add-Content -LiteralPath $consoleLog -Value $footer -Encoding UTF8
    }
    else {
        # 兜底路径：工程未提供生成器，只能由 PowerShell 自己写。
        # 该路径的中文用例名可能失真，仅保证流程可用。
        $banner = @(
            "VGGT 模块一：算法坐标转换系统 测试执行日志",
            "======================================================================",
            "执行时间      ：$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')",
            "被测对象      ：$testTargetRelative",
            "用例范围      ：$caseIdRange",
            "发现起点      ：$discoveryStart",
            "匹配模式      ：$TestPattern",
            "Python 解释器 ：$python",
            "工作目录      ：$projectRoot",
            "退出码        ：$testExitCode",
            "JUnit XML     ：$junitLabel",
            "======================================================================",
            ""
        )
        ($banner + $testOutput) | Set-Content -LiteralPath $consoleLog -Encoding UTF8
    }

    # 头部临时文件已完成使命。
    if (Test-Path -LiteralPath $headerFile) {
        Remove-Item -LiteralPath $headerFile -Force
    }
}

# ---------------------------------------------------------------------------
# 结果汇总
# ---------------------------------------------------------------------------

Write-Step "执行结果"

Write-Host "    退出码：$testExitCode" -ForegroundColor $(if ($testExitCode -eq 0) { "Green" } else { "Red" })
if (-not $NoLog) {
    Write-Info "控制台日志：$consoleLog"
    if ($xmlWritten) {
        Write-Info "JUnit XML ：$junitXml"
    }
}

if ($testExitCode -eq 0) {
    Write-Host ""
    Write-Host "全部用例通过。" -ForegroundColor Green
}
else {
    Write-Host ""
    Write-Host "存在未通过用例，请查看上方 FAIL/ERROR 明细与归档日志。" -ForegroundColor Red
    Write-Host "注意：测试未通过不等于有效缺陷；有效缺陷需经复现、分析、处理与复测，并保留证据。" -ForegroundColor Yellow
}

exit $testExitCode
