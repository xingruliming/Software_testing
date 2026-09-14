#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把 GLB 里的点云渲染成三视图正交投影，用于肉眼核验重建结果。

用法：
    python tools/make_pointcloud_compare.py OUT.png 上排.glb 下排.glb [--max-points 60000]

典型用途：对比"掩码前（含背景）"与"掩码后（只剩目标物体）"。
"""
import argparse
import os
import sys

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt          # noqa: E402


def largest_points(glb):
    """取 GLB 中最大的点云几何体，返回 (vertices, colors|None)。"""
    import trimesh
    scene = trimesh.load(glb)
    best = None
    for g in scene.geometry.values():
        if hasattr(g, "vertices") and len(g.vertices) > 100:
            if best is None or len(g.vertices) > len(best[0]):
                best = (np.asarray(g.vertices, dtype=np.float64),
                        getattr(g, "colors", None))
    if best is None:
        raise RuntimeError(f"{glb} 里没有找到点云几何体")
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out_png")
    ap.add_argument("glbs", nargs="+", help="每行一个 GLB，按顺序从上到下排")
    ap.add_argument("--labels", nargs="*", default=None, help="每行标题（纯 ASCII 更稳）")
    ap.add_argument("--max-points", type=int, default=60000)
    args = ap.parse_args()

    n = len(args.glbs)
    labels = args.labels or [os.path.basename(p) for p in args.glbs]
    pairs = [(0, 1, "view XY"), (0, 2, "view XZ"), (1, 2, "view YZ")]

    fig, axes = plt.subplots(n, 3, figsize=(13, 4 * n), squeeze=False)
    for r, glb in enumerate(args.glbs):
        v, c = largest_points(glb)
        if c is None:
            c = np.ones((len(v), 3)) * 0.5
        c = np.asarray(c)[:, :3] / 255.0
        idx = np.random.default_rng(0).choice(
            len(v), size=min(len(v), args.max_points), replace=False)
        vv, cc = v[idx], c[idx]
        ext = v.max(0) - v.min(0)
        print(f"{labels[r]}: {len(v)} 点  包围盒对角线 {np.linalg.norm(ext):.3f}")
        for col, (a, b, nm) in enumerate(pairs):
            ax = axes[r][col]
            ax.scatter(vv[:, a], vv[:, b], s=0.6, c=cc, linewidths=0, alpha=0.85)
            ax.set_title(f"{labels[r]}  |  {nm}", fontsize=9)
            ax.set_aspect("equal")
            ax.set_xticks([]); ax.set_yticks([])
    plt.tight_layout()
    plt.savefig(args.out_png, dpi=110)
    print(f"-> {args.out_png}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
