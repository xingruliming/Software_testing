# -*- coding: utf-8 -*-
"""VGGT 模块二（M2-AI-001 ~ M2-AI-015）用例统一运行器 —— 框架。

定位
----
``run_tests.ps1`` 负责「一次跑完整包 + 出一份 JUnit XML」；本脚本补上它没有的
能力：**按用例编号驱动、逐条独立计时与判定、缺陷折算、多格式归档**。
二者互不替代，共用同一套 ``m2_tests`` 用例。

核心能力
--------
1. **用例注册表**：用 ``ast`` 静态扫描 ``m2_tests/test_m2_ai*.py``，从方法名
   ``test_m2_ai_<NNN>_*`` 提取编号，与下方 ``CASE_META`` 的元数据（中文标题、
   预期结论、关联缺陷、数据依赖）合并。扫描是纯静态的，``--list`` 不导入
   任何测试模块，因此不产生副作用。
2. **选择器**：``--cases 001,003,010-015`` / ``--from`` / ``--to``，支持区间。
3. **逐条执行**：每条用例单独构建 suite 并独立计时，一条崩了不影响其余。
   ``--isolated`` 改为每条一个子进程，可硬超时、可回收显存。
4. **预期失败折算**：010 与 015 在清单中的判定即为 NG（对应 DEF-M2-003 /
   DEF-M2-001）。默认把它们的 FAIL 折算为 ``XFAIL``（符合预期，不算回归），
   把 PASS 折算为 ``XPASS``（提示缺陷可能已被修复）。``--strict`` 关闭折算，
   用于「修完之后验证是否全绿」。
5. **归档**：汇总 txt（人读）、json（机读）、csv（贴报告）、可选 JUnit XML。

退出码
------
====  ==========================================
0     全部符合预期（PASS / SKIP / XFAIL）
1     存在非预期失败、错误（或 --fail-on-skip 下的跳过）
2     测试工程不完整（缺 metrics.py / m2_tests 关键文件）
3     环境问题（无法定位解释器或导入被测模块）
4     用例发现不完整（清单 15 条未全部落地）
====  ==========================================

用法示例
--------
::

    python run_all_cases.py                       # 跑全部 15 条
    python run_all_cases.py --list                # 只列清单与数据就绪情况
    python run_all_cases.py --cases 010-012,015   # 只跑指定编号
    python run_all_cases.py --no-prepare          # 无 GPU：缺失数据标记跳过
    python run_all_cases.py --isolated --timeout 900
    python run_all_cases.py --strict              # 验证缺陷是否已修复
"""

from __future__ import annotations

import argparse
import ast
import csv
import importlib
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
import unittest
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# --------------------------------------------------------------------------
# 路径与工程常量（与 m2_tests/common.py 的口径一致，但不 import 它，
# 以保证 --list 这类只读操作不触发任何模块副作用）
# --------------------------------------------------------------------------
RUNNER_DIR = Path(__file__).resolve().parent          # .../deliverables/module2
REPO_ROOT = RUNNER_DIR.parents[1]                     # .../Software_testing
TESTS_DIR = RUNNER_DIR / "m2_tests"
VGGT_MAIN = REPO_ROOT / "vggt-main"
VGGT_OUTPUT = REPO_ROOT / "vggt_output"
EXP_ROOT = VGGT_OUTPUT / "exp"
RESULT_DIR = REPO_ROOT / "test_results" / "module2"
TMP_DIR = RESULT_DIR / "tmp"
MODEL_PATH = REPO_ROOT.parent / "model.pt"
METRICS_PY = REPO_ROOT / "metrics.py"

TOTAL_CASES = 15              # 清单固定 15 条，用于发现完整性校验
DEFAULT_TIMEOUT = 1800        # isolated 模式单条用例硬超时（秒）

# 状态枚举。XFAIL / XPASS 为折算后的状态，原始状态只有前四种。
STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_ERROR = "ERROR"
STATUS_SKIP = "SKIP"
STATUS_XFAIL = "XFAIL"
STATUS_XPASS = "XPASS"

UNEXPECTED_BAD = (STATUS_FAIL, STATUS_ERROR)


