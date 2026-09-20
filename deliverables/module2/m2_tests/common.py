# -*- coding: utf-8 -*-
"""模块二（AI 融合实践 · 方案 1「测 AI」）单元测试公共设施。

为 15 条用例（M2-AI-001 ~ M2-AI-015）提供统一的数据定位、指标计算、
推理调用与「数据就绪」保障，避免每个测试文件重复拼路径。

关键约定
--------
* 仓库根：由本文件位置上溯三级得到
  ``<repo>/deliverables/module2/m2_tests/common.py`` -> ``<repo>``。
* 指标来源：直接调用仓库根 ``metrics.py`` 的 ``compute_all`` 现场计算
  无真值几何自洽性指标 G1–G4，而不是读取历史 ``metrics.json``，
  这样断言针对的是「当前磁盘上的产物」而不是陈旧快照。
* GPU 数据：帧数扫描与扰动矩阵的推理产物位于 ``vggt_output/exp/<变体>/``。
  缺失时本模块按需生成（需要 CUDA 与 model.pt）；若显式设置
  ``M2_PREPARE=0``，则改为跳过相关用例并给出生成办法。

指标速查（与 metrics.py 的返回结构一一对应）
--------------------------------------------
G1 ``pointmap_vs_depth``  点图 vs 深度反投影，看 ``rel_mean_l2``
G2 ``pointmap_vs_camera`` 点图投影回自身相机，看 ``pix_err_mean`` / ``pix_err_lt5px_ratio``
G3 ``confidence``         置信度分布，看 ``depth_conf.mean`` / ``depth_conf.low_ratio_lt_thres``
G4 ``photometric``        相邻帧光度一致性，看 ``ncc_mean``
"""

from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path

# --------------------------------------------------------------------------
# 路径与常量
# --------------------------------------------------------------------------
M2_TESTS_DIR = Path(__file__).resolve().parent                  # .../module2/m2_tests
MODULE2_DIR = M2_TESTS_DIR.parent                                # .../module2
REPO_ROOT = MODULE2_DIR.parents[1]                               # .../Software_testing
VGGT_MAIN = REPO_ROOT / "vggt-main"
VGGT_OUTPUT = REPO_ROOT / "vggt_output"
EXP_ROOT = VGGT_OUTPUT / "exp"
INFERENCE_SCRIPT = REPO_ROOT / "run_vggt_inference.py"
MODEL_PATH = REPO_ROOT.parent / "model.pt"

# 把仓库根加入导入路径，使 `import metrics` 可用
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

BASE_SCENE = "002_computer"      # 9 帧横构图教室场景（基准）
WATER_SCENE = "001_watercup"     # 8 帧竖构图水杯近景（低置信对照场景）
SQUARE_VARIANT = "sq4096"        # M2-AI-012 的补白正方形变体

CONF_DEFAULT = 3.0               # 清单默认置信阈值
CONF_LOOSE = 1.0                 # M2-AI-011 下探阈值

# 是否允许在数据缺失时自动调用 GPU 推理补齐（run_tests.ps1 通过环境变量控制）
PREPARE_ENABLED = os.environ.get("M2_PREPARE", "1") != "0"

# 子进程使用的解释器：默认与当前测试进程一致（即 run_tests.ps1 探测到的那个）
PYTHON_EXE = os.environ.get("M2_PYTHON") or sys.executable

IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp")

# 基准场景的实测参考值（来自《VGGT 模块二测试用例清单》M2-AI-001）
BASELINE_G1_REL = 1.585e-3
BASELINE_G2_PX = 2.171
BASELINE_G4_NCC = 0.8729
BASELINE_CONF_MEAN = 8.125
WATER_G2_PX_CT1 = 41.447     # 清单 M2-AI-011
WATER_G1_REL_CT1 = 2.973e-2
WATER_G4_NCC_CT1 = 0.4919


# --------------------------------------------------------------------------
# 产物定位
# --------------------------------------------------------------------------
def scene_dir(scene: str) -> Path:
    return VGGT_OUTPUT / scene


def scene_npz(scene: str) -> Path:
    return scene_dir(scene) / "predictions.npz"


def exp_dir(variant: str) -> Path:
    return EXP_ROOT / variant


def exp_npz(variant: str) -> Path:
    return exp_dir(variant) / "predictions.npz"


