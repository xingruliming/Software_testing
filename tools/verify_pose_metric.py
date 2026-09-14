#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""验证相对旋转误差的正确公式。

工程内现有写法（run_aircraft_batch.relative_pose_metrics）用的是 **c2w** 旋转：
    dR = R_c2w_j @ R_c2w_i^T ;  err = angle(dR_p @ dR_g^T)
c2w 形式对「全局坐标系选择」**不是不变量**：若预测世界系与真值世界系相差一个
全局旋转 G（R_c2w^p = G R_c2w^g），则 dR_p = G dR_g G^T，误差里会混进 G 的成分。

正确做法是用 **w2c** 旋转构造相对量：
    dW = R_w2c_j @ R_w2c_i^T ;  err = angle(dW_p @ dW_g^T)
因为 R_w2c^p = R_w2c^g G^{-1}，代入后 G 逐项抵消 → 对全局坐标系不变。
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
        M = np.eye(4)
        M[:3, :3] = R.T
        M[:3, 3] = -R.T @ t
        out.append(M)
    return np.array(out)


def main():
    gt = load_gt_w2c(os.path.join(ROOT, "vggt_input", "009_arbus",
                                 "airbus_transforms.json"))
    hdr = f"{'N':<6}{'旧公式(c2w)':>13}{'共轭对齐后':>12}{'新公式(w2c)':>13}{'GT角度均值':>12}"
    print(hdr)
    print("-" * len(hdr))
    for tag in ["N02", "N04", "N08", "N16"]:
        d = os.path.join(ROOT, "vggt_output", "009_arbus_sweep", tag)
        if not os.path.exists(os.path.join(d, "predictions.npz")):
            continue
        sel = json.load(open(os.path.join(d, "selection.json"), encoding="utf-8"))["selected_indices"]
        with np.load(os.path.join(d, "predictions.npz"), allow_pickle=True) as z:
            pred = z["extrinsic"].astype(np.float64)
        n = min(len(pred), len(sel))
        w2c_p = np.zeros((n, 4, 4)); w2c_p[:, :3, :4] = pred[:n]; w2c_p[:, 3, 3] = 1.0
        w2c_g = np.array([gt[sel[k]] for k in range(n)])

        c2w_p, c2w_g = np.linalg.inv(w2c_p), np.linalg.inv(w2c_g)
        Mp = np.array([c2w_p[k][:3, :3] for k in range(n)])
        Mg = np.array([c2w_g[k][:3, :3] for k in range(n)])

        # 最优全局旋转 G：使 M_p ≈ G M_g  ->  叠加 M_p M_g^T 后投影到 SO(3)
        H = np.zeros((3, 3))
        for k in range(n):
            H += Mp[k] @ Mg[k].T
        U, _, Vt = np.linalg.svd(H)
        G = U @ Vt
        if np.linalg.det(G) < 0:
            U[:, -1] *= -1
            G = U @ Vt

        ii, jj = np.triu_indices(n, k=1)
        e_old, e_conj, e_new, gm = [], [], [], []
        for i, j in zip(ii, jj):
            Rp = c2w_p[j][:3, :3] @ c2w_p[i][:3, :3].T
            Rg = c2w_g[j][:3, :3] @ c2w_g[i][:3, :3].T
            e_old.append(ang(Rp @ Rg.T))
            e_conj.append(ang((G @ Rp @ G.T) @ Rg.T))
            Wp = w2c_p[j][:3, :3] @ w2c_p[i][:3, :3].T
            Wg = w2c_g[j][:3, :3] @ w2c_g[i][:3, :3].T
            e_new.append(ang(Wp @ Wg.T))
            gm.append(ang(Rg))
        print(f"{tag:<6}{np.mean(e_old):>13.2f}{np.mean(e_conj):>12.2f}"
              f"{np.mean(e_new):>13.2f}{np.mean(gm):>12.2f}")

    print()
    print("旧公式 = 工程现状（c2w，受全局坐标系影响，数值虚高）")
    print("共轭对齐后 = 先把预测世界系旋到真值世界系再按旧公式算（仍不是标准做法）")
    print("新公式 = 用 w2c 相对旋转（对全局坐标系不变，才是可比较的量）")
    print("GT角度均值 = 真值自身两两相对旋转的角度，用于对照量级")


if __name__ == "__main__":
    main()