# --------------------------------------------------------------------------
# 用例元数据注册表
# --------------------------------------------------------------------------
# 字段说明：
#   title  中文用例名（与《VGGT 模块二测试用例清单》一致）
#   expect "pass" = 应通过；"fail" = 清单判定为 NG，复现已知缺陷
#   defect 关联缺陷编号（无则 None）
#   data   依赖的产物，相对 vggt_output/；前缀 "exp:" 表示可现场生成的变体；
#          特殊值 "MODEL" = 权重、"CUDA" = 需要 GPU
#   note   一句话说明，用于 --list 与汇总表
CASE_META: dict = {
    "001": dict(
        title="基准场景自洽性基线测量（002_computer，9 帧）",
        expect="pass", defect=None,
        data=("002_computer/predictions.npz", "002_computer/run_info.json"),
        note="G1/G2/G3/G4 四项指标可统计且落在可用区间",
    ),
    "002": dict(
        title="帧数减少至 5 帧的自洽性退化",
        expect="pass", defect=None,
        data=("002_computer/predictions.npz", "exp:N5"),
        note="5 帧的 G1 相对误差应大于 9 帧基线",
    ),
    "003": dict(
        title="帧数减少至 2 帧的自洽性退化",
        expect="pass", defect=None,
        data=("002_computer/predictions.npz", "exp:N2", "exp:N5"),
        note="2 帧的 G1 相对误差应大于 5 帧",
    ),
    "004": dict(
        title="单帧输入时光度一致性指标应不可用",
        expect="pass", defect=None,
        data=("exp:N1",),
        note="无帧对时 G4 应报「不可用」而非给出错误数值",
    ),
    "005": dict(
        title="帧数—指标单调性检验（1→2→5→9）",
        expect="pass", defect=None,
        data=("002_computer/predictions.npz", "exp:N1", "exp:N2", "exp:N5"),
        note="G1 单调下降、G3 置信均值单调上升",
    ),
    "006": dict(
        title="分辨率降为 0.5 倍的鲁棒性",
        expect="pass", defect=None,
        data=("002_computer/predictions.npz", "exp:res50"),
        note="断言实测结论：G2/G4 与基线同量级（未显著退化）",
    ),
    "007": dict(
        title="高斯噪声 σ=10 的鲁棒性",
        expect="pass", defect=None,
        data=("002_computer/predictions.npz", "exp:noise10"),
        note="断言实测结论：G2/G4 与基线同量级（未显著退化）",
    ),
    "008": dict(
        title="随机遮挡 25% 面积的鲁棒性",
        expect="pass", defect=None,
        data=("002_computer/predictions.npz", "exp:occ25"),
        note="唯一显著退化项：G4 NCC 降幅 > 20%",
    ),
    "009": dict(
        title="重复运行确定性检验（逐位一致）",
        expect="pass", defect=None,
        data=("002_computer/predictions.npz", "exp:det2"),
        note="depth/world_points/extrinsic/intrinsic 四字段 max_abs_diff = 0",
    ),
    "010": dict(
        title="竖构图近景场景在默认置信阈值下的可用性",
        expect="fail", defect="DEF-M2-003",
        data=("001_watercup/predictions.npz",),
        note="清单判定 NG：conf=3.0 下四项指标全部不可统计",
    ),
    "011": dict(
        title="竖构图场景放宽置信阈值后的指标测量",
        expect="pass", defect=None,
        data=("001_watercup/predictions.npz",),
        note="conf=1.0 下指标可统计但显著劣于横构图基线",
    ),
    "012": dict(
        title="排除裁切影响：竖构图补白成正方形后重测",
        expect="pass", defect="DEF-M2-002",
        data=("001_watercup/predictions.npz", "exp:sq4096"),
        note="否证「裁切是退化主因」假说；关联 DEF-M2-002",
    ),
    "013": dict(
        title="空输入目录的异常处理",
        expect="pass", defect=None,
        data=(),
        note="现场调用推理脚本：非零退出码 + 中文提示 + 不建输出目录",
    ),
    "014": dict(
        title="输入目录不存在的异常处理",
        expect="pass", defect=None,
        data=(),
        note="现场调用推理脚本：非零退出码 + 中文提示",
    ),
    "015": dict(
        title="损坏图像文件的异常处理",
        expect="fail", defect="DEF-M2-001",
        data=("MODEL", "CUDA"),
        note="清单判定 NG：暴露 PIL 原始堆栈并残留半成品输出",
    ),
}


# --------------------------------------------------------------------------
# 数据结构
# --------------------------------------------------------------------------
@dataclass
class CaseSpec:
    """一条用例的定位信息 + 元数据。"""

    cid: str                 # 三位编号，如 "010"
    module: str              # 测试模块，如 "m2_tests.test_m2_ai_010_012_scene_dependency"
    cls: str                 # 测试类名
    method: str              # 测试方法名
    source: str              # 来源文件名
    title: str = ""
    expect: str = "pass"
    defect: str | None = None
    data: tuple = ()
    note: str = ""

    @property
    def label(self) -> str:
        return "M2-AI-%s" % self.cid

    @property
    def qualified_name(self) -> str:
        return "%s.%s.%s" % (self.module, self.cls, self.method)


@dataclass
class CaseResult:
    """一条用例的执行结果（status 为折算后的最终状态）。"""

    spec: CaseSpec
    status: str
    raw_status: str
    seconds: float
    detail: str = ""

    @property
    def cid(self) -> str:
        return self.spec.cid


