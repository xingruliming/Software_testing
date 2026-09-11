#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
robustness_experiments.py —— 模块二鲁棒性实验批量驱动

一次性完成：生成扰动输入 → 调用 run_vggt_inference.py 推理 → 调用 metrics.py 算指标
→ 汇总成 summary.json / summary.md，供测试报告引用。

用法（在仓库根目录执行）：
    D:\\anaconda3\\envs\\Pytorch_Vggt\\python.exe tools/robustness_experiments.py

实验设计（基准场景 002_computer，9 帧）：
    N1 / N2 / N5            帧数扫描（取前 N 帧）
    res50                   分辨率降为 0.5 倍
    noise10                 高斯噪声 sigma=10（0-255 尺度）
    occ25                   随机遮挡约 25% 面积
    det2                    原始 9 帧重跑一次，用于确定性比对

产物：
    vggt_output/exp/_inputs/<变体>/     扰动后的输入图（PNG）
    vggt_output/exp/<变体>/             推理产物（depth/ + predictions.npz + run_info.json）
    vggt_output/exp/<变体>/metrics.json 自洽性指标
    vggt_output/exp/summary.json        汇总表
    vggt_output/exp/summary.md          汇总表（Markdown）
"""

import json
import os
import shutil
import subprocess
import sys
import time

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PYTHON = r"D:\anaconda3\envs\Pytorch_Vggt\python.exe"
BASE_INPUT = os.path.join(ROOT, "vggt_input", "002_computer")
EXP_ROOT = os.path.join(ROOT, "vggt_output", "exp")
INPUT_ROOT = os.path.join(EXP_ROOT, "_inputs")
BASELINE_NPZ = os.path.join(ROOT, "vggt_output", "002_computer", "predictions.npz")

SEED = 20260911


def list_base_images():
    files = sorted(
        os.path.join(BASE_INPUT, f) for f in os.listdir(BASE_INPUT)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    )
    return files


def write_images(paths, out_dir):
    """把图像数组按 ASCII 序号命名写成 PNG，避免中文名带来的额外变量。"""
    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    for i, im in enumerate(paths):
        Image.fromarray(im).save(os.path.join(out_dir, f"{i:06d}.png"))
    return out_dir


def to_array(path):
    return np.asarray(Image.open(path).convert("RGB"))


def add_gaussian_noise(imgs, sigma):
    rng = np.random.default_rng(SEED)
    out = []
    for im in imgs:
        noise = rng.normal(0.0, sigma, im.shape)
        out.append(np.clip(im.astype(np.float32) + noise, 0, 255).astype(np.uint8))
    return out


def add_occlusion(imgs, ratio):
    """随机遮挡：每帧贴若干实心矩形，累计面积约 ratio。"""
    rng = np.random.default_rng(SEED)
    out = []
    for im in imgs:
        h, w = im.shape[:2]
        img = im.copy()
        remain = ratio
        while remain > 0.01:
            r = min(0.12, remain)
            bh = max(8, int(h * np.sqrt(r)))
            bw = max(8, int(w * np.sqrt(r)))
            y = int(rng.integers(0, max(1, h - bh)))
            x = int(rng.integers(0, max(1, w - bw)))
            img[y:y + bh, x:x + bw] = 0
            remain -= r
        out.append(img)
    return out


def resize_images(imgs, scale):
    out = []
    for im in imgs:
        h, w = im.shape[:2]
        small = Image.fromarray(im).resize((max(8, int(w * scale)), max(8, int(h * scale))), Image.LANCZOS)
        out.append(np.asarray(small))
    return out


def run_inference(in_dir, out_dir):
    cmd = [
        PYTHON, os.path.join(ROOT, "run_vggt_inference.py"),
        "--input-dir", in_dir,
        "--output-dir", out_dir,
        "--prediction-modes", "",          # 本批实验只关心深度图与 npz，不导 GLB
    ]
    t0 = time.time()
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    return proc.returncode, time.time() - t0, (proc.stdout or "") + (proc.stderr or "")


def run_metrics(npz_path, conf_thres, out_json):
    cmd = [PYTHON, os.path.join(ROOT, "metrics.py"), npz_path,
           "--conf-thres", str(conf_thres), "--json", out_json]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    if not os.path.isfile(out_json):
        return None
    with open(out_json, encoding="utf-8") as fh:
        data = json.load(fh)
    return {m["metric"]: m for m in data.get("metrics", [])}


def pick(metrics, name, keys):
    m = (metrics or {}).get(name) or {}
    return {k: m.get(k) for k in keys}


def main():
    base_paths = list_base_images()
    base_imgs = [to_array(p) for p in base_paths]
    print(f"[准备] 基准图像 {len(base_imgs)} 张，尺寸 {base_imgs[0].shape}")

    variants = [
        ("N1", lambda imgs: imgs[:1]),
        ("N2", lambda imgs: imgs[:2]),
        ("N5", lambda imgs: imgs[:5]),
        ("res50", lambda imgs: resize_images(imgs, 0.5)),
        ("noise10", lambda imgs: add_gaussian_noise(imgs, 10.0)),
        ("occ25", lambda imgs: add_occlusion(imgs, 0.25)),
        ("det2", lambda imgs: imgs),
    ]

    summary = []
    for name, fn in variants:
        print("=" * 70)
        print(f"[变体] {name}")
        in_dir = write_images(fn(base_imgs), os.path.join(INPUT_ROOT, name))
        out_dir = os.path.join(EXP_ROOT, name)
        os.makedirs(out_dir, exist_ok=True)

        rc, secs, log = run_inference(in_dir, out_dir)
        with open(os.path.join(out_dir, "inference.log"), "w", encoding="utf-8") as fh:
            fh.write(log)
        if rc != 0:
            print(f"  推理失败 rc={rc}，见 {out_dir}/inference.log")
            summary.append({"variant": name, "status": f"inference_failed(rc={rc})"})
            continue
        print(f"  推理完成 {secs:.1f} s")

        # 001 类低置信场景用 1.0 阈值，其余用默认 3.0
        metrics = run_metrics(os.path.join(out_dir, "predictions.npz"), 3.0,
                              os.path.join(out_dir, "metrics.json"))
        if metrics and not metrics.get("pointmap_vs_depth", {}).get("available", False):
            metrics = run_metrics(os.path.join(out_dir, "predictions.npz"), 1.0,
                                  os.path.join(out_dir, "metrics_ct1.json"))

        run_info = {}
        info_path = os.path.join(out_dir, "run_info.json")
        if os.path.isfile(info_path):
            with open(info_path, encoding="utf-8") as fh:
                run_info = json.load(fh)

        entry = {
            "variant": name,
            "status": "ok",
            "frames": run_info.get("num_images"),
            "tensor_shape": (run_info.get("inference") or {}).get("image_shape"),
            "model_load_s": (run_info.get("inference") or {}).get("model_load_seconds"),
            "inference_s": (run_info.get("inference") or {}).get("inference_seconds"),
            "peak_gpu_gb": (run_info.get("inference") or {}).get("peak_gpu_memory_gb"),
            "wall_s": round(secs, 2),
            "g1": pick(metrics, "pointmap_vs_depth",
                       ["available", "valid_ratio", "mean_l2", "rel_mean_l2", "scene_scale"]),
            "g2": pick(metrics, "pointmap_vs_camera",
                       ["available", "pix_err_mean", "pix_err_p90", "pix_err_lt5px_ratio", "z_rel_mean"]),
            "g3": {
                "depth_conf_mean": ((metrics or {}).get("confidence") or {}).get("depth_conf", {}).get("mean"),
                "depth_conf_max": ((metrics or {}).get("confidence") or {}).get("depth_conf", {}).get("max"),
                "low_ratio": ((metrics or {}).get("confidence") or {}).get("depth_conf", {}).get("low_ratio_lt_thres"),
                "wp_conf_mean": ((metrics or {}).get("confidence") or {}).get("world_points_conf", {}).get("mean"),
            },
            "g4": pick(metrics, "photometric",
                       ["available", "valid_proj_ratio_mean", "photometric_l1_mean", "ncc_mean", "ncc_min"]),
        }
        summary.append(entry)
        print(f"  G1 rel={entry['g1'].get('rel_mean_l2')} G2 px={entry['g2'].get('pix_err_mean')} "
              f"G4 ncc={entry['g4'].get('ncc_mean')}")

    # ---- 确定性比对：det2 vs 既有 002_computer ----
    det = {"checked": False}
    det_npz = os.path.join(EXP_ROOT, "det2", "predictions.npz")
    if os.path.isfile(det_npz) and os.path.isfile(BASELINE_NPZ):
        a = np.load(BASELINE_NPZ, allow_pickle=True)
        b = np.load(det_npz, allow_pickle=True)
        keys = [k for k in ("depth", "world_points", "extrinsic", "intrinsic") if k in a.files and k in b.files]
        det = {"checked": True, "baseline": BASELINE_NPZ, "rerun": det_npz, "fields": {}}
        for k in keys:
            x, y = np.asarray(a[k]), np.asarray(b[k])
            if x.shape != y.shape:
                det["fields"][k] = {"shape_baseline": list(x.shape), "shape_rerun": list(y.shape)}
                continue
            diff = np.abs(x.astype(np.float64) - y.astype(np.float64))
            det["fields"][k] = {
                "identical": bool(np.array_equal(x, y)),
                "max_abs_diff": float(diff.max()),
                "mean_abs_diff": float(diff.mean()),
            }
        print("[确定性] " + json.dumps(det["fields"], ensure_ascii=False))

    os.makedirs(EXP_ROOT, exist_ok=True)
    payload = {
        "baseline_scene": BASE_INPUT,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "conf_thres_default": 3.0,
        "determinism": det,
        "variants": summary,
    }
    with open(os.path.join(EXP_ROOT, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)

    # Markdown 汇总
    lines = ["| 变体 | 帧数 | 张量形状 | 加载(s) | 推理(s) | 峰值显存(GB) | G1 相对误差 | G2 像素误差 | G2 <5px | G3 置信均值 | G3 低置信占比 | G4 NCC |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for e in summary:
        if e.get("status") != "ok":
            lines.append(f"| {e['variant']} | — | — | — | — | — | — | — | — | — | — | — |  # {e.get('status')}")
            continue
        lines.append(
            f"| {e['variant']} | {e['frames']} | {e['tensor_shape']} | {e['model_load_s']} | "
            f"{e['inference_s']} | {e['peak_gpu_gb']} | {e['g1'].get('rel_mean_l2')} | "
            f"{e['g2'].get('pix_err_mean')} | {e['g2'].get('pix_err_lt5px_ratio')} | "
            f"{e['g3'].get('depth_conf_mean')} | {e['g3'].get('low_ratio')} | {e['g4'].get('ncc_mean')} |")
    with open(os.path.join(EXP_ROOT, "summary.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    print("=" * 70)
    print("全部实验完成 ->", os.path.join(EXP_ROOT, "summary.md"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
