#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
metrics.py — VGGT 无真值几何自洽性指标计算

从 demo 产出的 predictions.npz 读取预测结果，计算四组**不需要真值(GT)**的测试指标：

  1. pointmap_vs_depth    点图头输出 vs 深度+位姿反投影输出的一致性
  2. pointmap_vs_camera   点图头输出投影回自身相机，与像素网格/深度的一致性
  3. confidence           置信度分布与低置信像素占比
  4. photometric          相邻帧多视图重投影的光度一致性

用法:
  python metrics.py predictions.npz
  python metrics.py predictions.npz --conf-thres 3.0 --pairs 30
  python metrics.py predictions.npz --json result.json
  python metrics.py "vggt_output/gradio/*/predictions.npz" --json all.json

字段约定（已对着 vggt 源码核实）:
  depth                    (S, H, W, 1) 相机 z 向深度
  depth_conf               (S, H, W)    深度置信度
  world_points             (S, H, W, 3) 点图头输出的世界坐标
  world_points_conf        (S, H, W)    点图置信度
  world_points_from_depth  (S, H, W, 3) 深度+位姿反投影得到的世界坐标
  extrinsic                (S, 3, 4)    OpenCV 约定，world -> cam，即 X_cam = R @ X_world + t
  intrinsic                (S, 3, 3)    像素单位，主点在图像中心 (W/2, H/2)
  images                   (S, 3, H, W) 取值 [0,1]（已 ToTensor，未做 mean/std 归一化）
