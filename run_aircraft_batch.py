#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量运行 7 组飞行器多视角标定数据（Objaverse / DX.GL 渲染集，每组 196 视图）。

数据集关键事实（已实测确认，别再猜）
------------------------------------
1. `transforms.json` 里 `transform_matrix` 是 **camera-to-world**，
   旋转部分按 **OpenGL/Blender 约定**（x 右、y 上、z 向后）。
   实测验证：`R[:,2]` 与「相机→物体」方向的点积恒为 -1.000，
   即相机的 -z 轴正好指向物体，符合 look-at 约定。
   转成 VGGT/OpenCV（x 右、y 下、z 前）的 world→camera：
       c2w_ocv = T @ diag(1, -1, -1, 1)
       w2c     = inv(c2w_ocv)
   ⚠️ 只翻 y/z 两轴即可，**不要**额外翻 x（翻 x 会变成镜像、det=-1）。
2. **相机轨迹是黄金角（Fibonacci）球面螺旋**：
   方位角步进恒为 137.5078° = 360°×(1−1/φ)，俯仰角从 −89° 单调扫到 +89°。
   这意味着 **帧顺序 ≠ 平滑轨迹**，相邻帧在方位角上跳 137.5°。
   实测教训：按「每隔 8 帧取一帧」均匀抽样，会每次都取到相近的俯仰，
   导致视角多样性被摧毁 —— VGGT 输出退化成一小段弧
   （轨迹半径 0.97 vs 真值 4.06，相对旋转误差 118°）。
   因此本脚本提供 `--sampling stratified`（默认）：按俯仰分层、
   层内取方位角中位帧，使球面覆盖最大化。
3. 尺度是规范自由度（gauge freedom）：VGGT 的坐标系整体尺度与真值无关，
   所以精度只看**相对位姿**与 AUC，不要去比绝对尺度。

显存
----
RTX 3070 Laptop 只有 8 GB。实测：
- 24 帧 fp32/bf16 autocast -> 峰值 11.06 GB（**超出**，靠驱动共享内存才跑完）
- 因此默认 `--max-frames 16`，并且用 bf16 autocast（模型保持 fp32，
  因为 head 的 LayerNorm 不接受 bf16）。

产物
----
    <out>/<name>/
        predictions.npz         depth / depth_conf / world_points /
                                world_points_conf / extrinsic / intrinsic
        depth/000000.png ...    逐帧伪彩深度图
        metrics_gt.json         真值位姿指标 + 自洽性指标（G1/G3/G4）
        summary.json            精简汇总，便于集中统计
        run.log                 完整日志

用法
----
    D:\\anaconda3\\envs\\Pytorch_Vggt\\python.exe run_aircraft_batch.py \\
        --out-root output --max-frames 16
