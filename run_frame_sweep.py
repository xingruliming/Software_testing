#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""帧数扫描实验：同一场景，输入 N = 1/2/4/8/16/32 张，看重建质量如何随视角数变化。

为什么不能简单"取前 N 张"
--------------------------
本数据集（DX.GL / Objaverse 飞行器渲染集）的相机轨迹是**黄金角球面螺旋**：
方位角每帧步进 137.5078°，俯仰角从 −89° 单调扫到 +89°（相邻帧只差 0.91°）。
因此**文件顺序 ≠ 平滑轨迹**：
  - 「取前 16 连续帧」只覆盖 2/18 个 10° 俯仰层（实测），视角多样性被摧毁；
  - 「每隔 N 帧取一帧」会反复取到相近俯仰，同样退化。
本脚本因此采用**分层抽样**，并且做成**嵌套**的：

  1. 按俯仰把 196 帧分成 32 层；
  2. 层序按「到赤道（俯仰 0°）的距离」由近到远排列 —— 先用最有信息量的水平视角；
  3. 层内用贪心挑方位角、优先填补尚未覆盖的 10° 方位扇区（同分时取该层方位角中位帧）；
  4. 得到一条全局帧序 order[]，第 N 次模拟取 order[:N]。

这样 1 ⊂ 2 ⊂ 4 ⊂ 8 ⊂ 16 ⊂ 32 **严格嵌套**，"多加了几张"就是唯一自变量，
且每次前缀都尽量铺开俯仰/方位覆盖。

真值配对（重要）
----------------
选中的帧是**散落**的索引，所以真值位姿必须按 `gt[sel]` 取，
**不能**取 `gt[:N]` —— 否则预测与真值错配，旋转误差会完全失真。
（本工程旧脚本 run_aircraft_batch.py 存在这一处错配，已另行修正。）

产物
----
    <out-root>/N01/ ... N32/
        depth/000000.png ...    伪彩深度图（由 run_vggt_inference.py 产出）
        glbscene_*.glb          两个预测分支的 GLB（同上）
        predictions.npz         完整预测
        run_info.json           推理元信息
        metrics_gt.json         本脚本追加：真值位姿 + G1/G3/G4
        summary.json            本脚本追加：精简汇总
    <out-root>/_sweep_summary.json / _sweep_summary.md

用法
----
    python run_frame_sweep.py --images-dir vggt_input/009_arbus \
        --transforms vggt_input/009_arbus/airbus_transforms.json \
        --out-root vggt_output/009_arbus_sweep \
        --frames 1 2 4 8 16 32
