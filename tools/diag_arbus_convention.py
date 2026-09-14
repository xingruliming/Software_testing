#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""判定 009_arbus 上 VGGT 的相对旋转到底做对没有。

思路：相机的相对旋转**角度**是共轭不变量 —— OpenGL/OpenCV 约定之间只差一个
diag(1,-1,-1) 的共轭，角度不变。所以「预测的相对旋转角度」vs「真值的相对旋转
角度」这两个纯标量可以直接比，不受约定影响。

再对若干候选真值换算做最小二乘，找出误差最小的口径。
"""
import glob
import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def rot_angle(R):
    return float(np.degrees(np.arccos(np.clip((np.trace(R) - 1.0) / 2.0, -1.0, 1.0))))


def angles_of(Rs, ii, jj):
    return np.array([rot_angle(Rs[j] @ Rs[i].T) for i, j in zip(ii, jj)])


def gt_candidates(meta):
    """返回若干候选的真值 c2w / w2c 口径。"""
    T = [np.array(f["transform_matrix"], dtype=np.float64).reshape(4, 4)
         for f in meta["frames"]]
    D = np.diag([1.0, -1.0, -1.0, 1.0])
    out = {}

    def add(name, c2w_list):
        R = np.array([c[:3, :3] for c in c2w_list])
        # c2w 旋转的 det 必须为 +1 才算合法旋转
        out[name] = {"R": R, "c": np.array([c[:3, 3] for c in c2w_list]),
                     "det": float(np.mean([np.linalg.det(r) for r in R]))}

    add("A: T@flip 作 c2w (当前)", [t @ D for t in T])
    add("B: T 直接作 c2w（不翻轴）", [t.copy() for t in T])
    add("C: flip@T 作 c2w", [D @ t for t in T])
    # D: 把 T 当 w2c，则 c2w = inv(T)
    add("D: T 作 w2c -> c2w=inv(T)", [np.linalg.inv(t) for t in T])
    add("E: T 作 w2c(OpenGL) -> c2w=inv(T@flip)", [np.linalg.inv(t @ D) for t in T])
    return out


def main():
    ds = os.path.join(ROOT, "vggt_input", "009_arbus")
    meta = json.load(open(os.path.join(ds, "airbus_transforms.json"), encoding="utf-8"))
    cands = gt_candidates(meta)

    print("=" * 78)
    print("候选真值换算的合法性（c2w 旋转 det 应为 +1；相机中心应落在半径≈4.06 的球上）")
    for k, v in cands.items():
        r = np.linalg.norm(v["c"] - v["c"].mean(0), axis=1)
        print(f"  {k:<32} det={v['det']:+.4f}  半径 median {np.median(r):.4f} "
              f"(std {r.std():.5f})")

    # 相邻帧方位角步进（黄金角只会在正确的口径下出现）
    print()
    print("相邻帧方位角步进（期望 137.508°）")
    for k, v in cands.items():
        c = v["c"] - v["c"].mean(0)
        az = np.degrees(np.arctan2(c[:, 2], c[:, 0])) % 360.0
        print(f"  {k:<32} median {np.median(np.diff(az) % 360):.3f}°")

    for tag in ["N02", "N08", "N16"]:
        out = os.path.join(ROOT, "vggt_output", "009_arbus_sweep", tag)
        npz, selp = os.path.join(out, "predictions.npz"), os.path.join(out, "selection.json")
        if not (os.path.exists(npz) and os.path.exists(selp)):
            continue
        sel = json.load(open(selp, encoding="utf-8"))["selected_indices"]
        with np.load(npz, allow_pickle=True) as z:
            pred = z["extrinsic"].astype(np.float64)
        n = min(len(pred), len(sel))
        P4 = np.zeros((n, 4, 4)); P4[:, :3, :4] = pred[:n]; P4[:, 3, 3] = 1.0
        # 预测：extrinsic 是 w2c -> c2w
        Rp = np.linalg.inv(P4)[:, :3, :3]
        ii, jj = np.triu_indices(n, k=1)
        ap = angles_of(Rp, ii, jj)

        print()
        print("=" * 78)
        print(f"[{tag}] 帧 {n}  对数 {len(ii)}")
        print(f"  预测相对旋转角度: mean {ap.mean():7.2f}°  median {np.median(ap):7.2f}°  "
              f"max {ap.max():7.2f}°")
        for k, v in cands.items():
            Rg = v["R"][sel]
            ag = angles_of(Rg, ii, jj)
            if len(ap) > 1:
                c = float(np.corrcoef(ap, ag)[0, 1])
            else:
                c = float("nan")
            print(f"  {k:<32} GT角度 mean {ag.mean():7.2f}° median {np.median(ag):7.2f}°  "
                  f"角度相关 r={c:+.4f}  绝对差 mean {np.abs(ap-ag).mean():6.2f}°")


if __name__ == "__main__":
    main()