@dataclass
class Readiness:
    """数据就绪检查的汇总。"""

    missing: list = field(default_factory=list)      # 缺失且无法自动生成的产物
    generable: list = field(default_factory=list)    # 缺失但可现场生成的变体
    ready: list = field(default_factory=list)        # 已就绪的产物


# --------------------------------------------------------------------------
# 发现：静态扫描 m2_tests/
# --------------------------------------------------------------------------
def _parse_method_id(method_name: str):
    """从 ``test_m2_ai_010_xxx`` 提取 ``"010"``；不匹配返回 None。"""
    prefix = "test_m2_ai_"
    if not method_name.startswith(prefix):
        return None
    rest = method_name[len(prefix):]
    digits = rest.split("_", 1)[0]
    return digits if len(digits) == 3 and digits.isdigit() else None


def discover_specs() -> tuple:
    """静态扫描测试目录，返回 ``([CaseSpec], [问题描述])``。

    用 ``ast`` 解析而非 import：既避免副作用，也能在依赖缺失
    （例如没装 numpy）时照样列出清单。
    """
    specs = {}
    problems = []

    files = sorted(TESTS_DIR.glob("test_m2_ai*.py"))
    if not files:
        problems.append("目录 %s 下没有找到 test_m2_ai*.py" % TESTS_DIR)
        return [], problems

    for path in files:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            problems.append("解析失败 %s：%s" % (path.name, exc))
            continue

        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            if not any(_base_name(b) in ("TestCase", "TestCaseMixin") for b in node.bases):
                continue
            for item in node.body:
                if not isinstance(item, ast.FunctionDef):
                    continue
                cid = _parse_method_id(item.name)
                if cid is None:
                    continue
                if cid in specs:
                    problems.append(
                        "编号 %s 重复定义：%s 与 %s 都含该用例"
                        % (cid, specs[cid].module, path.name)
                    )
                    continue
                specs[cid] = CaseSpec(
                    cid=cid,
                    module="m2_tests.%s" % path.stem,
                    cls=node.name,
                    method=item.name,
                    source=path.name,
                    **CASE_META.get(cid, {}),
                )

    ordered = [specs[cid] for cid in sorted(specs)]
    found = {s.cid for s in ordered}
    expected = {"%03d" % i for i in range(1, TOTAL_CASES + 1)}
    for cid in sorted(expected - found):
        problems.append("清单用例 M2-AI-%s 未在 m2_tests/ 中找到对应测试方法" % cid)
    return ordered, problems


def _base_name(node) -> str:
    """取基类表达式的名字（``unittest.TestCase`` -> ``TestCase``）。"""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


# --------------------------------------------------------------------------
# 选择器
# --------------------------------------------------------------------------
def parse_case_selector(text: str, all_ids) -> list:
    """解析 ``"001,003,010-015"`` 形式的选择器，返回有序编号列表。"""
    if not text:
        return list(all_ids)
    wanted = set()
    for chunk in text.replace("，", ",").split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk[1:]:
            head, _, tail = chunk.partition("-")
            head, tail = head.strip().zfill(3), tail.strip().zfill(3)
            if not (head.isdigit() and tail.isdigit()):
                raise ValueError("无法解析区间：%s" % chunk)
            lo, hi = int(head), int(tail)
            if lo > hi:
                lo, hi = hi, lo
            wanted.update("%03d" % i for i in range(lo, hi + 1))
        else:
            token = chunk.zfill(3)
            if not token.isdigit():
                raise ValueError("无法解析用例编号：%s" % chunk)
            wanted.add(token)
    return [cid for cid in all_ids if cid in wanted]


def select_specs(specs, args) -> list:
    """按 --cases / --from / --to 过滤。"""
    ids = [s.cid for s in specs]
    chosen = parse_case_selector(args.cases, ids)
    if args.from_case:
        lo = args.from_case.strip().zfill(3)
        chosen = [cid for cid in chosen if cid >= lo]
    if args.to_case:
        hi = args.to_case.strip().zfill(3)
        chosen = [cid for cid in chosen if cid <= hi]
    picked = set(chosen)
    return [s for s in specs if s.cid in picked]


# --------------------------------------------------------------------------
# 就绪检查
# --------------------------------------------------------------------------
def check_readiness(specs, prepare: bool) -> Readiness:
    """按注册表的 data 字段检查产物是否齐备。"""
    r = Readiness()
    seen = set()
    for spec in specs:
        for item in spec.data:
            if item in seen:
                continue
            seen.add(item)

            if item == "MODEL":
                (r.ready if MODEL_PATH.is_file() else r.missing).append(
                    "模型权重 %s" % MODEL_PATH
                )
                continue
            if item == "CUDA":
                continue  # GPU 可用性由用例自身在运行时判定，此处不探测

            if item.startswith("exp:"):
                variant = item[4:]
                npz = EXP_ROOT / variant / "predictions.npz"
                if npz.is_file():
                    r.ready.append(item)
                elif prepare:
                    r.generable.append(item)
                else:
                    r.missing.append(item + "（可现场生成，但已设置 --no-prepare）")
            else:
                target = VGGT_OUTPUT / item
                (r.ready if target.is_file() else r.missing).append(item)
    return r