"""

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime

import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import run_aircraft_batch as rab  # noqa: E402  复用其指标函数，保持口径一致

DEFAULT_PYTHON = r"D:\anaconda3\envs\Pytorch_Vggt\python.exe"


def log(msg, fh=None):
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    if fh is not None:
        fh.write(line + "\n")
        fh.flush()


# --------------------------------------------------------------------------
# 真值
# --------------------------------------------------------------------------
def load_gt_path(json_path):
    """读任意路径的 transforms.json（airbus_transforms.json 等）。

    transform_matrix 是 camera-to-world（OpenGL）；转 OpenCV 的 world-to-camera：
        c2w_ocv = T @ diag(1, -1, -1, 1);  w2c = inv(c2w_ocv)
    只翻 y/z 两轴，翻 x 会变成镜像（det = −1）。
    """
    with open(json_path, encoding="utf-8") as fh:
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


def spherical(centers):
    """由相机中心算俯仰/方位（相对所有中心的质心）。"""
    c = np.asarray(centers, dtype=np.float64)
    rel = c - c.mean(axis=0)
    r = np.linalg.norm(rel, axis=1)
    el = np.degrees(np.arcsin(np.clip(rel[:, 1] / np.maximum(r, 1e-12), -1, 1)))
    az = np.degrees(np.arctan2(rel[:, 2], rel[:, 0])) % 360.0
    return el, az, r


# --------------------------------------------------------------------------
# 嵌套分层抽样的全局帧序
# --------------------------------------------------------------------------
def build_global_order(centers, n_bands=32, sector_deg=10.0):
    """返回一条全局帧序（长度 = 帧数）。前 N 项即第 N 次模拟的输入。

    层序：按每层平均俯仰到赤道的距离升序（先水平视角）。
    层内：贪心优先填补未覆盖的方位扇区；同分取该层方位角中位帧。
    """
    el, az, _ = spherical(centers)
    n_total = len(el)
    sector = (az // sector_deg).astype(int)

    # 按俯仰排序后等分成 n_bands 层
    order_el = np.argsort(el)
    bounds = [int(round(b * n_total / n_bands)) for b in range(n_bands + 1)]
    bounds[-1] = n_total
    bands = [order_el[bounds[b]:bounds[b + 1]] for b in range(n_bands)]
    bands = [b for b in bands if len(b) > 0]

    # 层序：平均俯仰到赤道由近到远
    bands.sort(key=lambda b: abs(float(np.mean(el[b]))))

    used = {}
    seq = []
    for b in bands:
        s = sector[b]
        # 贪心：选该层中"扇区使用次数最少"的帧
        counts = np.array([used.get(int(v), 0) for v in s], dtype=float)
        cand = b[counts == counts.min()]
        # 同分取方位角最接近该层中位者
        m = float(np.median(az[b]))
        d = np.abs(((az[cand] - m + 180.0) % 360.0) - 180.0)
        pick = int(cand[int(np.argmin(d))])
        seq.append(pick)
        used[int(sector[pick])] = used.get(int(sector[pick]), 0) + 1

    # 兜底：把未被选中的帧按索引顺序追加（正常情况不会触发，n_bands 已覆盖全部）
    seen = set(seq)
    seq.extend(i for i in range(n_total) if i not in seen)
    return seq, el, az


def coverage(sel, el, az):
    """球面覆盖：俯仰 10° 层数、方位 10° 扇区数、俯仰跨度。"""
    e, a = el[sel], az[sel]
    return {
        "n": len(sel),
        "elev_min_deg": float(e.min()), "elev_max_deg": float(e.max()),
        "elev_bands_10deg": len(set((e // 10).astype(int))),
        "elev_bands_total": len(set((el // 10).astype(int))),
        "azim_sectors_10deg": len(set((a // 10).astype(int))),
        "azim_sectors_total": len(set((az // 10).astype(int))),
    }


# --------------------------------------------------------------------------
# 单档
# --------------------------------------------------------------------------
def stage_images(sel, all_images, stage_dir):
    """把选中的帧按「选帧顺序」复制成 000000.png…，并返回清单。

    注意：**不使用 shutil.rmtree** —— 批量删除会触发环境的删除保护钩子
    （SAFE_DELETE_BULK_CONFIRM_REQUIRED）而中断整个扫描。
    暂存目录由调用方保证是本次运行独有的空目录。
    """
    os.makedirs(stage_dir, exist_ok=True)
    manifest = []
    for k, idx in enumerate(sel):
        src = all_images[idx]
        dst = os.path.join(stage_dir, f"{k:06d}.png")
        shutil.copy2(src, dst)
        manifest.append({"order": k, "source_index": int(idx),
                         "source_file": os.path.basename(src)})
    return manifest


def run_inference(py, input_dir, output_dir, log_path):
    cmd = [py, os.path.join(SCRIPT_DIR, "run_vggt_inference.py"),
           "--input-dir", input_dir, "--output-dir", output_dir]
    t0 = time.time()
    with open(log_path, "w", encoding="utf-8", errors="replace") as fh:
        fh.write("CMD: " + " ".join(cmd) + "\n\n")
        fh.flush()
        p = subprocess.run(cmd, cwd=SCRIPT_DIR, stdout=fh,
                           stderr=subprocess.STDOUT)
    return p.returncode, round(time.time() - t0, 2)


def main():
    ap = argparse.ArgumentParser(description="帧数扫描：N 张输入 -> 质量变化")
    ap.add_argument("--images-dir", required=True, help="扁平图像目录（*.png）")
    ap.add_argument("--transforms", required=True, help="真值 transforms.json")
    ap.add_argument("--out-root", required=True, help="输出根目录")
    ap.add_argument("--stage-root", default=None,
                    help="临时输入目录根（默认 <out-root>/_staged_inputs）")
    ap.add_argument("--frames", nargs="*", type=int, default=[1, 2, 4, 8, 16, 32])
    ap.add_argument("--python", default=DEFAULT_PYTHON)
    ap.add_argument("--conf-thres", type=float, default=3.0,
                    help="自洽性指标用的置信度阈值（GLB 的百分位过滤另由推理脚本控制）")
    ap.add_argument("--dry-run", action="store_true", help="只做选帧，不跑推理")
    ap.add_argument("--reuse-npz", action="store_true",
                    help="若该档已有 predictions.npz 则跳过推理，只重算指标（指标不需要 GPU）")
    args = ap.parse_args()

    images_dir = args.images_dir if os.path.isabs(args.images_dir) \
        else os.path.join(SCRIPT_DIR, args.images_dir)
    transforms = args.transforms if os.path.isabs(args.transforms) \
        else os.path.join(SCRIPT_DIR, args.transforms)
    out_root = args.out_root if os.path.isabs(args.out_root) \
        else os.path.join(SCRIPT_DIR, args.out_root)
    stage_root = args.stage_root or os.path.join(out_root, "_staged_inputs")
    # 每次运行用独立子目录，避免任何删除操作（删除会触发环境的批量删除保护）
    run_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    stage_root = os.path.join(stage_root, run_stamp)
    os.makedirs(out_root, exist_ok=True)
    os.makedirs(stage_root, exist_ok=True)

    all_images = sorted(glob.glob(os.path.join(images_dir, "*.png")))
    if not all_images:
        raise SystemExit(f"[错误] {images_dir} 下没有 png")

    gt_w2c, gt_centers, angle_x = load_gt_path(transforms)
    if len(gt_w2c) != len(all_images):
        print(f"[警告] 真值帧数 {len(gt_w2c)} != 图像数 {len(all_images)}，"
              f"按较小者对齐；请确认命名顺序一致")

    order, el, az = build_global_order(gt_centers)

    print("=" * 78)
    print("帧数扫描实验")
    print(f"  图像目录 : {images_dir}  （{len(all_images)} 帧）")
    print(f"  真值     : {transforms}")
    print(f"  输出     : {out_root}")
    print(f"  扫描帧数 : {args.frames}")
    print("=" * 78)

    results = []
    for n in args.frames:
        n = int(n)
        if n > len(all_images):
            print(f"[跳过] N={n} 超过可用帧数 {len(all_images)}")
            continue
        sel = order[:n]
        cov = coverage(sel, el, az)
        tag = f"N{n:02d}"
        out_dir = os.path.join(out_root, tag)
        os.makedirs(out_dir, exist_ok=True)

        prev_npz = os.path.join(out_dir, "predictions.npz")
        reuse = args.reuse_npz and os.path.exists(prev_npz)
        manifest = [{"order": k, "source_index": int(i),
                     "source_file": os.path.basename(all_images[i])}
                    for k, i in enumerate(sel)]

        if reuse:
            print(f"\n[{tag}] 选中 {n} 帧  俯仰 {cov['elev_min_deg']:.1f}..{cov['elev_max_deg']:.1f}° "
                  f"({cov['elev_bands_10deg']}/{cov['elev_bands_total']} 层)  "
                  f"方位 {cov['azim_sectors_10deg']}/{cov['azim_sectors_total']} 扇区"
                  f"  -> 复用已有 npz，只重算指标")
        else:
            stage_dir = os.path.join(stage_root, tag)
            stage_images(sel, all_images, stage_dir)
            print(f"\n[{tag}] 选中 {n} 帧  俯仰 {cov['elev_min_deg']:.1f}..{cov['elev_max_deg']:.1f}° "
                  f"({cov['elev_bands_10deg']}/{cov['elev_bands_total']} 层)  "
                  f"方位 {cov['azim_sectors_10deg']}/{cov['azim_sectors_total']} 扇区")

        with open(os.path.join(out_dir, "selection.json"), "w", encoding="utf-8") as fh:
            json.dump({"tag": tag, "num_frames": n, "coverage": cov,
                       "frame_order_global_first_48": [int(i) for i in order[:48]],
                       "selected_indices": [int(i) for i in sel],
                       "manifest": manifest}, fh, ensure_ascii=False, indent=2)

        summary = {"tag": tag, "num_frames": n, "coverage": cov,
                   "out_dir": os.path.relpath(out_dir, SCRIPT_DIR)}

        if args.dry_run:
            summary["status"] = "dry-run"
            results.append(summary)
            continue

        if reuse:
            summary["inference_returncode"] = 0
            summary["inference_wall_seconds"] = None
            summary["reused_npz"] = True
        else:
            rc, wall = run_inference(args.python, stage_dir, out_dir,
                                     os.path.join(out_dir, "run.log"))
            summary["inference_returncode"] = rc
            summary["inference_wall_seconds"] = wall
        if summary["inference_returncode"] != 0:
            summary["status"] = "failed"
            print(f"[{tag}] 推理失败 rc={rc}，见 {os.path.join(out_dir, 'run.log')}")
            results.append(summary)
            continue

        npz = os.path.join(out_dir, "predictions.npz")
        try:
            sc = rab.geometric_consistency(npz, args.conf_thres)
            ph = rab.photometric_consistency(npz, conf_thres=args.conf_thres)

            with np.load(npz, allow_pickle=True) as z:
                pred = z["extrinsic"]
                pred_intr = z["intrinsic"]
            n_use = min(len(pred), len(sel))
            pred4 = np.zeros((n_use, 4, 4), dtype=np.float64)
            pred4[:, :3, :4] = pred[:n_use].astype(np.float64)
            pred4[:, 3, 3] = 1.0
            # 关键：真值按「选中的帧索引」配对，不能取前 n 个
            gt4 = np.array([gt_w2c[sel[k]] for k in range(n_use)], dtype=np.float64)

            rpm = rab.relative_pose_metrics(pred4, gt4)
            fo = rab.focal_error(pred_intr, angle_x)

            with open(os.path.join(out_dir, "run_info.json"), encoding="utf-8") as fh:
                ri = json.load(fh)
            inf = ri.get("inference", {}) or {}
            m = {"tag": tag, "num_frames": n, "coverage": cov,
                 "peak_gpu_memory_gb": inf.get("peak_gpu_memory_gb"),
                 "inference_seconds": inf.get("inference_seconds"),
                 "self_consistency": sc, "photometric": ph,
                 "ground_truth": {"relative_pose": rpm, "focal": fo}}
            with open(os.path.join(out_dir, "metrics_gt.json"), "w",
                      encoding="utf-8") as fh:
                json.dump(m, fh, ensure_ascii=False, indent=2)

            summary.update({
                "status": "ok",
                "peak_gpu_memory_gb": m["peak_gpu_memory_gb"],
                "inference_seconds": m["inference_seconds"],
                "G1_relative_pct": sc["G1"]["relative_pct"],
                "G1_mean_l2": sc["G1"]["mean_l2"],
                "G3_depth_conf_below_thres_pct": sc["G3"]["depth_conf"]["below_thres_pct"],
                "G3_depth_conf_mean": sc["G3"]["depth_conf"]["mean"],
                "G3_depth_conf_p50": sc["G3"]["depth_conf"]["p50"],
                "G4_NCC": ph.get("NCC_mean"),
                "G4_L1": ph.get("L1_mean"),
                "G4_valid_rate_pct": ph.get("valid_rate_pct_mean"),
                "GT_rot_mean_deg": (rpm.get("rotation_deg") or {}).get("mean"),
                "GT_rot_median_deg": (rpm.get("rotation_deg") or {}).get("median"),
                "GT_rot_p90_deg": (rpm.get("rotation_deg") or {}).get("p90"),
                "GT_trans_mean_pct": (rpm.get("translation_pct") or {}).get("mean"),
                "GT_AUC30": rpm.get("AUC30"),
                "GT_RRA5": rpm.get("RRA5"), "GT_RRA15": rpm.get("RRA15"),
                "GT_RTA5": rpm.get("RTA5"), "GT_RTA15": rpm.get("RTA15"),
                "GT_focal_rel_err_pct": fo["rel_err_mean_pct"],
                "pointcloud_diag": sc["pointcloud_scale"]["diag"],
                "num_pairs": rpm.get("num_pairs", 0),
            })
            g = summary["GT_rot_mean_deg"]
            print(f"[{tag}] 峰值 {summary['peak_gpu_memory_gb']}GB  "
                  f"GT旋转均值 {g if g is None else round(g,2)}°  "
                  f"AUC30 {summary['GT_AUC30']}  "
                  f"G1相对 {summary['G1_relative_pct']}%  NCC {summary['G4_NCC']}")
        except Exception as exc:                                # noqa: BLE001
            import traceback
            summary["status"] = "metrics_failed"
            summary["error"] = f"{type(exc).__name__}: {exc}"
            summary["traceback"] = traceback.format_exc()
            print(f"[{tag}] 指标计算失败: {summary['error']}")

        with open(os.path.join(out_dir, "summary.json"), "w", encoding="utf-8") as fh:
            json.dump(summary, fh, ensure_ascii=False, indent=2)
        results.append(summary)

    # 汇总时从磁盘读回所有 Nxx/summary.json，而不是只用本轮结果，
    # 这样分批跑（例如单独补跑 32 帧）也能得到完整表格。
    disk = []
    for d in sorted(glob.glob(os.path.join(out_root, "N*"))):
        p = os.path.join(d, "summary.json")
        if os.path.isfile(p):
            try:
                with open(p, encoding="utf-8") as fh:
                    disk.append(json.load(fh))
            except Exception:                                   # noqa: BLE001
                pass
    results = sorted(disk, key=lambda s: s.get("num_frames", 0)) or results

    agg = {"generated_at": datetime.now().isoformat(timespec="seconds"),
           "images_dir": images_dir, "transforms": transforms,
           "out_root": out_root, "frames": args.frames,
           "sampling": "nested-stratified (elevation bands, equator-outward, azimuth-diversified)",
           "results": results}
    with open(os.path.join(out_root, "_sweep_summary.json"), "w", encoding="utf-8") as fh:
        json.dump(agg, fh, ensure_ascii=False, indent=2)

    def f(v, d=2):
        return "—" if v is None else f"{v:.{d}f}"

    lines = ["# 帧数扫描汇总（009_arbus）", "",
             f"抽样：嵌套分层（俯仰 32 层、层序由赤道向外、层内方位角最大化分散）；"
             f"第 N 次输入 `order[:N]`，严格嵌套。", "",
             "| N | 俯仰层(10°) | 方位扇区(10°) | 峰值显存GB | GT旋转均值° | GT旋转中位° | RRA@5% | AUC@30 | GT平移均值% | RTA@15% | G1相对% | G3低置信% | G4 NCC | G4有效率% |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for s in results:
        if s.get("status") != "ok":
            lines.append(f"| {s['num_frames']} | {s['coverage']['elev_bands_10deg']}/{s['coverage']['elev_bands_total']} | "
                         f"{s['coverage']['azim_sectors_10deg']}/{s['coverage']['azim_sectors_total']} | "
                         f"— | — | — | — | — | — | — | — | — | — | — |")
            continue
        c = s["coverage"]
        lines.append(
            f"| {s['num_frames']} | {c['elev_bands_10deg']}/{c['elev_bands_total']} | "
            f"{c['azim_sectors_10deg']}/{c['azim_sectors_total']} | "
            f"{f(s['peak_gpu_memory_gb'])} | {f(s['GT_rot_mean_deg'])} | {f(s['GT_rot_median_deg'])} | "
            f"{f(s.get('GT_RRA5'),1)} | {f(s['GT_AUC30'],1)} | {f(s['GT_trans_mean_pct'])} | "
            f"{f(s.get('GT_RTA15'),1)} | {f(s['G1_relative_pct'],3)} | "
            f"{f(s['G3_depth_conf_below_thres_pct'],1)} | {f(s['G4_NCC'],4)} | "
            f"{f(s['G4_valid_rate_pct'],1)} |")
    md = "\n".join(lines) + "\n"
    with open(os.path.join(out_root, "_sweep_summary.md"), "w", encoding="utf-8") as fh:
        fh.write(md)

    print("\n" + "=" * 78)
    print(md)
    print(f"汇总: {os.path.join(out_root, '_sweep_summary.json')}")
    print(f"      {os.path.join(out_root, '_sweep_summary.md')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