"""

import argparse
import glob
import json
import os
import sys
import time
import traceback
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VGGT_DIR = os.path.join(SCRIPT_DIR, "vggt-main")
if VGGT_DIR not in sys.path:
    sys.path.insert(0, VGGT_DIR)

DEFAULT_SRC = r"E:\0_work\suanfa\vggt\download\extracted"
DEFAULT_MODEL = r"E:\0_work\1shijian\model.pt"
DEPTH_COLORMAP = "INFERNO"
DEFAULT_DATASETS = ["airbus", "f51d_mustang_6_25", "il86",
                    "littlebird", "s39", "se210", "wessex"]


def log(msg, fh=None):
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    if fh is not None:
        fh.write(line + "\n")
        fh.flush()


# --------------------------------------------------------------------------
# 真值解析
# --------------------------------------------------------------------------
def load_gt(dataset_dir):
    """读 transforms.json，返回 (w2c 4x4 列表, 相机中心数组, camera_angle_x)。

    transform_matrix 是 camera-to-world（OpenGL），转 world-to-camera：
        c2w_ocv = T @ diag(1, -1, -1, 1)
        w2c     = inv(c2w_ocv)
    """
    with open(os.path.join(dataset_dir, "transforms.json"), encoding="utf-8") as fh:
        meta = json.load(fh)

    flip = np.diag([1.0, -1.0, -1.0, 1.0])
    w2c_list, centers = [], []
    for fr in meta["frames"]:
        T = np.array(fr["transform_matrix"], dtype=np.float64).reshape(4, 4)
        c2w = T @ flip
        R, t = c2w[:3, :3], c2w[:3, 3]
        M = np.eye(4)
        M[:3, :3] = R.T
        M[:3, 3] = -R.T @ t
        w2c_list.append(M)
        centers.append(t.copy())
    return w2c_list, np.array(centers), float(meta["camera_angle_x"])


def rotation_angle_deg(R):
    c = (np.trace(R) - 1.0) / 2.0
    return float(np.degrees(np.arccos(np.clip(c, -1.0, 1.0))))


def relative_pose_metrics(pred_w2c, gt_w2c):
    """相对位姿误差。相对量对整体坐标系/尺度选择不变，可直接跨模型比较。

    ⚠️ 必须用 **w2c** 矩阵构造相对位姿：T_{i→j} = W_j @ inv(W_i)。
    不能先用 inv() 转成 c2w 再比 —— c2w 形式的相对旋转是 R_c2w_j R_c2w_i^T，
    在「预测世界系与真值世界系相差一个全局旋转 G」时等于 G dR G^T，
    误差里会混进 G 的成分，数值严重虚高。
    实测（009_arbus，N=2/4/8/16）：
        c2w 写法 40.3 / 49.1 / 94.8 / 107.2°（受 G 污染）
        w2c 写法  0.44 / 0.59 / 0.41 /  0.38°（正确，与真值相对旋转角度吻合）
    ⚠️ 平移量必须先把预测缩放到真值尺度再比。
    尺度（整体缩放）是规范自由度：实测预测相机半径恒为真值的 0.245~0.258 倍。
    若直接用「真值尺度」去除「预测平移」，s 不会抵消，会凭空多出 (1-s)≈75% 的
    虚假误差。实测（009_arbus）：
        不做尺度对齐 74.2 / 90.7 / 81.9 / 73.0 / 70.4 %
        做完尺度对齐  1.11 /  2.79 /  1.47 /  0.89 /  1.85 %   (N=2/4/8/16/32)
    """
    n = len(pred_w2c)
    if n < 2:
        return {}
    ii, jj = np.triu_indices(n, k=1)

    # 尺度是规范自由度：预测与真值各自取相机中心成对距离中位数，
    # 用其比值把预测缩放到真值尺度后再比较。
    gt_centers = np.linalg.inv(gt_w2c)[:, :3, 3]
    pair_d = np.linalg.norm(gt_centers[ii] - gt_centers[jj], axis=1)
    scale_gt = float(np.median(pair_d)) if len(pair_d) else 1.0
    scale_gt = scale_gt if scale_gt > 1e-9 else 1.0

    pred_centers = np.linalg.inv(pred_w2c)[:, :3, 3]
    pair_dp = np.linalg.norm(pred_centers[ii] - pred_centers[jj], axis=1)
    scale_pred = float(np.median(pair_dp)) if len(pair_dp) else 1.0
    scale_pred = scale_pred if scale_pred > 1e-9 else 1.0
    s = scale_gt / scale_pred          # 把预测缩放到真值尺度

    rel_R, rel_t = [], []
    for i, j in zip(ii, jj):
        Tp = pred_w2c[j] @ np.linalg.inv(pred_w2c[i])   # i -> j，w2c 构造
        Tg = gt_w2c[j] @ np.linalg.inv(gt_w2c[i])
        dR_p, dt_p = Tp[:3, :3], Tp[:3, 3]
        dR_g, dt_g = Tg[:3, :3], Tg[:3, 3]
        rel_R.append(rotation_angle_deg(dR_p @ dR_g.T))
        rel_t.append(float(np.linalg.norm(s * dt_p - dt_g) / scale_gt * 100.0))

    rel_R, rel_t = np.array(rel_R), np.array(rel_t)

    def auc(err, thr):
        return float(np.mean(np.clip(1.0 - err / thr, 0.0, 1.0)) * 100.0)

    out = {
        "num_pairs": int(len(rel_R)),
        "scale_ratio_pred_over_gt": float(scale_pred / scale_gt),
        "rotation_deg": {
            "mean": float(rel_R.mean()), "median": float(np.median(rel_R)),
            "p90": float(np.percentile(rel_R, 90)), "max": float(rel_R.max()),
        },
        "translation_pct": {
            "mean": float(rel_t.mean()), "median": float(np.median(rel_t)),
            "p90": float(np.percentile(rel_t, 90)), "max": float(rel_t.max()),
        },
        "AUC30": auc(rel_R, 30.0),
    }
    for thr in (5, 15, 30):
        out[f"RRA{thr}"] = float(np.mean(rel_R < thr) * 100.0)
        out[f"RTA{thr}"] = float(np.mean(rel_t < thr) * 100.0)
    return out


def focal_error(pred_intr, gt_angle_x):
    """焦距相对误差。VGGT 输出像素单位焦距，真值只给水平 FOV。

    VGGT 对 518x518 方形输入给出 fx≈fy≈617~625px（真值 625.28），
    说明它把所有帧内参统一化 —— 内参本身自洽，误差很小。

    防御：调用方若误传 extrinsic(3x4) 会得到 shape (S,3,4)，
    `[:,0,0]` 变成取第 0 列平移量（≈0.7），误差会假性地显示 99.88%。
    因此这里显式校验最后一维必须是 3x3。
    """
    pred_intr = np.asarray(pred_intr)
    if pred_intr.ndim != 3 or pred_intr.shape[1:] != (3, 3):
        raise ValueError(
            f"focal_error 需要 (S,3,3) 的 intrinsic，收到 {pred_intr.shape}；"
            "很可能是误传了 extrinsic")
    W = 518
    fx = pred_intr[:, 0, 0]
    fx_gt = (W / 2.0) / np.tan(gt_angle_x / 2.0)
    rel = np.abs(fx - fx_gt) / fx_gt * 100.0
    return {
        "fx_gt_px": float(fx_gt),
        "fx_pred_mean_px": float(fx.mean()),
        "fx_pred_std_px": float(fx.std()),
        "rel_err_mean_pct": float(rel.mean()),
        "rel_err_median_pct": float(np.median(rel)),
        "rel_err_max_pct": float(rel.max()),
        "num_frames": int(len(fx)),
    }


# --------------------------------------------------------------------------
# 抽帧策略
# --------------------------------------------------------------------------
def select_frames(n_total, n_want, mode, centers=None):
    """返回要保留的帧索引（升序）。

    mode="stratified": 按俯仰角分层、层内取方位角中位帧，最大化球面覆盖。
                       这是黄金角螺旋数据集的正确抽样方式。
    mode="first":      取前 n_want 帧连续帧。
    mode="uniform":    等间隔抽（**不推荐**，会摧毁视角多样性，保留用于对照实验）。
    """
    if n_want <= 0 or n_want >= n_total:
        return list(range(n_total))

    if mode == "uniform" or centers is None:
        step = n_total / float(n_want)
        sel = sorted(set(min(int(round(k * step)), n_total - 1) for k in range(n_want)))
        return sel

    if mode == "first":
        return list(range(n_want))

    # stratified
    c = np.asarray(centers, dtype=np.float64)
    obj = c.mean(axis=0)
    rel = c - obj
    r = np.linalg.norm(rel, axis=1)
    el = np.degrees(np.arcsin(np.clip(rel[:, 1] / np.maximum(r, 1e-12), -1, 1)))
    az = np.degrees(np.arctan2(rel[:, 2], rel[:, 0])) % 360.0

    order = np.argsort(el)
    sel = []
    for k in range(n_want):
        lo = int(round(k * n_total / n_want))
        hi = int(round((k + 1) * n_total / n_want))
        grp = order[lo:hi]
        if len(grp) == 0:
            grp = order[lo:lo + 1]
        m = np.median(az[grp])
        pick = grp[np.argmin(np.abs(((az[grp] - m + 180.0) % 360.0) - 180.0))]
        sel.append(int(pick))
    return sorted(set(sel))


def coverage_report(sel, centers_all):
    c = np.asarray(centers_all, dtype=np.float64)
    obj = c.mean(axis=0)
    rel = c - obj
    r = np.linalg.norm(rel, axis=1)
    el = np.degrees(np.arcsin(np.clip(rel[:, 1] / np.maximum(r, 1e-12), -1, 1)))
    az = np.degrees(np.arctan2(rel[:, 2], rel[:, 0])) % 360.0
    e, a = el[sel], az[sel]
    return {
        "elev_min": float(e.min()), "elev_max": float(e.max()),
        "elev_bands_10deg": len(set((e // 10).astype(int))),
        "elev_bands_total": len(set((el // 10).astype(int))),
        "azim_sectors_10deg": len(set((a // 10).astype(int))),
        "azim_sectors_total": len(set((az // 10).astype(int))),
        "radius_median": float(np.median(r[sel])),
    }


# --------------------------------------------------------------------------
# 自洽性指标
# --------------------------------------------------------------------------
def geometric_consistency(npz_path, conf_thres):
    out = {}
    with np.load(npz_path, allow_pickle=True) as d:
        wp = d["world_points"].astype(np.float32)
        wpd = d["world_points_from_depth"].astype(np.float32)
        conf = d["world_points_conf"].astype(np.float32)
        dep = d["depth"].astype(np.float32)
        dconf = d["depth_conf"].astype(np.float32)

    m = conf > conf_thres
    if m.sum() == 0:
        m = np.ones_like(conf, dtype=bool)
    diff = np.linalg.norm((wp - wpd)[m], axis=-1)
    sel = wp[m]
    diag = float(np.linalg.norm(sel.max(axis=0) - sel.min(axis=0)))
    out["G1"] = {
        "mean_l2": float(diff.mean()),
        "median_l2": float(np.median(diff)),
        "relative_pct": float(diff.mean() / diag * 100.0) if diag > 1e-9 else None,
        "scene_diag": diag,
        "valid_pixels": int(m.sum()),
        "total_pixels": int(m.size),
    }
    out["G3"] = {
        "world_points_conf": {
            "mean": float(conf.mean()),
            "p05": float(np.percentile(conf, 5)),
            "p50": float(np.percentile(conf, 50)),
            "below_thres_pct": float((conf < conf_thres).mean() * 100.0),
        },
        "depth_conf": {
            "mean": float(dconf.mean()),
            "p05": float(np.percentile(dconf, 5)),
            "p50": float(np.percentile(dconf, 50)),
            "below_thres_pct": float((dconf < conf_thres).mean() * 100.0),
        },
    }
    dd = dep[..., 0] if dep.ndim == 4 else dep
    out["depth_stats"] = {
        "mean": float(np.nanmean(dd)), "median": float(np.nanmedian(dd)),
        "min": float(np.nanmin(dd)), "max": float(np.nanmax(dd)),
        "zeros_pct": float((dd <= 0).mean() * 100.0),
    }
    # 由深度+位姿反投影得到的点云尺度（与真值半径对比可看尺度退化）
    flat = wpd[m]
    out["pointcloud_scale"] = {
        "extent": [float(v) for v in (flat.max(axis=0) - flat.min(axis=0))],
        "diag": diag,
    }
    return out


def photometric_consistency(npz_path, pairs=12, conf_thres=3.0, stride=8):
    with np.load(npz_path, allow_pickle=True) as d:
        depth = d["depth"].astype(np.float32)
        ext = d["extrinsic"].astype(np.float32)
        intr = d["intrinsic"].astype(np.float32)
        imgs = d["images"].astype(np.float32)

    if depth.ndim == 4:
        depth = depth[..., 0]
    S, H, W = depth.shape
    if S < 2:
        return {"available": False, "note": "single frame"}

    import cv2
    rng = np.random.default_rng(0)
    idx = np.sort(rng.choice(S, size=min(pairs, S), replace=False))
    ys, xs = np.meshgrid(np.arange(0, H, stride), np.arange(0, W, stride),
                         indexing="ij")
    pix = np.stack([xs.ravel(), ys.ravel()], axis=-1).astype(np.float32)

    l1s, nccs, rates = [], [], []
    for i in idx:
        j = int((i + 1) % S)
        d_i = depth[i][ys.ravel(), xs.ravel()]
        valid = d_i > 1e-6
        if valid.sum() < 100:
            continue
        p, dv = pix[valid], d_i[valid]
        K = intr[i]
        xyz = np.stack([(p[:, 0] - K[0, 2]) / K[0, 0] * dv,
                        (p[:, 1] - K[1, 2]) / K[1, 1] * dv, dv], axis=-1)
        world = (xyz - ext[i][:3, 3]) @ ext[i][:3, :3]
        cam_j = world @ ext[j][:3, :3].T + ext[j][:3, 3]
        z = cam_j[:, 2]
        ok = z > 1e-6
        if ok.sum() < 50:
            continue
        K2 = intr[j]
        u = (cam_j[ok, 0] / z[ok]) * K2[0, 0] + K2[0, 2]
        v = (cam_j[ok, 1] / z[ok]) * K2[1, 1] + K2[1, 2]
        inb = (u >= 0) & (u <= W - 1) & (v >= 0) & (v <= H - 1)
        if inb.sum() < 50:
            continue
        u, v = u[inb], v[inb]
        srcp = p[ok][inb]
        gimg, simg = imgs[j].mean(axis=0), imgs[i].mean(axis=0)
        a = cv2.remap(gimg, u.astype(np.float32).reshape(1, -1),
                      v.astype(np.float32).reshape(1, -1), cv2.INTER_LINEAR).ravel()
        b = cv2.remap(simg, srcp[:, 0].astype(np.float32).reshape(1, -1),
                      srcp[:, 1].astype(np.float32).reshape(1, -1),
                      cv2.INTER_LINEAR).ravel()
        fin = np.isfinite(a) & np.isfinite(b)
        if fin.sum() < 50:
            continue
        a, b = a[fin], b[fin]
        rates.append(float(inb.sum() / len(p) * 100.0))
        l1s.append(float(np.mean(np.abs(a - b))))
        if a.std() > 1e-6 and b.std() > 1e-6:
            nccs.append(float(np.corrcoef(a, b)[0, 1]))

    if not l1s:
        return {"available": False, "note": "no valid pair"}
    return {
        "available": True,
        "num_pairs": len(l1s),
        "L1_mean": float(np.mean(l1s)),
        "NCC_mean": float(np.mean(nccs)) if nccs else None,
        "valid_rate_pct_mean": float(np.mean(rates)),
    }


# --------------------------------------------------------------------------
# 单组推理
# --------------------------------------------------------------------------
def run_one(name, src_root, out_root, model_path, sampling, max_frames,
            conf_thres, save_depth_png):
    src_dir = os.path.join(src_root, f"{name}_multiview")
    img_dir = os.path.join(src_dir, "images")
    out_dir = os.path.join(out_root, name)
    os.makedirs(out_dir, exist_ok=True)

    with open(os.path.join(out_dir, "run.log"), "w", encoding="utf-8") as fh:
        def L(m):
            log(m, fh)

        L("=" * 70)
        L(f"数据集 {name}")
        L(f"  源目录 : {src_dir}")
        L(f"  输出   : {out_dir}")
        L(f"  抽样   : {sampling}  上限 {max_frames} 帧")
        L("=" * 70)

        summary = {"dataset": name, "status": "unknown", "src_dir": src_dir,
                   "out_dir": out_dir, "sampling": sampling}
        t_all = time.time()

        try:
            if not os.path.isdir(img_dir):
                raise FileNotFoundError(f"缺少 images 目录: {img_dir}")

            import torch
            from vggt.models.vggt import VGGT
            from vggt.utils.load_fn import load_and_preprocess_images
            from vggt.utils.pose_enc import pose_encoding_to_extri_intri
            from vggt.utils.geometry import unproject_depth_map_to_point_map

            all_images = sorted(glob.glob(os.path.join(img_dir, "*")))
            L(f"[输入] 源目录共 {len(all_images)} 帧")

            gt_w2c, gt_centers, angle_x = load_gt(src_dir)

            sel = select_frames(len(all_images), max_frames, sampling, gt_centers)
            image_paths = [all_images[i] for i in sel]
            L(f"[抽样] {sampling} -> 保留 {len(sel)} 帧")
            cov = coverage_report(sel, gt_centers)
            L(f"  球面覆盖: 俯仰 {cov['elev_min']:.1f}..{cov['elev_max']:.1f}° "
              f"({cov['elev_bands_10deg']}/{cov['elev_bands_total']} 层)  "
              f"方位 {cov['azim_sectors_10deg']}/{cov['azim_sectors_total']} 扇区")
            summary["num_images"] = len(image_paths)
            summary["coverage"] = cov

            t0 = time.time()
            model = VGGT()
            sd = torch.load(model_path, map_location="cpu")
            if isinstance(sd, dict) and "model" in sd and len(sd) < 5:
                sd = sd["model"]
            model.load_state_dict(sd)
            del sd
            model.eval()
            # 模型保持 fp32：head 的 LayerNorm 不接受 bf16；
            # aggregator 在建图阶段靠 autocast 跑 bf16 省显存。
            model = model.to("cuda").to(torch.float32)
            L(f"[模型] 加载完成 {time.time() - t0:.1f}s (fp32 + autocast bf16)")

            images = load_and_preprocess_images(image_paths).to("cuda")
            L(f"[输入] 张量形状 {tuple(images.shape)}")

            torch.cuda.reset_peak_memory_stats()
            t1 = time.time()
            with torch.no_grad():
                with torch.amp.autocast("cuda", dtype=torch.bfloat16):
                    preds = model(images)
            torch.cuda.synchronize()
            infer_s = time.time() - t1
            peak_gb = torch.cuda.max_memory_allocated() / (1024 ** 3)
            L(f"[推理] 完成 {infer_s:.1f}s，峰值显存 {peak_gb:.2f} GB")

            extri, intr = pose_encoding_to_extri_intri(
                preds["pose_enc"], images.shape[-2:])

            arrays = {
                "depth": preds["depth"], "depth_conf": preds["depth_conf"],
                "world_points": preds["world_points"],
                "world_points_conf": preds["world_points_conf"],
                "pose_enc": preds["pose_enc"],
                "extrinsic": extri, "intrinsic": intr, "images": preds["images"],
            }
            for k in list(arrays):
                arrays[k] = arrays[k].squeeze(0).to(torch.float32).cpu().numpy()
            del preds, images
            torch.cuda.empty_cache()

            L("[反投影] 由深度图计算世界坐标 ...")
            arrays["world_points_from_depth"] = unproject_depth_map_to_point_map(
                arrays["depth"], arrays["extrinsic"], arrays["intrinsic"]
            ).astype(np.float32)

            npz_path = os.path.join(out_dir, "predictions.npz")
            np.savez(npz_path, **arrays)
            L(f"[保存] predictions.npz {os.path.getsize(npz_path)/2**20:.1f} MB")
            del arrays
            torch.cuda.empty_cache()

            if save_depth_png:
                import cv2
                import cv2_unicode
                with np.load(npz_path, allow_pickle=True) as z:
                    dep = z["depth"]
                if dep.ndim == 4:
                    dep = dep[..., 0]
                dep_dir = os.path.join(out_dir, "depth")
                os.makedirs(dep_dir, exist_ok=True)
                cmap = getattr(cv2, f"COLORMAP_{DEPTH_COLORMAP}", cv2.COLORMAP_INFERNO)
                for k in range(dep.shape[0]):
                    d = dep[k]
                    lo, hi = np.nanpercentile(d, 2), np.nanpercentile(d, 98)
                    if not (np.isfinite(lo) and np.isfinite(hi)) or hi - lo < 1e-6:
                        lo, hi = float(np.nanmin(d)), float(np.nanmax(d))
                    if not (np.isfinite(lo) and np.isfinite(hi)) or hi - lo < 1e-6:
                        lo, hi = 0.0, 1.0
                    dn = np.clip(np.nan_to_num((d - lo) / (hi - lo)), 0, 1)
                    col = cv2.applyColorMap((dn * 255).astype(np.uint8), cmap)
                    if not cv2_unicode.imwrite(os.path.join(dep_dir, f"{k:06d}.png"), col):
                        raise RuntimeError(f"深度图写盘失败 idx={k}")
                L(f"[深度图] {dep.shape[0]} 张 -> {dep_dir}")
                del dep

            L("[指标] 无真值自洽性 ...")
            sc = geometric_consistency(npz_path, conf_thres)
            ph = photometric_consistency(npz_path, conf_thres=conf_thres)

            L("[指标] 真值位姿 ...")
            with np.load(npz_path, allow_pickle=True) as z:
                pred = z["extrinsic"]
                pred_intr = z["intrinsic"]
            n_use = min(len(gt_w2c), len(image_paths))
            pred4 = np.zeros((n_use, 4, 4), dtype=np.float64)
            pred4[:, :3, :4] = pred[:n_use].astype(np.float64)
            pred4[:, 3, 3] = 1.0
            # 预测的第 k 帧对应源目录的 sel[k]，真值必须按同一个 sel 取。
            # 原来写的是 gt_w2c[:n_use]（取前 n 个），这只在 mode="first" 时才对；
            # stratified / uniform 选出的是散落索引，会与预测错配、使旋转误差失真。
            gt4 = np.array([gt_w2c[sel[k]] for k in range(n_use)], dtype=np.float64)
            rpm = relative_pose_metrics(pred4, gt4)
            # 注意：必须传 intrinsic，不要传 extrinsic
            fo = focal_error(pred_intr, angle_x)

            L(f"  GT 相对旋转 mean={rpm['rotation_deg']['mean']:.2f}° "
              f"中位={rpm['rotation_deg']['median']:.2f}° AUC@30={rpm['AUC30']:.1f}")
            L(f"  GT 相对平移 mean={rpm['translation_pct']['mean']:.2f}% "
              f"RTA@15={rpm['RTA15']:.1f}%")
            L(f"  GT 焦距 真值={fo['fx_gt_px']:.1f}px 预测={fo['fx_pred_mean_px']:.1f}px "
              f"误差={fo['rel_err_mean_pct']:.2f}%")
            L(f"  G1 相对={sc['G1']['relative_pct']:.3f}%  "
              f"G4 NCC={ph.get('NCC_mean')}")

            metrics = {
                "dataset": name, "num_images": len(image_paths),
                "sampling": sampling, "coverage": cov,
                "inference_seconds": round(infer_s, 2),
                "peak_gpu_memory_gb": round(peak_gb, 3),
                "self_consistency": sc, "photometric": ph,
                "ground_truth": {"relative_pose": rpm, "focal": fo},
            }
            with open(os.path.join(out_dir, "metrics_gt.json"), "w",
                      encoding="utf-8") as f:
                json.dump(metrics, f, ensure_ascii=False, indent=2)

            summary.update({
                "status": "ok",
                "inference_seconds": round(infer_s, 2),
                "peak_gpu_memory_gb": round(peak_gb, 3),
                "total_seconds": round(time.time() - t_all, 2),
                "G1_relative_pct": sc["G1"]["relative_pct"],
                "G3_below_thres_pct": sc["G3"]["world_points_conf"]["below_thres_pct"],
                "G4_NCC": ph.get("NCC_mean") if ph.get("available") else None,
                "G4_valid_rate_pct": ph.get("valid_rate_pct_mean") if ph.get("available") else None,
                "GT_rot_mean_deg": rpm["rotation_deg"]["mean"],
                "GT_rot_median_deg": rpm["rotation_deg"]["median"],
                "GT_trans_mean_pct": rpm["translation_pct"]["mean"],
                "GT_AUC30": rpm["AUC30"],
                "GT_RRA15": rpm["RRA15"], "GT_RTA15": rpm["RTA15"],
                "GT_focal_rel_err_pct": fo["rel_err_mean_pct"],
                "pointcloud_diag": sc["pointcloud_scale"]["diag"],
            })
            L(f"[完成] 总耗时 {time.time() - t_all:.1f}s")

        except Exception as exc:                                # noqa: BLE001
            summary["status"] = "failed"
            summary["error"] = f"{type(exc).__name__}: {exc}"
            summary["traceback"] = traceback.format_exc()
            L(f"[失败] {summary['error']}")
            L(summary["traceback"])

        with open(os.path.join(out_dir, "summary.json"), "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        try:
            import torch
            torch.cuda.empty_cache()
        except Exception:
            pass
        import gc
        gc.collect()
        return summary


def main():
    ap = argparse.ArgumentParser(description="批量跑飞行器多视角标定数据")
    ap.add_argument("--src-root", default=DEFAULT_SRC)
    ap.add_argument("--out-root", default=os.path.join(SCRIPT_DIR, "output"))
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--datasets", nargs="*", default=DEFAULT_DATASETS)
    ap.add_argument("--sampling", default="stratified",
                    choices=["stratified", "uniform", "first"])
    ap.add_argument("--max-frames", type=int, default=16,
                    help="每组保留帧数上限；0 = 全部 196 帧（8GB 显存会 OOM）")
    ap.add_argument("--conf-thres", type=float, default=3.0)
    ap.add_argument("--no-depth-png", dest="depth_png", action="store_false",
                    default=True)
    args = ap.parse_args()

    out_root = args.out_root if os.path.isabs(args.out_root) \
        else os.path.join(SCRIPT_DIR, args.out_root)
    os.makedirs(out_root, exist_ok=True)

    print("=" * 78)
    print("批量飞行器多视角标定数据 - VGGT 推理")
    print(f"  源目录 : {args.src_root}")
    print(f"  输出   : {out_root}")
    print(f"  权重   : {args.model}")
    print(f"  抽样   : {args.sampling}  上限 {args.max_frames} 帧")
    print(f"  数据集 : {args.datasets}")
    print("=" * 78)

    results = []
    for name in args.datasets:
        results.append(run_one(name, args.src_root, out_root, args.model,
                               args.sampling, args.max_frames,
                               args.conf_thres, args.depth_png))

    agg = {"generated_at": datetime.now().isoformat(timespec="seconds"),
           "src_root": args.src_root, "out_root": out_root,
           "sampling": args.sampling, "max_frames": args.max_frames,
           "results": results}
    with open(os.path.join(out_root, "_summary_all.json"), "w",
              encoding="utf-8") as f:
        json.dump(agg, f, ensure_ascii=False, indent=2)

    print("=" * 78)
    hdr = (f"{'数据集':<20}{'状态':<8}{'帧':>4}{'耗时s':>8}{'峰值GB':>8}"
           f"{'G1%':>7}{'GT旋转°':>9}{'AUC30':>7}{'焦距%':>7}")
    print(hdr)
    for s in results:
        print(f"{s['dataset']:<20}{s['status']:<8}{s.get('num_images',0):>4}"
              f"{s.get('inference_seconds',0):>8.1f}{s.get('peak_gpu_memory_gb',0):>8.2f}"
              f"{(s.get('G1_relative_pct') or 0):>7.3f}"
              f"{(s.get('GT_rot_median_deg') or 0):>9.2f}"
              f"{(s.get('GT_AUC30') or 0):>7.1f}"
              f"{(s.get('GT_focal_rel_err_pct') or 0):>7.2f}")
    print("=" * 78)
    print(f"汇总文件: {os.path.join(out_root, '_summary_all.json')}")
    return 0 if all(s["status"] == "ok" for s in results) else 1


if __name__ == "__main__":
    sys.exit(main())