def size_mb(path: Path) -> float:
    return path.stat().st_size / (1024 ** 2)


# --------------------------------------------------------------------------
# 指标计算（带进程内缓存）
# --------------------------------------------------------------------------
_METRIC_CACHE: dict = {}


def metrics_of(npz_path, conf_thres: float = CONF_DEFAULT, num_pairs: int = 30) -> dict:
    """调用 metrics.compute_all 计算 G1–G4；同一 (npz, 阈值) 在进程内只算一次。"""
    import metrics as metrics_mod

    key = (str(Path(npz_path).resolve()), float(conf_thres), int(num_pairs))
    if key not in _METRIC_CACHE:
        _METRIC_CACHE[key] = metrics_mod.compute_all(str(npz_path), float(conf_thres), int(num_pairs))
    return _METRIC_CACHE[key]


def pick(results: dict, metric_name: str) -> dict:
    """从 compute_all 结果里取出某一项指标（如 'pointmap_vs_depth'）。"""
    for item in results.get("metrics", []):
        if item.get("metric") == metric_name:
            return item
    raise KeyError("指标 %s 不在结果中：%s" % (metric_name, list(results.get("metrics", []))))


def is_available(results: dict, metric_name: str) -> bool:
    return bool(pick(results, metric_name).get("available"))


def g1_rel(results: dict):
    return pick(results, "pointmap_vs_depth").get("rel_mean_l2")


def g2_px(results: dict):
    return pick(results, "pointmap_vs_camera").get("pix_err_mean")


def g3_conf_mean(results: dict):
    conf = pick(results, "confidence").get("depth_conf") or {}
    return conf.get("mean")


def g3_low_ratio(results: dict):
    conf = pick(results, "confidence").get("depth_conf") or {}
    return conf.get("low_ratio_lt_thres")


def g4_ncc(results: dict):
    return pick(results, "photometric").get("ncc_mean")


# --------------------------------------------------------------------------
# 推理调用与数据就绪
# --------------------------------------------------------------------------
def _robustness_module():
    """延迟导入 tools/robustness_experiments.py，复用其变体生成与推理封装。"""
    tools_dir = str(REPO_ROOT / "tools")
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    import robustness_experiments as rx  # noqa: WPS433

    return rx


def run_inference(input_dir, output_dir, prediction_modes: str = "", timeout: int = 1800):
    """调用 run_vggt_inference.py（子进程）。返回 CompletedProcess。

    ``prediction_modes=""`` 表示只出深度图与 npz，不导出 GLB（省时省盘）。
    """
    cmd = [
        PYTHON_EXE, str(INFERENCE_SCRIPT),
        "--input-dir", str(input_dir),
        "--output-dir", str(output_dir),
        "--prediction-modes", prediction_modes,
    ]
    return subprocess.run(
        cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=timeout,
    )


def _skip(reason: str):
    raise unittest.SkipTest(reason)


def need_variant(variant: str) -> Path:
    """确保 ``vggt_output/exp/<variant>/`` 的推理产物存在。

    存在则直接返回 npz 路径；缺失且允许自动生成时现场跑一次推理；
    否则跳过用例（附生成办法）。
    """
    npz = exp_npz(variant)
    if npz.is_file():
        return npz
    if not PREPARE_ENABLED:
        _skip(
            "缺少实验产物 %s（M2_PREPARE=0 已禁用自动生成）。"
            "先执行：python tools/robustness_experiments.py" % npz
        )
    _prepare_variant(variant)
    if not npz.is_file():
        _skip("自动生成 %s 未产出 predictions.npz，请检查 GPU 环境与日志" % variant)
    return npz


def _prepare_variant(variant: str) -> Path:
    """按变体名生成扰动输入并推理（复用 tools/robustness_experiments.py）。"""
    rx = _robustness_module()
    base_imgs = [rx.to_array(p) for p in rx.list_base_images()]

    builders = {
        "N1": lambda imgs: imgs[:1],
        "N2": lambda imgs: imgs[:2],
        "N5": lambda imgs: imgs[:5],
        "res50": lambda imgs: rx.resize_images(imgs, 0.5),
        "noise10": lambda imgs: rx.add_gaussian_noise(imgs, 10.0),
        "occ25": lambda imgs: rx.add_occlusion(imgs, 0.25),
        "det2": lambda imgs: imgs,
    }
    if variant not in builders:
        _skip("未知变体 %s，且磁盘上没有既有产物" % variant)

    in_dir = rx.write_images(builders[variant](base_imgs), str(rx.INPUT_ROOT / variant))
    out_dir = str(rx.EXP_ROOT / variant)
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    rc, secs, log = rx.run_inference(in_dir, out_dir)
    (Path(out_dir) / "inference.log").write_text(log, encoding="utf-8")
    if rc != 0:
        _skip("生成变体 %s 失败（rc=%d），见 %s/inference.log" % (variant, rc, out_dir))
    return Path(out_dir)


