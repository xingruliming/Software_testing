#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""诊断：009_arbus 上预测位姿与真值位姿到底差在哪。

依次检验：
 A. 真值 camera-to-world 约定是否成立（R[:,2] 是否指向物体，点积 ≈ -1）
 B. 视频/图像顺序与真值索引是否对齐
 C. 相对旋转误差在几种候选约定下分别是多少（找出正确口径）
 D. 预测相机中心的球面轨迹 vs 真值（形状是否退化）
 E. 把预测点云/中心与真值做相似变换对齐后的残差（几何是否对但口径差一个全局变换）
"""
import glob
import json
import os
import sys

import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # 工程根目录
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)


def rot_angle(R):
    return float(np.degrees(np.arccos(np.clip((np.trace(R) - 1.0) / 2.0, -1.0, 1.0))))


def load_gt(path):
    meta = json.load(open(path, encoding="utf-8"))
    flip = np.diag([1.0, -1.0, -1.0, 1.0])
    c2w_list, w2c_list, centers = [], [], []
    for fr in meta["frames"]:
        T = np.array(fr["transform_matrix"], dtype=np.float64).reshape(4, 4)
        c2w = T @ flip
        c2w_list.append(c2w)
        centers.append(c2w[:3, 3].copy())
        R, t = c2w[:3, :3], c2w[:3, 3]
        M = np.eye(4)
        M[:3, :3] = R.T
        M[:3, 3] = -R.T @ t
        w2c_list.append(M)
    return meta, c2w_list, w2c_list, np.array(centers)


def rel_rot(R):  # (n,3,3) -> list of pairwise relative rotations
    n = len(R)
    ii, jj = np.triu_indices(n, k=1)
    return np.array([R[j] @ R[i].T for i, j in zip(ii, jj)]), ii, jj


def main():
    ds = os.path.join(SCRIPT_DIR, "vggt_input", "009_arbus")
    tj = os.path.join(ds, "airbus_transforms.json")
    meta, c2w_list, w2c_list, gt_c = load_gt(tj)

    print("=" * 72)
    print("A. 真值约定检验")
    obj = gt_c.mean(axis=0)
    dots = []
    for c, c2w in zip(gt_c, c2w_list):
        d = obj - c
        d = d / np.linalg.norm(d)
        dots.append(float(c2w[:3, 2] @ d))     # 相机 +z 轴（OpenGL 朝后）与 相机->物体
    print(f"   R[:,2]·(cam->obj): mean {np.mean(dots):.4f}  min {np.min(dots):.4f}  max {np.max(dots):.4f}")
    print(f"   -> 期望接近 -1（相机 -z 指向物体）。实际 {'符合' if np.mean(dots) < -0.9 else '不符合'}")
    print(f"   轨迹半径 median {np.median(np.linalg.norm(gt_c-obj,axis=1)):.4f}（技能记录 4.062）")

    print()
    print("=" * 72)
    print("B/C/D. 逐档诊断")
    for tag in ["N02", "N04", "N08", "N16", "N32"]:
        out = os.path.join(SCRIPT_DIR, "vggt_output", "009_arbus_sweep", tag)
        npz = os.path.join(out, "predictions.npz")
        selp = os.path.join(out, "selection.json")
        if not (os.path.exists(npz) and os.path.exists(selp)):
            print(f"\n[{tag}] 缺少产物，跳过")
            continue
        sel = json.load(open(selp, encoding="utf-8"))["selected_indices"]
        with np.load(npz, allow_pickle=True) as z:
            pred = z["extrinsic"].astype(np.float64)
            wpd = z["world_points_from_depth"].astype(np.float64)

        n = min(len(pred), len(sel))
        P4 = np.zeros((n, 4, 4)); P4[:, :3, :4] = pred[:n]; P4[:, 3, 3] = 1.0
        G4 = np.array([w2c_list[sel[k]] for k in range(n)])

        Pr = np.linalg.inv(P4)[:, :3, :3]      # 预测 c2w 旋转
        Gr = np.linalg.inv(G4)[:, :3, :3]      # 真值 c2w 旋转
        dRp, ii, jj = rel_rot(Pr)
        dRg, _, _ = rel_rot(Gr)

        err = np.array([rot_angle(a @ b.T) for a, b in zip(dRp, dRg)])
        # 候选约定
        err_T = np.array([rot_angle(a.T @ b.T) for a, b in zip(dRp, dRg)])
        err_inv = np.array([rot_angle(np.linalg.inv(a) @ b.T) for a, b in zip(dRp, dRg)])
        # 真值相对旋转本身的角度（看基线是否本来就很大）
        gmag = np.array([rot_angle(b) for b in dRg])

        pc = np.linalg.inv(P4)[:, :3, 3]       # 预测相机中心
        gc = np.linalg.inv(G4)[:, :3, 3]
        pc_r = np.linalg.norm(pc - pc.mean(0), axis=1)
        gc_r = np.linalg.norm(gc - gc.mean(0), axis=1)

        print(f"\n[{tag}] 帧 {n}  对数 {len(err)}")
        print(f"   真值相对旋转角度: mean {gmag.mean():.2f}°  median {np.median(gmag):.2f}°  max {gmag.max():.2f}°")
        print(f"   误差(标准)  mean {err.mean():7.2f}°  median {np.median(err):7.2f}°")
        print(f"   误差(R^T)   mean {err_T.mean():7.2f}°  median {np.median(err_T):7.2f}°")
        print(f"   误差(inv)   mean {err_inv.mean():7.2f}°  median {np.median(err_inv):7.2f}°")
        print(f"   预测相机半径 median {np.median(pc_r):.4f} (range {pc_r.min():.3f}..{pc_r.max():.3f})")
        print(f"   真值相机半径 median {np.median(gc_r):.4f}")
        # 点云尺度
        d = np.linalg.norm(wpd.max(0) - wpd.min(0))
        print(f"   预测点云对角线 {d:.4f}   真值直径 {2*np.median(gc_r):.4f}   比值 {d/(2*np.median(gc_r)):.4f}")

        # 最佳全局旋转对齐（Kabsch）后残差
        A = Pr.reshape(-1, 3); B = Gr.reshape(-1, 3)
        H = A.T @ B
        U, S, Vt = np.linalg.svd(H)
        Ropt = Vt.T @ U.T
        if np.linalg.det(Ropt) < 0:
            Vt[-1] *= -1
            Ropt = Vt.T @ U.T
        Aa = A @ Ropt
        res = np.array([rot_angle(aa @ b.T) for aa, b in zip(Aa.reshape(-1,3,3), B.reshape(-1,3,3))])
        print(f"   Kabsch 全局对齐后逐帧旋转残差: mean {res.mean():.2f}°  median {np.median(res):.2f}°  max {res.max():.2f}°")


if __name__ == "__main__":
    main()