def preflight() -> list:
    """工程完整性检查，返回问题列表（空表示通过）。"""
    problems = []
    required = [
        METRICS_PY,
        TESTS_DIR / "__init__.py",
        TESTS_DIR / "common.py",
        REPO_ROOT / "run_vggt_inference.py",
    ]
    for path in required:
        if not path.exists():
            problems.append("缺少必需文件：%s" % path)
    if not VGGT_MAIN.is_dir():
        problems.append("缺少被测基线目录：%s" % VGGT_MAIN)
    return problems


# --------------------------------------------------------------------------
# 执行：进程内 / 隔离子进程
# --------------------------------------------------------------------------
class CaseOutcome(unittest.TestResult):
    """只记录「这一条」用例的结论，不打印任何东西。"""

    def __init__(self):
        super().__init__()
        self.status = STATUS_PASS
        self.detail = ""

    def _mark(self, status, detail=""):
        # ERROR 优先级最高（前置失败）；其余保留首个结论
        if self.status == STATUS_PASS or status == STATUS_ERROR:
            self.status = status
            self.detail = detail

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._mark(STATUS_FAIL, describe_error(err))

    def addError(self, test, err):
        super().addError(test, err)
        self._mark(STATUS_ERROR, describe_error(err))

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self._mark(STATUS_SKIP, str(reason).strip())

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err is not None and issubclass(err[0], test.failureException):
            self._mark(STATUS_FAIL, describe_error(err))
        elif err is not None and issubclass(err[0], unittest.SkipTest):
            self._mark(STATUS_SKIP, str(err[1]).strip())


def describe_error(err) -> str:
    """把 (type, value, tb) 压成一行摘要。"""
    exc_type, exc_value = err[0], err[1]
    text = "%s: %s" % (exc_type.__name__, exc_value)
    text = " ".join(str(text).split())
    return text[:400] if text else exc_type.__name__


def run_one_inproc(spec: CaseSpec) -> tuple:
    """在当前进程内跑一条用例，返回 (status, detail, seconds)。"""
    module = importlib.import_module(spec.module)
    case_cls = getattr(module, spec.cls)
    suite = unittest.TestSuite([case_cls(spec.method)])

    result = CaseOutcome()
    started = time.perf_counter()
    try:
        suite.run(result)
    except Exception as exc:                      # 运行器层面的兜底
        return STATUS_ERROR, "运行器异常：%s" % exc, time.perf_counter() - started
    return result.status, result.detail, time.perf_counter() - started


def run_one_isolated(spec: CaseSpec, timeout: int, prepare: bool) -> tuple:
    """在独立子进程中跑一条用例，返回 (status, detail, seconds)。

    好处：单条用例挂起可被硬超时掐断，且 GPU 显存随进程退出回收。
    """
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    exchange = TMP_DIR / ("isolated_%s_%s.json" % (spec.cid, time.strftime("%Y%m%d_%H%M%S")))
    cmd = [
        sys.executable, str(Path(__file__).resolve()),
        "--_execute", spec.cid, "--_json-out", str(exchange),
    ]
    if not prepare:
        cmd.append("--no-prepare")
    if os.environ.get("M2_PYTHON"):
        cmd += ["--python", os.environ["M2_PYTHON"]]

    started = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd, cwd=str(RUNNER_DIR), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return STATUS_ERROR, "单条用例超时（> %d s）被终止" % timeout, time.perf_counter() - started

    elapsed = time.perf_counter() - started
    if exchange.is_file():
        payload = json.loads(exchange.read_text(encoding="utf-8"))
        return payload.get("status", STATUS_ERROR), payload.get("detail", ""), payload.get("seconds", elapsed)

    tail = ((proc.stderr or "") + (proc.stdout or "")).strip().splitlines()
    detail = "子进程未产出结果（rc=%s）；末尾输出：%s" % (
        proc.returncode, " | ".join(tail[-3:]) if tail else "（无）",
    )
    return STATUS_ERROR, detail, elapsed


def execute(spec: CaseSpec, args) -> CaseResult:
    """执行一条用例并完成预期失败折算。"""
    prepare = not args.no_prepare
    if args.isolated:
        raw, detail, seconds = run_one_isolated(spec, args.timeout, prepare)
    else:
        raw, detail, seconds = run_one_inproc(spec)

    status = classify(spec, raw, strict=args.strict)
    return CaseResult(spec=spec, status=status, raw_status=raw, seconds=seconds, detail=detail)


