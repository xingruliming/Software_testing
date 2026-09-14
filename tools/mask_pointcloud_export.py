#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""按目标掩码剔除背景点，导出"只剩目标物体"的 GLB（VGGT 预测后处理）。

背景问题的成因
--------------
VGGT 对每一帧**每个像素**都回归出一个世界坐标，它不区分"这是物体"还是"这是背景"。
本数据集背景是纯白（占比 91~96%），所以点云里绝大多数点其实是背景平面
（渲染背景没有纹理，模型只能给出一个大致齐平的平面），视觉上就是一片白。

三种解法（本脚本实现前两种）
--------------------------
1. `--mode gt`    用数据集自带的 **GT 掩码**（`masks/frame_XXXXX.png`）逐像素过滤。**最精确**。
2. `--mode white` 按颜色剔白底（等价于 `visual_util` 的 `mask_white_bg`，RGB 全 >240 判为白）。
   零依赖，但抗锯齿边缘会残留一圈浅色点。
3. `--mode both`  两者取交集。

关键实现细节（踩过的坑）
----------------------
- **掩码 PNG 是 RGBA，但掩码存在 RGB 三个通道里（5 级灰度 + 抗锯齿边），alpha 恒为 255。**
  取 `getchannel('A')` 会得到全 255 的"全前景"，必须取 R/G/B。
- 掩码图按 `transforms.json` 的帧序编号 `frame_00000.png`…；扁平化后的输入图是
  `airbus_frame_00000.png`…，**索引一一对应**。选帧是散落的，所以要用
  `selection.json` 的 `selected_indices` 把「预测第 k 帧」映射回「源帧索引」。
- 过滤方式：把掩码外的 `world_points_conf` / `depth_conf` **置 0**，再用
  `conf_thres=0.0` 调 `predictions_to_glb`。该函数对 `conf_thres == 0.0` 有专门分支，
  且 `conf > 1e-5` 这一条会把置 0 的背景点全部排除 —— 于是掩码成为唯一过滤器。
- 掩码边缘是抗锯齿的，`>127` 会带上与白底混合的半透明像素，表现为物体轮廓外一圈
  浅色飘点。`--erode-px 1` 腐蚀一圈即可干净去掉（518 宽下 1 px 仅占 0.2%）。

用法
----
    python tools/mask_pointcloud_export.py \
        --npz vggt_output/009_arbus_sweep/N32/predictions.npz \
        --masks-dir "E:/0_work/suanfa/vggt/download/extracted/airbus_multiview/masks" \
        --selection vggt_output/009_arbus_sweep/N32/selection.json \
        --out-dir vggt_output/009_arbus_sweep/N32/aircraft_only \
        --mode gt --erode-px 1