def need_square_case() -> Path:
    """确保 M2-AI-012 的「补白正方形」变体存在（输入补白 + 推理 + 指标）。"""
    npz = exp_npz(SQUARE_VARIANT)
    if npz.is_file():
        return npz
    if not PREPARE_ENABLED:
        _skip(
            "缺少补白正方形变体 %s（M2_PREPARE=0 已禁用自动生成）；"
            "删除 vggt_output/exp/%s 后重跑一键脚本即可生成" % (npz, SQUARE_VARIANT)
        )
    _prepare_square()
    if not npz.is_file():
        _skip("补白正方形变体生成失败，请检查 GPU 环境与 %s" % (exp_dir(SQUARE_VARIANT) / "inference.log"))
    return npz


def _prepare_square() -> Path:
    """把 001_watercup 竖构图居中补白成正方形，使其在 crop 预处理下不再被裁切。

    帧集以原场景 ``run_info.json`` 记录的 ``image_names`` 为准：
    输入目录里可能混有非本场景的图片（如后期放入的截图），若直接整目录取图，
    补白变体就会与原竖构图产物不同帧数，对照实验失去可比性。
    """
    import json

    from PIL import Image

    rx = _robustness_module()
    src_dir = REPO_ROOT / "vggt_input" / WATER_SCENE

    info_path = scene_dir(WATER_SCENE) / "run_info.json"
    names = []
    if info_path.is_file():
        info = json.loads(info_path.read_text(encoding="utf-8"))
        names = [n for n in (info.get("image_names") or []) if (src_dir / n).is_file()]

    if names:
        src = [src_dir / n for n in names]
    else:
        src = sorted(p for p in src_dir.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES)
    if not src:
        _skip("找不到 %s 的输入图像，无法构建补白变体" % src_dir)

    in_dir = EXP_ROOT / "_inputs" / SQUARE_VARIANT
    in_dir.mkdir(parents=True, exist_ok=True)
    for i, p in enumerate(src):
        im = Image.open(p).convert("RGB")
        w, h = im.size
        side = max(w, h)
        canvas = Image.new("RGB", (side, side), (255, 255, 255))
        canvas.paste(im, ((side - w) // 2, (side - h) // 2))
        canvas.save(in_dir / ("%06d.png" % i))

    out_dir = exp_dir(SQUARE_VARIANT)
    out_dir.mkdir(parents=True, exist_ok=True)
    rc, secs, log = rx.run_inference(str(in_dir), str(out_dir))
    (out_dir / "inference.log").write_text(log, encoding="utf-8")
    if rc != 0:
        _skip("补白变体推理失败（rc=%d），见 %s/inference.log" % (rc, out_dir))
    rx.run_metrics(str(out_dir / "predictions.npz"), CONF_DEFAULT, str(out_dir / "metrics.json"))
    rx.run_metrics(str(out_dir / "predictions.npz"), CONF_LOOSE, str(out_dir / "metrics_ct1.json"))
    return out_dir


def cuda_available() -> bool:
    """惰性检测当前解释器的 CUDA 可用性（结果缓存，供 015 等 GPU 用例前置判断）。"""
    if not hasattr(cuda_available, "_cached"):
        try:
            proc = subprocess.run(
                [PYTHON_EXE, "-c", "import torch;print(int(torch.cuda.is_available()))"],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300,
            )
            cuda_available._cached = proc.stdout.strip().endswith("1")
        except Exception:
            cuda_available._cached = False
    return cuda_available._cached


def make_temp_case_dir(name: str) -> Path:
    """在 test_results/module2/tmp/ 下建一个干净的临时产物目录（返回路径，不创建）。"""
    base = REPO_ROOT / "test_results" / "module2" / "tmp"
    base.mkdir(parents=True, exist_ok=True)
    return base / name