def classify(spec: CaseSpec, raw_status: str, strict: bool) -> str:
    """把原始结论折算为最终结论。

    清单判定为 NG 的用例（010 / 015）承担「缺陷复现」职责：
    * 默认：失败 -> XFAIL（符合预期）；通过 -> XPASS（缺陷疑似已修复）。
    * --strict：不做折算，失败即 FAIL，用于修复后的全绿验收。
    """
    if strict or spec.expect != "fail":
        return raw_status
    if raw_status in UNEXPECTED_BAD:
        return STATUS_XFAIL
    if raw_status == STATUS_PASS:
        return STATUS_XPASS
    return raw_status


# --------------------------------------------------------------------------
# 环境准备
# --------------------------------------------------------------------------
def setup_environment(args) -> str:
    """注入 PYTHONPATH / M2_* 环境变量，返回实际使用的解释器路径。

    ``m2_tests/common.py`` 在 **import 时**读取 M2_PREPARE 与 M2_PYTHON，
    因此这两项必须在导入测试模块之前设好。
    """
    python_exe = args.python or os.environ.get("M2_PYTHON") or sys.executable

    existing = os.environ.get("PYTHONPATH", "")
    parts = [str(REPO_ROOT), str(VGGT_MAIN)]
    if existing:
        parts.append(existing)
    os.environ["PYTHONPATH"] = os.pathsep.join(parts)

    os.environ["M2_PYTHON"] = python_exe
    os.environ["M2_PREPARE"] = "0" if args.no_prepare else "1"

    for path in (str(RUNNER_DIR), str(REPO_ROOT)):
        if path not in sys.path:
            sys.path.insert(0, path)
    return python_exe


def force_utf8_stdout() -> None:
    """Windows 控制台默认 GBK，中文用例名会抛 UnicodeEncodeError。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


# --------------------------------------------------------------------------
# 输出渲染
# --------------------------------------------------------------------------
def display_width(text: str) -> int:
    """中文按 2 列宽计算，保证表格对齐。"""
    return sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in text)


def pad(text: str, width: int, align: str = "left") -> str:
    gap = max(0, width - display_width(text))
    return (" " * gap + text) if align == "right" else (text + " " * gap)


STATUS_COLOR = {
    STATUS_PASS: "\033[32m", STATUS_FAIL: "\033[31m", STATUS_ERROR: "\033[31m",
    STATUS_SKIP: "\033[33m", STATUS_XFAIL: "\033[36m", STATUS_XPASS: "\033[35m",
}
RESET = "\033[0m"


def colorize(text: str, color: str, enabled: bool) -> str:
    return "%s%s%s" % (color, text, RESET) if enabled else text


def status_text(status: str, enabled: bool, width: int = 6) -> str:
    """渲染状态列；``width=0`` 表示不填充（用于逐条进度行）。"""
    text = pad(status, width) if width else status
    return colorize(text, STATUS_COLOR.get(status, ""), enabled)


def banner(lines, use_color: bool) -> list:
    rule = "=" * 78
    return [colorize(rule, "\033[36m", use_color)] + lines + [colorize(rule, "\033[36m", use_color)]


# --------------------------------------------------------------------------
# 归档
# --------------------------------------------------------------------------
def write_text_report(path: Path, lines) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_json_report(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv_report(path: Path, results) -> None:
    """utf-8-sig：Excel 直接双击打开不乱码。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["用例编号", "结果", "原始结果", "耗时(秒)", "关联缺陷", "用例名称", "详情"])
        for r in results:
            writer.writerow([
                r.spec.label, r.status, r.raw_status, "%.2f" % r.seconds,
                r.spec.defect or "", r.spec.title, r.detail,
            ])


def write_junit_report(path: Path, results, seconds: float) -> None:
    """最小可用的 JUnit XML：CI 只需 tests / failures / errors / skipped。"""
    import xml.etree.ElementTree as ET

    failures = sum(1 for r in results if r.status in (STATUS_FAIL, STATUS_ERROR))
    skipped = sum(1 for r in results if r.status == STATUS_SKIP)
    suite = ET.Element("testsuite", {
        "name": "module2-ai-output",
        "tests": str(len(results)),
        "failures": str(failures),
        "errors": "0",
        "skipped": str(skipped),
        "time": "%.3f" % seconds,
    })
    for r in results:
        case = ET.SubElement(suite, "testcase", {
            "classname": r.spec.cls,
            "name": r.spec.method,
            "time": "%.3f" % r.seconds,
        })
        if r.status in (STATUS_FAIL, STATUS_ERROR):
            ET.SubElement(case, "failure", {"message": r.detail[:500], "type": r.status})
        elif r.status == STATUS_SKIP:
            ET.SubElement(case, "skipped", {"message": r.detail[:500]})
        elif r.status == STATUS_XFAIL:
            ET.SubElement(case, "skipped", {"message": "预期失败（%s）：%s" % (r.spec.defect or "-", r.detail[:300])})

    path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(suite).write(path, encoding="utf-8", xml_declaration=True)


