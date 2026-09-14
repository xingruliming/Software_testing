#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""验证相对平移误差的尺度归一化问题。

现象：预测相机半径 / 真值相机半径 ≈ 0.25（恒定），说明预测与真值只差一个
全局尺度 —— 这是规范自由度，不该计入误差。

但 relative_pose_metrics 里：
    dt_p = T_pred 的平移（带预测尺度）
    scale = 真值相机中心成对距离中位数（真值尺度）
    err = ||dt_p - dt_g|| / scale * 100
两者尺度不同源，s 不会抵消 → 误差凭空多出 (1-s) 量级。s=0.25 时约 75%。

正确做法：先把预测整体缩放到真值尺度（除以 s_pred/scale_gt），再比较。
"""
import json
import os

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def ang(R):
    return float(np.degrees(np.arccos(np.clip((np.trace(R) - 1.0) / 2.0, -1.0, 1.0))))


def load_gt_w2c(path):
    meta = json.load(open(path, encoding="utf-8"))
    flip = np.diag([1.0, -1.0, -1.0, 1.0])
    out = []
    for f in meta["frames"]:
        T = np.array(f["transform_matrix"], dtype=np.float64).reshape(4, 4)
        c2w = T @ flip
        R, t = c2w[:3, :3], c2w[:3, 3]
        M = np.eye(4); M[:3, :3] = R.T; M[:3, 3] = -R.T @ t
        out.append(M)
    return np.array(out)


def main():
    gt = load_gt_w2c(os.path.join(ROOT, "vggt_input", "009_arbus",
                                 "airbus_transforms.json"))
    print(f"{'N':<6}{'尺度比s':>10}{'旧公式%':>10}{'按预测尺度归一%':>16}{'缩放对齐后%':>14}")
    print("-" * 58)
    for tag in ["N02", "N04", "N08", "N16", "N32"]:
        d = os.path.join(ROOT, "vggt_output", "009_arbus_sweep", tag)
        if not os.path.exists(os.path.join(d, "predictions.npz")):
            continue
        sel = json.load(open(os.path.join(d, "selection.json"), encoding="utf-8"))["selected_indices"]
        with np.load(os.path.join(d, "predictions.npz"), allow_pickle=True) as z:
            pred = z["extrinsic"].astype(np.float64)
        n = min(len(pred), len(sel))
        wp = np.zeros((n, 4, 4)); wp[:, :3, :4] = pred[:n]; wp[:, 3, 3] = 1.0
        wg = np.array([gt[sel[k]] for k in range(n)])

        cp = np.linalg.inv(wp)[:, :3, 3]      # 预测相机中心
        cg = np.linalg.inv(wg)[:, :3, 3]      # 真值相机中心
        ii, jj = np.triu_indices(n, k=1)
        dp = np.linalg.norm(cp[ii] - cp[jj], axis=1)
        dg = np.linalg.norm(cg[ii] - cg[jj], axis=1)
        sp, sg = float(np.median(dp)), float(np.median(dg))
        s_ratio = sp / sg
        s = sg / sp                            # 把预测缩放到真值尺度

        e_old, e_prednorm, e_scaled = [], [], []
        for i, j in zip(ii, jj):
            Tp = wp[j] @ np.linalg.inv(wp[i])
            Tg = wg[j] @ np.linalg.inv(wg[i])
            dtp, dtg = Tp[:3, 3], Tg[:3, 3]
            e_old.append(np.linalg.norm(dtp - dtg) / sg * 100.0)
            e_prednorm.append(np.linalg.norm(dtp / sp - dtg / sg) * 100.0)
            e_scaled.append(np.linalg.norm(s * dtp - dtg) / sg * 100.0)
        print(f"{tag:<6}{s_ratio:>10.4f}{np.mean(e_old):>10.2f}"
              f"{np.mean(e_prednorm):>16.2f}{np.mean(e_scaled):>14.2f}")

    print()
    print("尺度比s = 预测相机半径 / 真值相机半径（恒为常数即纯粹是尺度规范自由度）")
    print("旧公式      = 现状：用真值尺度去除预测平移 -> 混入 (1-s) 的虚假误差")
    print("按预测尺度归一 = 预测/真值各自用自身尺度归一，再比方向（标准做法之一）")
    print("缩放对齐后   = 先把预测整体缩放到真值尺度再比（与上面的等价）")


if __name__ == "__main__":
    main()