"""
import argparse
import json
import os
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VGGT_DIR = os.path.join(ROOT, "vggt-main")
for p in (ROOT, VGGT_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

import cv2  # noqa: E402
import cv2_unicode  # noqa: E402


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def load_matte(path):
    """读掩码 PNG，返回 uint8 的 0/255 二值前景图（1024×1024）。

    掩码文件是 RGBA，但有效信息在 RGB 三通道（灰度 5 级 + 抗锯齿），alpha 恒 255。
    """
    img = cv2.imdecode(np.fromfile(path, np.uint8), cv2.IMREAD_UNCHANGED)
    if img is None:
        raise RuntimeError(f"掩码读取失败: {path}")
    if img.ndim == 3:
        r = img[..., 0]
        # 若 R 通道是常量 255 而 alpha 有变化，才说明掩码在 alpha；否则掩码就在 RGB
        if (img.shape[2] == 4 and int(r.min()) == 255 and int(r.max()) == 255
                and int(img[..., 3].min()) != int(img[..., 3].max())):
            ch = img[..., 3]
        else:
            ch = r
    else:
        ch = img
    return ch


def build_keep_mask(npz_path, masks_dir, selection, mode, erode_px, white_thr=240):
    """返回 (keep: (S,H,W) bool, 统计信息)。"""
    with np.load(npz_path, allow_pickle=True) as z:
        wp = z["world_points"]
        imgs = z["images"]
    S, H, W, _ = wp.shape

    idx = None
    if selection and os.path.exists(selection):
        with open(selection, encoding="utf-8") as fh:
            idx = json.load(fh)["selected_indices"]
        if len(idx) != S:
            log(f"[警告] selection 有 {len(idx)} 帧，预测有 {S} 帧，按较小者对齐")
            idx = idx[:S]

    keep = np.ones((S, H, W), dtype=bool)
    n_gt_removed = n_white_removed = 0

    if mode in ("gt", "both"):
        if not masks_dir:
            raise SystemExit("--mode gt/both 需要 --masks-dir")
        if idx is None:
            raise SystemExit("--mode gt/both 需要 --selection（预测帧序与源帧索引不同）")
        files = sorted(f for f in os.listdir(masks_dir) if f.lower().endswith(".png"))
        for k in range(S):
            src = os.path.join(masks_dir, files[idx[k]])
            m = load_matte(src)
            m = cv2.resize(m, (W, H), interpolation=cv2.INTER_LINEAR)
            if erode_px > 0:
                ker = np.ones((2 * erode_px + 1, 2 * erode_px + 1), np.uint8)
                m = cv2.erode(m, ker, iterations=1)
            fg = m > 127
            n_gt_removed += int((~fg).sum())
            # 必须逐帧写：写成 keep &= fg 会把 (H,W) 广播到所有帧，变成跨帧取交集
            keep[k] &= fg

    if mode in ("white", "both"):
        rgb = imgs.transpose(0, 2, 3, 1)
        if rgb.max() <= 1.5:
            rgb = rgb * 255.0
        white = ((rgb[..., 0] > white_thr) & (rgb[..., 1] > white_thr)
                 & (rgb[..., 2] > white_thr))
        n_white_removed += int(white.sum())
        keep &= ~white

    info = {
        "seed_frames": S, "height": H, "width": W, "mode": mode,
        "erode_px": erode_px,
        "total_pixels": int(S * H * W),
        "kept_pixels": int(keep.sum()),
        "kept_pct": round(float(keep.mean() * 100), 4),
        "removed_pixels": int((~keep).sum()),
        "gt_removed_pixels": n_gt_removed,
        "white_removed_pixels": n_white_removed,
    }
    return keep, info


def main():
    ap = argparse.ArgumentParser(description="按掩码剔除背景点，导出只剩目标物体的 GLB")
    ap.add_argument("--npz", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--masks-dir", default=None, help="GT 掩码目录（mode=gt/both 必填）")
    ap.add_argument("--selection", default=None, help="selection.json（含 selected_indices）")
    ap.add_argument("--mode", default="gt", choices=["gt", "white", "both"])
    ap.add_argument("--erode-px", type=int, default=1, help="掩码腐蚀像素数，去抗锯齿边缘，默认 1")
    ap.add_argument("--white-thr", type=int, default=240)
    ap.add_argument("--prediction-modes", default="点云图分支,深度图与相机分支")
    ap.add_argument("--conf-thres", type=float, default=0.0,
                    help="置 0 掩码外的置信度后用 0.0 让掩码成为唯一过滤器")
    ap.add_argument("--show-cam", action="store_true", default=True)
    ap.add_argument("--no-show-cam", dest="show_cam", action="store_false")
    ap.add_argument("--save-npz", action="store_true", default=False,
                    help="另存一份掩码后的 predictions.npz")
    args = ap.parse_args()

    npz = args.npz if os.path.isabs(args.npz) else os.path.join(ROOT, args.npz)
    out_dir = args.out_dir if os.path.isabs(args.out_dir) else os.path.join(ROOT, args.out_dir)
    sel = args.selection
    if sel and not os.path.isabs(sel):
        sel = os.path.join(ROOT, sel)
    os.makedirs(out_dir, exist_ok=True)

    log(f"读取 {npz}")
    keep, info = build_keep_mask(npz, args.masks_dir, sel, args.mode,
                                 args.erode_px, args.white_thr)
    log(f"掩码: 保留 {info['kept_pct']:.2f}% 像素 "
        f"({info['kept_pixels']} / {info['total_pixels']})，"
        f"剔除 {info['removed_pixels']} 个背景像素")

    with np.load(npz, allow_pickle=True) as z:
        preds = {k: z[k] for k in z.files if k != "pose_enc_list"}
    S, H, W, _ = preds["world_points"].shape

    # 关键：掩码外置信度置 0，配合 conf_thres=0.0 使掩码成为唯一过滤器
    before = {}
    for key in ("world_points_conf", "depth_conf"):
        if key not in preds:
            continue
        a = np.asarray(preds[key])
        before[key] = int((a > 1e-5).sum())
        a = a.astype(np.float32)
        if a.ndim == 4 and a.shape[-1] == 1:
            a = a[..., 0]
        a = a * keep.astype(np.float32)
        preds[key] = a
        log(f"  {key}: 有效点 {before[key]} -> {int((a > 1e-5).sum())}")

    preds["pose_enc_list"] = None

    from visual_util import predictions_to_glb
    from run_vggt_inference import normalize_prediction_mode

    glb_files = []
    modes = [m for m in (args.prediction_modes or "").split(",") if m.strip()]
    for raw in modes:
        mode = normalize_prediction_mode(raw)
        tag = mode.replace(" ", "_")
        name = f"aircraft_only_{args.mode}_erode{args.erode_px}_pred{tag}.glb"
        path = os.path.join(out_dir, name)
        log(f"导出 {mode} ...")
        scene = predictions_to_glb(
            preds, conf_thres=args.conf_thres, filter_by_frames="All",
            mask_black_bg=False, mask_white_bg=False, show_cam=args.show_cam,
            mask_sky=False, target_dir=out_dir, prediction_mode=mode)
        scene.export(file_obj=path)
        n_pts = 0
        for g in scene.geometry.values():
            if hasattr(g, "vertices"):
                n_pts = max(n_pts, len(g.vertices))
        log(f"  -> {os.path.basename(path)}  ({os.path.getsize(path)/2**20:.1f} MB, "
            f"点云 {n_pts} 点)")
        glb_files.append({"file": name, "points": int(n_pts),
                          "size_mb": round(os.path.getsize(path) / 2**20, 2)})

    if args.save_npz:
        p = os.path.join(out_dir, "predictions_aircraft_only.npz")
        np.savez(p, **preds)
        log(f"掩码后 npz -> {p} ({os.path.getsize(p)/2**20:.1f} MB)")

    info["glb_files"] = glb_files
    info["source_npz"] = npz
    with open(os.path.join(out_dir, "mask_info.json"), "w", encoding="utf-8") as fh:
        json.dump(info, fh, ensure_ascii=False, indent=2)
    log(f"完成 -> {out_dir}")


if __name__ == "__main__":
    main()