"""

import argparse
import glob
import json
import os
import sys

import numpy as np

EPS = 1e-8


# ---------------------------------------------------------------------------
# 数据读取与形状规整
# ---------------------------------------------------------------------------
def load_predictions(npz_path):
    """读取 predictions.npz，把 0 维/异常维度统一规整，缺失的键返回 None。"""
    raw = np.load(npz_path, allow_pickle=True)
    pred = {}
    for key in raw.files:
        pred[key] = np.asarray(raw[key])

    # images: (S,3,H,W) -> (S,H,W,3)
    images = pred.get("images")
    if images is not None:
        if images.ndim == 4 and images.shape[1] == 3:
            images = np.transpose(images, (0, 2, 3, 1))
        pred["images"] = images.astype(np.float32)

    # depth: 统一成 (S,H,W)
    depth = pred.get("depth")
    if depth is not None:
        if depth.ndim == 4 and depth.shape[-1] == 1:
            depth = depth[..., 0]
        pred["depth"] = depth.astype(np.float32)

    for key in ("world_points", "world_points_from_depth", "extrinsic", "intrinsic"):
        if pred.get(key) is not None:
            pred[key] = pred[key].astype(np.float32)

    return pred


def infer_num_frames(pred):
    for key in ("depth", "world_points", "world_points_from_depth", "extrinsic"):
        arr = pred.get(key)
        if arr is not None and arr.ndim >= 1:
            return int(arr.shape[0])
    raise ValueError("predictions 里找不到任何含帧维度的字段")


def get_conf(pred, which, num_frames, hw):
    """取置信度图；缺失时用全 1 占位（即不做置信度过滤）。"""
    key = "depth_conf" if which == "depth" else "world_points_conf"
    conf = pred.get(key)
    if conf is None:
        return np.ones((num_frames,) + hw, dtype=np.float32), False
    if conf.ndim == 4 and conf.shape[-1] == 1:
        conf = conf[..., 0]
    return conf.astype(np.float32), True


def scene_scale(world_points, conf, conf_thres):
    """用高置信点云的包围盒对角线长度作为场景尺度，用于归一化报告相对误差。"""
    valid = np.isfinite(world_points).all(axis=-1) & (conf >= conf_thres)
    if valid.sum() < 16:
        valid = np.isfinite(world_points).all(axis=-1)
    if valid.sum() < 16:
        return 1.0
    pts = world_points[valid]
    lo, hi = pts.min(axis=0), pts.max(axis=0)
    diag = float(np.linalg.norm(hi - lo))
    return diag if diag > EPS else 1.0


# ---------------------------------------------------------------------------
# 双线性采样（避免依赖 scipy）
# ---------------------------------------------------------------------------
def bilinear_sample(img, u, v):
    """
    在 img (H,W,C) 上按浮点坐标 (u=列, v=行) 做双线性采样。
    返回 (H,W,C)；越界坐标会被夹到边界。
    """
    h, w = img.shape[:2]
    u = np.clip(u, 0, w - 1.001)
    v = np.clip(v, 0, h - 1.001)
    u0 = np.floor(u).astype(np.int64)
    v0 = np.floor(v).astype(np.int64)
    u1 = np.clip(u0 + 1, 0, w - 1)
    v1 = np.clip(v0 + 1, 0, h - 1)
    du = (u - u0)[..., None].astype(np.float32)
    dv = (v - v0)[..., None].astype(np.float32)
    a = img[v0, u0]
    b = img[v0, u1]
    c = img[v1, u0]
    d = img[v1, u1]
    return a * (1 - du) * (1 - dv) + b * du * (1 - dv) + c * (1 - du) * dv + d * du * dv


# ---------------------------------------------------------------------------
# 指标 1：点图头 vs 深度反投影
# ---------------------------------------------------------------------------
def metric_pointmap_vs_depth(pred, conf_thres):
    wp = pred.get("world_points")
    wd = pred.get("world_points_from_depth")
    invalid = {
        "metric": "pointmap_vs_depth", "available": False,
        "reason": "predictions 里缺少 world_points 或 world_points_from_depth",
    }
    if wp is None or wd is None:
        return invalid

    s = min(wp.shape[0], wd.shape[0])
    h = min(wp.shape[1], wd.shape[1])
    w = min(wp.shape[2], wd.shape[2])
    wp = wp[:s, :h, :w]
    wd = wd[:s, :h, :w]

    conf, has_conf = get_conf(pred, "pointmap", s, (h, w))
    conf = conf[:s, :h, :w]
    valid = (
        np.isfinite(wp).all(axis=-1)
        & np.isfinite(wd).all(axis=-1)
        & (conf >= conf_thres)
    )
    n_valid = int(valid.sum())
    if n_valid < 16:
        return {
            "metric": "pointmap_vs_depth", "available": False,
            "reason": f"有效像素仅 {n_valid} 个，不足以统计（可调低 --conf-thres）",
        }

    diff = np.linalg.norm(wp - wd, axis=-1)[valid]
    scale = scene_scale(wp, conf, conf_thres)

    return {
        "metric": "pointmap_vs_depth",
        "available": True,
        "valid_pixels": n_valid,
        "valid_ratio": round(n_valid / float(s * h * w), 4),
        "mean_l2": round(float(diff.mean()), 6),
        "median_l2": round(float(np.median(diff)), 6),
        "p90_l2": round(float(np.percentile(diff, 90)), 6),
        "rel_mean_l2": round(float(diff.mean() / scale), 6),
        "rel_p90_l2": round(float(np.percentile(diff, 90) / scale), 6),
        "scene_scale": round(scale, 6),
        "used_confidence": has_conf,
        "conf_thres": conf_thres,
    }


# ---------------------------------------------------------------------------
# 指标 2：点图头 vs 相机头（把世界点投回自己的相机）
# ---------------------------------------------------------------------------
def metric_pointmap_vs_camera(pred, conf_thres):
    wp = pred.get("world_points")
    ext = pred.get("extrinsic")
    intr = pred.get("intrinsic")
    depth = pred.get("depth")
    if wp is None or ext is None or intr is None or depth is None:
        return {
            "metric": "pointmap_vs_camera", "available": False,
            "reason": "predictions 里缺少 world_points / extrinsic / intrinsic / depth 之一",
        }

    s = min(wp.shape[0], ext.shape[0], intr.shape[0], depth.shape[0])
    h = min(wp.shape[1], depth.shape[1])
    w = min(wp.shape[2], depth.shape[2])
    wp = wp[:s, :h, :w]
    depth = depth[:s, :h, :w]

    conf, has_conf = get_conf(pred, "pointmap", s, (h, w))
    conf = conf[:s, :h, :w]

    # 理想像素网格：主点在 (W/2, H/2)，故像素中心的连续坐标为 下标 + 0.5
    u_grid, v_grid = np.meshgrid(np.arange(w, dtype=np.float32) + 0.5,
                                 np.arange(h, dtype=np.float32) + 0.5)

    pix_err, z_rel, masks = [], [], []
    for i in range(s):
        R = ext[i][:3, :3]
        t = ext[i][:3, 3]
        K = intr[i]
        Xc = wp[i].reshape(-1, 3) @ R.T + t
        z = Xc[:, 2]
        fx, fy = K[0, 0], K[1, 1]
        cx, cy = K[0, 2], K[1, 2]
        u = fx * Xc[:, 0] / np.where(np.abs(z) < EPS, EPS, z) + cx
        v = fy * Xc[:, 1] / np.where(np.abs(z) < EPS, EPS, z) + cy

        d = depth[i].reshape(-1)
        m = (
            np.isfinite(Xc).all(axis=1)
            & np.isfinite(u) & np.isfinite(v)
            & (z > EPS) & (d > EPS)
            & (conf[i].reshape(-1) >= conf_thres)
        )
        if m.sum() == 0:
            continue
        du = u[m] - u_grid.reshape(-1)[m]
        dv = v[m] - v_grid.reshape(-1)[m]
        pix_err.append(np.sqrt(du * du + dv * dv))
        z_rel.append(np.abs(z[m] - d[m]) / np.maximum(d[m], EPS))
        masks.append(int(m.sum()))

    if not pix_err:
        return {
            "metric": "pointmap_vs_camera", "available": False,
            "reason": "没有任何帧存在有效像素（检查 extrinsic 方向约定或 conf_thres）",
        }

    pix_err = np.concatenate(pix_err)
    z_rel = np.concatenate(z_rel)
    n = int(pix_err.size)
    return {
        "metric": "pointmap_vs_camera",
        "available": True,
        "valid_pixels": n,
        "pix_err_mean": round(float(pix_err.mean()), 4),
        "pix_err_median": round(float(np.median(pix_err)), 4),
        "pix_err_p90": round(float(np.percentile(pix_err, 90)), 4),
        "pix_err_lt1px_ratio": round(float((pix_err < 1.0).mean()), 4),
        "pix_err_lt5px_ratio": round(float((pix_err < 5.0).mean()), 4),
        "z_rel_mean": round(float(z_rel.mean()), 6),
        "z_rel_median": round(float(np.median(z_rel)), 6),
        "used_confidence": has_conf,
        "conf_thres": conf_thres,
    }


# ---------------------------------------------------------------------------
# 指标 3：置信度分布
# ---------------------------------------------------------------------------
def metric_confidence(pred, conf_thres):
    num_frames = infer_num_frames(pred)
    hw = pred["depth"].shape[1:3] if pred.get("depth") is not None else pred["world_points"].shape[1:3]
    out = {"metric": "confidence", "available": False}

    for which, label in (("depth", "depth_conf"), ("pointmap", "world_points_conf")):
        conf, has_conf = get_conf(pred, which, num_frames, hw)
        if not has_conf:
            out[label] = {"available": False, "reason": "该字段不存在"}
            continue
        conf = conf[:num_frames, :hw[0], :hw[1]]
        finite = np.isfinite(conf)
        total = int(finite.sum())
        if total == 0:
            out[label] = {"available": False, "reason": "全部非有限值"}
            continue
        vals = conf[finite]
        low = float((vals < conf_thres).mean())
        out[label] = {
            "available": True,
            "mean": round(float(vals.mean()), 4),
            "median": round(float(np.median(vals)), 4),
            "p05": round(float(np.percentile(vals, 5)), 4),
            "p25": round(float(np.percentile(vals, 25)), 4),
            "max": round(float(vals.max()), 4),
            "low_ratio_lt_thres": round(low, 4),
        }
        out["available"] = True

    out["conf_thres"] = conf_thres
    return out


# ---------------------------------------------------------------------------
# 指标 4：多视图重投影光度一致性
# ---------------------------------------------------------------------------
def metric_photometric(pred, conf_thres, num_pairs, seed=42):
    wd = pred.get("world_points_from_depth")
    ext = pred.get("extrinsic")
    intr = pred.get("intrinsic")
    images = pred.get("images")
    depth = pred.get("depth")
    if wd is None or ext is None or intr is None or images is None or depth is None:
        return {
            "metric": "photometric", "available": False,
            "reason": "缺少 world_points_from_depth / extrinsic / intrinsic / images / depth 之一",
        }

    s = min(wd.shape[0], ext.shape[0], intr.shape[0], images.shape[0], depth.shape[0])
    h = min(wd.shape[1], images.shape[1], depth.shape[1])
    w = min(wd.shape[2], images.shape[2], depth.shape[2])
    wd = wd[:s, :h, :w]
    images = images[:s, :h, :w]
    depth = depth[:s, :h, :w]

    if s < 2:
        return {"metric": "photometric", "available": False,
                "reason": f"只有 {s} 帧，无法做多视图重投影（至少需要 2 帧）"}

    conf, has_conf = get_conf(pred, "depth", s, (h, w))
    conf = conf[:s, :h, :w]

    # 选帧对：优先相邻帧，帧数多时均匀抽样
    all_pairs = [(i, i + 1) for i in range(s - 1)]
    rng = np.random.default_rng(seed)
    if num_pairs is not None and len(all_pairs) > num_pairs:
        idx = np.linspace(0, len(all_pairs) - 1, num_pairs).astype(int)
        pairs = [all_pairs[i] for i in idx]
    else:
        pairs = all_pairs

    gray = images.mean(axis=-1)

    l1_list, ncc_list, ratio_list = [], [], []
    for i, j in pairs:
        z_i = depth[i]
        Pw = wd[i].reshape(-1, 3)
        valid = (
            np.isfinite(Pw).all(axis=1)
            & (z_i.reshape(-1) > EPS)
            & (conf[i].reshape(-1) >= conf_thres)
        )
        R = ext[j][:3, :3]
        t = ext[j][:3, 3]
        K = intr[j]
        with np.errstate(divide="ignore", invalid="ignore"):
            Xc = Pw @ R.T + t
            z = Xc[:, 2]
            u = K[0, 0] * Xc[:, 0] / np.where(np.abs(z) < EPS, EPS, z) + K[0, 2]
            v = K[1, 1] * Xc[:, 1] / np.where(np.abs(z) < EPS, EPS, z) + K[1, 2]
            inside = np.isfinite(z) & (z > EPS)
            inside &= np.isfinite(u) & np.isfinite(v)
            inside &= (u >= 0) & (u <= w - 1) & (v >= 0) & (v <= h - 1)
        valid = valid & inside

        n_proj = int(valid.sum())
        if n_proj < 16:
            continue
        ratio_list.append(n_proj / float(valid.size))

        # 越界像素置 0，采样后只取 valid 掩码内的结果，避免形状错乱
        u_full = np.where(valid, u, 0.0).reshape(h, w)
        v_full = np.where(valid, v, 0.0).reshape(h, w)
        sampled = bilinear_sample(images[j], u_full, v_full)
        mask2d = valid.reshape(h, w)

        src = images[i][mask2d]
        dst = sampled[mask2d]
        l1_list.append(float(np.abs(src - dst).mean()))

        gi = gray[i][mask2d]
        gj = sampled[mask2d].mean(axis=-1)
        gi_c = gi - gi.mean()
        gj_c = gj - gj.mean()
        denom = np.sqrt((gi_c ** 2).sum() * (gj_c ** 2).sum())
        ncc_list.append(float((gi_c * gj_c).sum() / denom) if denom > EPS else 0.0)

    if not l1_list:
        return {"metric": "photometric", "available": False,
                "reason": "所有帧对都没有足够多的有效投影点（可调低 --conf-thres）"}

    return {
        "metric": "photometric",
        "available": True,
        "frames": s,
        "pairs_evaluated": len(l1_list),
        "valid_proj_ratio_mean": round(float(np.mean(ratio_list)), 4),
        "photometric_l1_mean": round(float(np.mean(l1_list)), 6),
        "photometric_l1_median": round(float(np.median(l1_list)), 6),
        "photometric_l1_p90": round(float(np.percentile(l1_list, 90)), 6),
        "ncc_mean": round(float(np.mean(ncc_list)), 4),
        "ncc_min": round(float(np.min(ncc_list)), 4),
        "used_confidence": has_conf,
        "conf_thres": conf_thres,
    }


# ---------------------------------------------------------------------------
# 汇总与输出
# ---------------------------------------------------------------------------
def compute_all(npz_path, conf_thres, num_pairs):
    pred = load_predictions(npz_path)
    results = {
        "file": os.path.abspath(npz_path),
        "num_frames": infer_num_frames(pred),
        "metrics": [
            metric_pointmap_vs_depth(pred, conf_thres),
            metric_pointmap_vs_camera(pred, conf_thres),
            metric_confidence(pred, conf_thres),
            metric_photometric(pred, conf_thres, num_pairs),
        ],
    }
    return results


def print_report(res):
    print("=" * 72)
    print(f"文件: {res['file']}")
    print(f"帧数: {res['num_frames']}")
    print("-" * 72)
    for m in res["metrics"]:
        name = m.get("metric", "?")
        if not m.get("available"):
            print(f"[跳过] {name}: {m.get('reason', '不可用')}")
            continue
        print(f"[{name}]")
        for k, v in m.items():
            if k == "metric" or isinstance(v, dict):
                continue
            print(f"    {k:<26} {v}")
        for k, v in m.items():
            if isinstance(v, dict):
                if not v.get("available"):
                    print(f"    {k:<26} 不可用（{v.get('reason')}）")
                    continue
                print(f"    {k}:")
                for kk, vv in v.items():
                    if kk == "available":
                        continue
                    print(f"        {kk:<22} {vv}")
        print("-" * 72)


def main():
    ap = argparse.ArgumentParser(
        description="计算 VGGT 的无真值几何自洽性指标",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("npz", help="predictions.npz 路径，支持通配符（如 'vggt_output/**/*.npz'）")
    ap.add_argument("--conf-thres", type=float, default=3.0,
                    help="置信度过滤阈值，低于该值的像素不参与统计（默认 3.0）")
    ap.add_argument("--pairs", type=int, default=None,
                    help="光度一致性最多评估多少对相邻帧（默认全部）")
    ap.add_argument("--json", default=None, help="把结果同时写出为 JSON 文件")
    args = ap.parse_args()

    paths = sorted(glob.glob(args.npz)) or [args.npz]
    paths = [p for p in paths if os.path.isfile(p)]
    if not paths:
        print(f"找不到文件: {args.npz}", file=sys.stderr)
        return 1

    all_results = []
    for p in paths:
        try:
            res = compute_all(p, args.conf_thres, args.pairs)
        except Exception as e:
            print(f"[错误] {p}: {type(e).__name__}: {e}", file=sys.stderr)
            continue
        print_report(res)
        all_results.append(res)

    if not all_results:
        print("没有任何文件计算成功", file=sys.stderr)
        return 1

    if args.json:
        payload = all_results[0] if len(all_results) == 1 else all_results
        out_dir = os.path.dirname(os.path.abspath(args.json))
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"已写出 JSON: {os.path.abspath(args.json)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