# --------------------------------------------------------------------------
# 主流程
# --------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="run_all_cases.py",
        description="VGGT 模块二用例统一运行器（M2-AI-001 ~ M2-AI-015）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--cases", default="", help="按编号选择，如 001,003,010-015")
    p.add_argument("--from", dest="from_case", default="", help="起始编号（含）")
    p.add_argument("--to", dest="to_case", default="", help="结束编号（含）")
    p.add_argument("--list", "--dry-run", dest="list_only", action="store_true",
                   help="只列出用例清单与数据就绪情况，不执行任何测试")
    p.add_argument("--strict", action="store_true",
                   help="不折算预期失败（010/015 失败即 FAIL），用于修复后验收")
    p.add_argument("--no-prepare", action="store_true",
                   help="禁用缺失数据的自动生成（等价 M2_PREPARE=0，无 GPU 时用）")
    p.add_argument("--isolated", action="store_true",
                   help="每条用例独立子进程执行（可硬超时、逐条回收显存）")
    p.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                   help="isolated 模式单条用例超时秒数（默认 %d）" % DEFAULT_TIMEOUT)
    p.add_argument("--stop-on-fail", action="store_true", help="遇到非预期失败即停止")
    p.add_argument("--fail-on-skip", action="store_true", help="把跳过也视为失败")
    p.add_argument("--python", default="", help="指定 Python 解释器（供子进程与 GPU 用例使用）")
    p.add_argument("--quiet", action="store_true", help="不打印逐条进度，只打印汇总")
    p.add_argument("--no-color", action="store_true", help="关闭彩色输出")
    p.add_argument("--no-log", action="store_true", help="不写归档文件")
    p.add_argument("--junit", default="", help="额外输出 JUnit XML 的路径")
    p.add_argument("--json", dest="json_out", default="", help="额外输出 JSON 的路径")
    p.add_argument("--csv", dest="csv_out", default="", help="额外输出 CSV 的路径")
    # 内部参数：隔离子进程执行单条用
    p.add_argument("--_execute", default="", help=argparse.SUPPRESS)
    p.add_argument("--_json-out", default="", help=argparse.SUPPRESS)
    return p


def main(argv=None) -> int:
    force_utf8_stdout()
    args = build_parser().parse_args(argv)
    use_color = not args.no_color

    # ---- 内部模式：子进程只跑一条用例，结果写 JSON 后退出 ----
    if args._execute:
        return _execute_child(args)

    python_exe = setup_environment(args)

    problems = preflight()
    if problems:
        print("[错误] 测试工程不完整：")
        for item in problems:
            print("       - %s" % item)
        return 2

    specs, discover_problems = discover_specs()

    # ---- 清单模式 ----
    if args.list_only:
        return _print_listing(specs, discover_problems, args, python_exe, use_color)

    selected = select_specs(specs, args)
    if not selected:
        print("[错误] 选择器没有匹配到任何用例，请检查 --cases / --from / --to。")
        return 4

    readiness = check_readiness(selected, prepare=not args.no_prepare)

    header = banner([
        "  VGGT 模块二 · 用例统一运行器（M2-AI-001 ~ M2-AI-015）",
        "  执行时间：%s" % datetime.now().strftime("%Y-%m-%d %H:%M:%S %z"),
        "  Python  ：%s" % python_exe,
        "  仓库根  ：%s" % REPO_ROOT,
        "  运行模式：%s｜预期失败折算：%s｜自动补齐数据：%s" % (
            "逐条子进程（超时 %ds）" % args.timeout if args.isolated else "进程内逐条",
            "关闭（--strict）" if args.strict else "开启",
            "关闭（--no-prepare）" if args.no_prepare else "开启",
        ),
    ], use_color)
    for line in header:
        print(line)
    if readiness.generable:
        print("  [提示] %d 项变体产物缺失，将在执行中现场生成（需 CUDA）：%s"
              % (len(readiness.generable), "、".join(readiness.generable)))
    if readiness.missing:
        print(colorize("  [警告] %d 项产物缺失且无法自动生成，相关用例将被跳过："
                       % len(readiness.missing), "\033[33m", use_color))
        for item in readiness.missing:
            print("         - %s" % item)
    print("")

    # ---- 逐条执行 ----
    results = []
    run_started = time.perf_counter()
    for index, spec in enumerate(selected, start=1):
        if not args.quiet:
            print("[%2d/%d] %s  %s" % (index, len(selected), spec.label, spec.title))
        result = execute(spec, args)
        results.append(result)
        if not args.quiet:
            line = "        -> %s  %.2fs" % (status_text(result.status, use_color, width=0), result.seconds)
            print(line)
            if result.detail and result.status in (STATUS_SKIP,) + UNEXPECTED_BAD:
                print("           %s" % result.detail[:160])
        if args.stop_on_fail and result.status in UNEXPECTED_BAD:
            print(colorize("  [停止] 遇到非预期失败，按 --stop-on-fail 中止后续用例。",
                           "\033[31m", use_color))
            break
    total_seconds = time.perf_counter() - run_started

    # ---- 汇总 ----
    summary = summarize(results)
    report_lines = render_report(results, summary, args, python_exe, readiness, total_seconds, selected)

    if not args.quiet:
        print("")
        for line in report_lines:
            print(line)

    exit_code = decide_exit_code(results, summary, args)

    # ---- 归档 ----
    if not args.no_log:
        stamp = time.strftime("%Y%m%d_%H%M%S")
        txt_path = RESULT_DIR / ("run_all_%s.txt" % stamp)
        write_text_report(txt_path, _strip_ansi(report_lines))
        write_json_report(RESULT_DIR / ("run_all_%s.json" % stamp), build_json_payload(
            results, summary, python_exe, total_seconds, exit_code))
        write_csv_report(RESULT_DIR / ("run_all_%s.csv" % stamp), results)
        print("")
        print("  归档：%s" % txt_path)
        print("        %s" % (RESULT_DIR / ("run_all_%s.json" % stamp)))
        print("        %s" % (RESULT_DIR / ("run_all_%s.csv" % stamp)))

    for flag_path, writer in ((args.junit, "junit"), (args.json_out, "json"), (args.csv_out, "csv")):
        if not flag_path:
            continue
        target = Path(flag_path)
        if writer == "junit":
            write_junit_report(target, results, total_seconds)
        elif writer == "json":
            write_json_report(target, build_json_payload(results, summary, python_exe, total_seconds, exit_code))
        else:
            write_csv_report(target, results)
        print("  额外输出：%s" % target)

    return exit_code


