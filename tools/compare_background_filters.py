#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""定量对比三种去背景方案在 009_arbus 上的效果。

方案：
  A. 原始（不做任何背景过滤）
  B. GT 掩码过滤（tools/mask_pointcloud_export.py，conf 置 0 + conf_thres=0.0）
  C. 内置白底过滤（run_vggt_inference.py --mask-white-bg，conf_thres=50 百分位 + RGB>240 判白）

关键指标：**残留背景点数** = 保留下来的、落在 GT 掩码之外的点。
它直接量出"白底没剔干净"的程度（抗锯齿边缘像素颜色不完全白，阈值法删不掉）。
"""
import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "vggt-main"))
import cv2  # noqa: E402


def gt_keep(S, H, W, masks_dir, sel, erode_px):
    keep = np.ones((S, H, W), dtype=bool)
    files = sorted(f for f in os.listdir(masks_dir) if f.lower().endswith(".png"))
    for k in range(S):
        img = cv2.imdecode(np.fromfile(os.path.join(masks_dir, files[sel[k]]), np.uint8),
                           cv2.IMREAD_UNCHANGED)
        m = img[..., 0] if img.ndim == 3 else img
        m = cv2.resize(m, (W, H), interpolation=cv2.INTER_LINEAR)
        if erode_px > 0:
            ker = np.ones((2 * erode_px + 1, 2 * erode_px + 1), np.uint8)
            m = cv2.erode(m, ker, iterations=1)
        keep[k] = m > 127
    return keep


def bbox_diag(pts):
    return float(np.linalg.norm(pts.max(0) - pts.min(0)))


def main():
    tag = "N32"
    d = os.path.join(ROOT, "vggt_output", "009_arbus_sweep", tag)
    masks_dir = os.path.join(ROOT, "vggt_input", "009_arbus", "masks")
    sel = json.load(open(os.path.join(d, "selection.json"), encoding="utf-8"))["selected_indices"]

    with np.load(os.path.join(d, "predictions.npz"), allow_pickle=True) as z:
        wp = z["world_points"].astype(np.float32)
        conf = z["world_points_conf"].astype(np.float32)
        imgs = z["images"].astype(np.float32)
    S, H, W, _ = wp.shape
    total = S * H * W
    print(f"[{tag}] 总像素 {total}")

    rgb = imgs.transpose(0, 2, 3, 1)
    if rgb.max() <= 1.5:
        rgb = rgb * 255.0
    white = (rgb[..., 0] > 240) & (rgb[..., 1] > 240) & (rgb[..., 2] > 240)

    keep_gt = gt_keep(S, H, W, masks_dir, sel, erode_px=1)

    # --- A 原始：predictions_to_glb 默认 conf_thres=50 百分位（不剔白底）---
    thr50 = float(np.percentile(conf, 50))
    mask_a = (conf >= thr50) & (conf > 1e-5)

    # --- C 白底过滤：同一个 conf 阈值，再叠加非白 ---
    mask_c = mask_a & (~white)

    # --- B GT 掩码：掩码为唯一过滤器（conf 置 0 后 conf_thres=0.0）---
    mask_b = keep_gt & (conf > 1e-5)

    rows = []
    for name, m in (("A 原始(conf p50)", mask_a),
                    ("B GT掩码+腐蚀1px", mask_b),
                    ("C 内置 --mask-white-bg", mask_c)):
        pts = wp[m]
        resid = int((m & (~keep_gt)).sum())      # 掩码之外的点 = 残留背景
        rows.append((name, int(m.sum()), m.mean() * 100, resid,
                     resid / max(m.sum(), 1) * 100, bbox_diag(pts)))

    print()
    print(f"{'方案':<24}{'保留点':>10}{'占比%':>8}{'残留背景点':>11}{'占保留%':>9}{'包围盒对角线':>12}")
    print("-" * 76)
    for r in rows:
        print(f"{r[0]:<24}{r[1]:>10}{r[2]:>8.2f}{r[3]:>11}{r[4]:>9.3f}{r[5]:>12.3f}")

    print()
    print("说明：【残留背景点】= 保留下来的点里落在 GT 掩码之外的数量。")
    print(f"      数据集中飞机真实占比（GT 掩码 腐蚀1px）约 {keep_gt.mean()*100:.2f}%。")
    print("      B 方案残留必然约 0（掩码就是过滤器），作为下界基准。")
    print("      C 方案若残留显著大于 0，说明阈值删不掉抗锯齿边缘（那里颜色不是纯白）。")

    # 与 GLB 实际点数交叉核对
    print()
    import trimesh
    for name, sub in (("B", "aircraft_only/aircraft_only_gt_erode1_predPointmap_Branch.glb"),
                      ("C", os.path.join("..", f"{tag}_whitebg",
                                         "glbscene_50.0_All_maskbFalse_maskwTrue_camTrue_skyFalse_predPointmap_Branch.glb"))):
        p = os.path.join(d, sub)
        if os.path.exists(p):
            sc = trimesh.load(p)
            n = max((len(g.vertices) for g in sc.geometry.values() if hasattr(g, "vertices")),
                    default=0)
            print(f"  GLB 实际点数 [{name}] {n}")


if __name__ == "__main__":
    main()