def _execute_child(args) -> int:
    """隔离子进程分支：跑单条用例，把结论写成 JSON。"""
    force_utf8_stdout()
    setup_environment(args)
    specs, _ = discover_specs()
    spec = next((s for s in specs if s.cid == args._execute), None)
    if spec is None:
        payload = {"status": STATUS_ERROR, "detail": "找不到用例 M2-AI-%s" % args._execute, "seconds": 0.0}
    else:
        raw, detail, seconds = run_one_inproc(spec)
        payload = {"status": raw, "detail": detail, "seconds": seconds}

    if args._json_out:
        write_json_report(Path(args._json_out), payload)
    print(json.dumps(payload, ensure_ascii=False))
    return 0


def summarize(results) -> dict:
    counts = {key: 0 for key in (STATUS_PASS, STATUS_FAIL, STATUS_ERROR, STATUS_SKIP, STATUS_XFAIL, STATUS_XPASS)}
    for r in results:
        counts[r.status] = counts.get(r.status, 0) + 1
    counts["total"] = len(results)
    counts["seconds"] = sum(r.seconds for r in results)
    counts["unexpected"] = counts[STATUS_FAIL] + counts[STATUS_ERROR]
    return counts


def decide_exit_code(results, summary, args) -> int:
    if summary["unexpected"]:
        return 1
    if args.fail_on_skip and summary[STATUS_SKIP]:
        return 1
    if len(results) < TOTAL_CASES and not (args.cases or args.from_case or args.to_case):
        return 4
    return 0


def decide_conclusion(summary, args) -> tuple:
    """返回 (结论文本, 颜色)。"""
    if summary["unexpected"]:
        return ("存在 %d 条非预期失败/错误，请查看明细与归档日志。"
                % summary["unexpected"], "\033[31m")
    if args.fail_on_skip and summary[STATUS_SKIP]:
        return ("有 %d 条用例被跳过，且启用了 --fail-on-skip。" % summary[STATUS_SKIP], "\033[31m")
    if summary[STATUS_XPASS]:
        return ("全部符合预期，但有 %d 条「预期失败」的用例通过了（XPASS）——"
                "对应缺陷可能已修复，请复核缺陷报告与用例清单。"
                % summary[STATUS_XPASS], "\033[35m")
    if summary[STATUS_SKIP]:
        return ("符合预期（%d 条通过、%d 条预期失败）；另有 %d 条跳过，"
                "如需完整执行请补齐数据或开启自动生成。"
                % (summary[STATUS_PASS], summary[STATUS_XFAIL], summary[STATUS_SKIP]), "\033[33m")
    return ("全部符合预期：%d 条通过，%d 条预期失败（复现已知缺陷）。"
            % (summary[STATUS_PASS], summary[STATUS_XFAIL]), "\033[32m")


def render_report(results, summary, args, python_exe, readiness, total_seconds, selected) -> list:
    """生成人读汇总（返回带 ANSI 的行列表）。"""
    use_color = not args.no_color
    rule = "-" * 78
    lines = [colorize(rule, "\033[36m", use_color)]
    lines.append("  结果汇总（%d 条用例，耗时 %.1fs）" % (len(results), total_seconds))
    lines.append(colorize(rule, "\033[36m", use_color))

    head = "%s  %s  %s  %s  %s" % (
        pad("用例", 10), pad("结果", 6), pad("耗时", 8, "right"),
        pad("关联缺陷", 12), "用例名称",
    )
    lines.append(head)
    lines.append(rule)
    for r in results:
        lines.append("%s  %s  %s  %s  %s" % (
            pad(r.spec.label, 10),
            status_text(r.status, use_color),
            pad("%.2fs" % r.seconds, 8, "right"),
            pad(r.spec.defect or "-", 12),
            r.spec.title,
        ))
        if r.detail and r.status in UNEXPECTED_BAD + (STATUS_XPASS,):
            lines.append("            %s" % r.detail[:200])

    lines.append(rule)
    lines.append("  统计：执行 %d → 通过 %d｜失败 %d｜错误 %d｜跳过 %d｜预期失败 %d｜意外通过 %d" % (
        summary["total"], summary[STATUS_PASS], summary[STATUS_FAIL], summary[STATUS_ERROR],
        summary[STATUS_SKIP], summary[STATUS_XFAIL], summary[STATUS_XPASS],
    ))
    if readiness.generable:
        lines.append("  现场生成：%s" % "、".join(readiness.generable))
    if readiness.missing:
        lines.append("  产物缺失：%s" % "；".join(readiness.missing))

    conclusion, color = decide_conclusion(summary, args)
    lines.append("  结论：" + colorize(conclusion, color, use_color))
    lines.append(colorize(rule, "\033[36m", use_color))
    if summary[STATUS_XFAIL]:
        pairs = "、".join("%s→%s" % (r.spec.label, r.spec.defect or "-")
                         for r in results if r.status == STATUS_XFAIL)
        lines.append("  说明：预期失败用例 %s 复现的是清单已判定 NG 的缺陷，" % pairs)
        lines.append("        它们为 XFAIL 不构成回归；用 --strict 可在缺陷修复后做全绿验收。")
    return lines


def _print_listing(specs, discover_problems, args, python_exe, use_color) -> int:
    """--list：只列清单与就绪状态，不执行测试。"""
    readiness = check_readiness(specs, prepare=not args.no_prepare)
    rule = "-" * 78
    print("\n".join(banner([
        "  VGGT 模块二 · 用例清单（M2-AI-001 ~ M2-AI-015）",
        "  Python：%s" % python_exe,
        "  用例目录：%s" % TESTS_DIR,
    ], use_color)))
    print("")
    print("%s  %s  %s  %s  %s" % (
        pad("用例", 10), pad("预期", 6), pad("缺陷", 12), pad("来源文件", 44), "用例名称"))
    print(rule)
    for spec in specs:
        print("%s  %s  %s  %s  %s" % (
            pad(spec.label, 10),
            pad(spec.expect, 6),
            pad(spec.defect or "-", 12),
            pad(spec.source, 44),
            spec.title,
        ))
    print(rule)
    print("  共 %d 条用例；预期通过 %d 条，预期失败 %d 条（复现已知缺陷）" % (
        len(specs),
        sum(1 for s in specs if s.expect == "pass"),
        sum(1 for s in specs if s.expect == "fail"),
    ))
    print("  已就绪产物：%d 项" % len(readiness.ready))
    if readiness.generable:
        print("  可现场生成（需 CUDA）：%s" % "、".join(readiness.generable))
    if readiness.missing:
        print(colorize("  缺失且不可自动生成：%s" % "；".join(readiness.missing), "\033[33m", use_color))
    for problem in discover_problems:
        print(colorize("  [发现问题] %s" % problem, "\033[33m", use_color))
    print("\n  本机未执行任何测试（--list 为只读模式）。")
    return 0 if not discover_problems else 4


def build_json_payload(results, summary, python_exe, total_seconds, exit_code) -> dict:
    return {
        "suite": "module2-ai-output",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "python": python_exe,
        "repo_root": str(REPO_ROOT),
        "exit_code": exit_code,
        "duration_seconds": round(total_seconds, 3),
        "summary": summary,
        "cases": [{
            "id": r.spec.label,
            "title": r.spec.title,
            "status": r.status,
            "raw_status": r.raw_status,
            "expect": r.spec.expect,
            "defect": r.spec.defect,
            "seconds": round(r.seconds, 3),
            "source": r.spec.source,
            "method": r.spec.qualified_name,
            "detail": r.detail,
        } for r in results],
    }


_ANSI_RE = re.compile(r"\033\[[0-9;]*m")


def _strip_ansi(lines) -> list:
    """归档文本去掉颜色转义，便于直接阅读与粘贴。"""
    return [_ANSI_RE.sub("", line) for line in lines]


if __name__ == "__main__":
    raise SystemExit(main())
