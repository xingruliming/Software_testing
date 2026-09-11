#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
VGGT 无界面（headless）推理脚本 —— 不启动 Gradio，直接产出深度图与 GLB。

复制自 vggt-main/demo_gradio_cn.py 的 run_model / save_depth_images / 产物命名逻辑，
去掉全部界面依赖，便于批量和自动化执行。

用法示例（PowerShell / bash 均可）：

    D:\anaconda3\envs\Pytorch_Vggt\python.exe run_vggt_inference.py \
        --input-dir  "vggt_input/001_watercup" \
        --output-dir "vggt_output/001_watercup"

产物目录结构：

    <output-dir>/
        images/                        输入图像副本（供 mask_sky 等复用）
        depth/                         逐帧伪彩色深度图 PNG（000000.png ...）
        predictions.npz                完整预测结果（depth / extrinsic / intrinsic / ...）
        glbscene_*.glb                 3D 场景（点云 + 相机），每个预测分支一个
        run_info.json                  本次运行的元信息（帧数、耗时、峰值显存等）
"""

import argparse
import gc
import glob
import json
import os
import shutil
import sys
import time
from datetime import datetime

# Windows 控制台默认码页可能无法输出部分字符，这里统一成 UTF-8，避免打印中文时崩溃
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import cv2
import numpy as np

import cv2_unicode  # 同目录下的中文路径兼容层

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))          # 仓库根目录
VGGT_DIR = os.path.join(SCRIPT_DIR, "vggt-main")                 # 被测软件基线与依赖所在目录

# vggt 包不在 vggt-main 内层的 python 包里，需要把该目录加入搜索路径
if VGGT_DIR not in sys.path:
    sys.path.insert(0, VGGT_DIR)

# 深度图配色与最大渲染帧数（与 demo_gradio_cn.py 保持一致）
DEPTH_COLORMAP = "INFERNO"
DEPTH_MAX_FRAMES = 64

# 中文预测模式 -> visual_util 能识别的英文规范值
PREDICTION_MODE_MAP = {
    "深度图与相机分支": "Depthmap and Camera Branch",
    "点云图分支": "Pointmap Branch",
    "Depthmap and Camera Branch": "Depthmap and Camera Branch",
    "Depthmap and Camera": "Depthmap and Camera Branch",
    "Pointmap Branch": "Pointmap Branch",
    "Pointmap Regression": "Pointmap Branch",
    "Predicted Pointmap": "Pointmap Branch",
}

IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp")


def normalize_prediction_mode(mode):
    """中文 / 别名预测模式统一映射为英文规范值。"""
    if not mode:
        return "Depthmap and Camera Branch"
    return PREDICTION_MODE_MAP.get(mode.strip(), mode.strip())


def resolve_path(path, base=SCRIPT_DIR):
    """相对路径按仓库根目录解析，绝对路径原样返回。"""
    return path if os.path.isabs(path) else os.path.normpath(os.path.join(base, path))


def collect_images(input_dir):
    """收集输入目录下的图像，按文件名排序（微信图片_时间戳 命名即等于拍摄顺序）。"""
    files = [
        f for f in glob.glob(os.path.join(input_dir, "*"))
        if os.path.isfile(f) and f.lower().endswith(IMAGE_SUFFIXES)
    ]
    return sorted(files)


def stage_images(image_paths, target_dir):
    """把输入图像复制到 target_dir/images/ 下，返回该目录。"""
    images_dir = os.path.join(target_dir, "images")
    os.makedirs(images_dir, exist_ok=True)
    for src in image_paths:
        shutil.copy2(src, os.path.join(images_dir, os.path.basename(src)))
    print(f"[准备] 已复制 {len(image_paths)} 张图像 -> {images_dir}")
    return images_dir


def run_model(target_dir, model, torch):
    """VGGT 单次前馈推理。逻辑与 demo_gradio_cn.py 的 run_model 一致。"""
    from vggt.utils.load_fn import load_and_preprocess_images
    from vggt.utils.pose_enc import pose_encoding_to_extri_intri
    from vggt.utils.geometry import unproject_depth_map_to_point_map

    call_start = time.time()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA 不可用，请检查 Pytorch_Vggt 环境中的 PyTorch 是否为 CUDA 版本。")

    model = model.to(device)
    model.eval()

    image_names = sorted(glob.glob(os.path.join(target_dir, "images", "*")))
    print(f"[推理] 找到 {len(image_names)} 张图像")
    if len(image_names) == 0:
        raise RuntimeError("未找到任何图像，请检查输入目录。")

    images = load_and_preprocess_images(image_names).to(device)
    print(f"[推理] 预处理后张量形状: {tuple(images.shape)}")

    dtype = torch.bfloat16 if torch.cuda.get_device_capability()[0] >= 8 else torch.float16
    print(f"[推理] autocast dtype = {dtype}")

    torch.cuda.reset_peak_memory_stats()
    infer_start = time.time()
    with torch.no_grad():
        with torch.amp.autocast("cuda", dtype=dtype):
            predictions = model(images)
    infer_seconds = time.time() - infer_start
    print(f"[推理] 前馈完成，耗时 {infer_seconds:.2f} s")

    extrinsic, intrinsic = pose_encoding_to_extri_intri(predictions["pose_enc"], images.shape[-2:])
    predictions["extrinsic"] = extrinsic
    predictions["intrinsic"] = intrinsic

    for key in list(predictions.keys()):
        if isinstance(predictions[key], torch.Tensor):
            predictions[key] = predictions[key].cpu().numpy().squeeze(0)  # 去掉 batch 维
    predictions["pose_enc_list"] = None  # 与 demo 保持一致，不落盘

    print("[推理] 由深度图反投影计算世界坐标...")
    predictions["world_points_from_depth"] = unproject_depth_map_to_point_map(
        predictions["depth"], predictions["extrinsic"], predictions["intrinsic"]
    )

    peak_bytes = torch.cuda.max_memory_allocated()
    torch.cuda.empty_cache()

    stats = {
        "inference_seconds": round(infer_seconds, 3),
        "run_model_seconds": round(time.time() - call_start, 3),
        "peak_gpu_memory_gb": round(peak_bytes / (1024 ** 3), 3),
    }
    return predictions, stats


def save_depth_images(predictions, target_dir, max_frames=DEPTH_MAX_FRAMES):
    """逐帧渲染伪彩色深度图到 target_dir/depth/，每帧按 2%~98% 分位数归一化。

    写盘统一走 cv2_unicode.imwrite，规避 cv2.imwrite 在中文路径下静默失败的问题。
    """
    depth = predictions.get("depth")
    if depth is None:
        print("[深度图] predictions 中没有 depth，跳过")
        return []

    depth = np.asarray(depth, dtype=np.float32)
    if depth.ndim == 4:      # (S, H, W, 1) -> (S, H, W)
        depth = depth[..., 0]
    if depth.ndim == 2:      # 单帧补一维
        depth = depth[None]

    out_dir = os.path.join(target_dir, "depth")
    os.makedirs(out_dir, exist_ok=True)

    colormap = getattr(cv2, f"COLORMAP_{DEPTH_COLORMAP}", cv2.COLORMAP_INFERNO)
    saved = []
    for i in range(min(depth.shape[0], max_frames)):
        d = depth[i]
        lo, hi = np.nanpercentile(d, 2), np.nanpercentile(d, 98)
        if not (np.isfinite(lo) and np.isfinite(hi)) or hi - lo < 1e-6:
            lo, hi = np.nanmin(d), np.nanmax(d)
        if not (np.isfinite(lo) and np.isfinite(hi)) or hi - lo < 1e-6:
            lo, hi = 0.0, 1.0
        d_norm = np.nan_to_num((d - lo) / (hi - lo), nan=0.0, posinf=1.0, neginf=0.0)
        d_norm = np.clip(d_norm, 0.0, 1.0)

        color = cv2.applyColorMap((d_norm * 255).astype(np.uint8), colormap)
        out_path = os.path.join(out_dir, f"{i:06d}.png")
        if not cv2_unicode.imwrite(out_path, color):
            raise RuntimeError(f"深度图写盘失败: {out_path}")
        saved.append(out_path)

    print(f"[深度图] 已生成 {len(saved)} 张 -> {out_dir}")
    return saved


def build_glb_name(target_dir, conf_thres, frame_filter, mask_black_bg, mask_white_bg, show_cam, mask_sky, mode):
    """沿用 demo_gradio_cn.py 的 GLB 命名规则。"""
    frame_token = str(frame_filter).replace(".", "_").replace(":", "").replace(" ", "_")
    return os.path.join(
        target_dir,
        f"glbscene_{conf_thres}_{frame_token}"
        f"_maskb{mask_black_bg}_maskw{mask_white_bg}_cam{show_cam}_sky{mask_sky}"
        f"_pred{mode.replace(' ', '_')}.glb",
    )


def load_previous_inference_info(output_dir):
    """
    读取既有 run_info.json 中的推理统计块。

    --from-npz 模式下，npz 是**上一轮真实推理**的产物，本轮并没有跑推理；
    因此耗时、峰值显存这些统计必须从上一轮的记录里继承，否则会被本轮的
    0 值覆盖，让产物记录失真。
    """
    path = os.path.join(output_dir, "run_info.json")
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            previous = json.load(fh)
    except (OSError, ValueError) as exc:
        print(f"[警告] 无法读取既有 run_info.json（{exc}），推理统计将为空")
        return {}
    return previous.get("inference") or {}


def main():
    parser = argparse.ArgumentParser(description="VGGT 无界面推理：输入图像目录 -> 深度图 + GLB")
    parser.add_argument("--input-dir", default="vggt_input/001_watercup",
                        help="输入图像目录（相对路径以仓库根目录为基准）")
    parser.add_argument("--output-dir", default=None,
                        help="输出目录，默认 vggt_output/<输入目录名>")
    parser.add_argument("--model", default=os.path.join(os.path.dirname(SCRIPT_DIR), "model.pt"),
                        help="VGGT 权重文件路径（默认上级目录的 model.pt）")
    parser.add_argument("--conf-thres", type=float, default=50.0,
                        help="GLB 点云置信度过滤百分比，与界面默认值一致（默认 50.0）")
    parser.add_argument("--prediction-modes", default="深度图与相机分支,点云图分支",
                        help="要导出 GLB 的预测分支，逗号分隔；留空则只跑推理不出 GLB")
    parser.add_argument("--frame-filter", default="All", help="只显示指定帧的点，默认 All")
    parser.add_argument("--show-cam", action="store_true", default=True, help="GLB 中显示相机（默认开启）")
    parser.add_argument("--no-show-cam", dest="show_cam", action="store_false", help="GLB 中不显示相机")
    parser.add_argument("--mask-black-bg", action="store_true", default=False, help="过滤黑色背景")
    parser.add_argument("--mask-white-bg", action="store_true", default=False, help="过滤白色背景")
    parser.add_argument("--mask-sky", action="store_true", default=False, help="过滤天空（需要 skyseg.onnx）")
    parser.add_argument("--keep-images", action="store_true", default=True, help="在输出目录保留输入图像副本（默认开启）")
    parser.add_argument("--from-npz", action="store_true", default=False,
                        help="复用输出目录中已有的 predictions.npz，跳过推理，只重出深度图 / GLB")
    args = parser.parse_args()

    input_dir = resolve_path(args.input_dir)
    output_dir = resolve_path(args.output_dir) if args.output_dir else \
        os.path.join(SCRIPT_DIR, "vggt_output", os.path.basename(os.path.normpath(input_dir)))
    model_path = resolve_path(args.model)

    print("=" * 72)
    print("VGGT 无界面推理")
    print(f"  输入目录 : {input_dir}")
    print(f"  输出目录 : {output_dir}")
    print(f"  权重文件 : {model_path}")
    print("=" * 72)

    if not os.path.isdir(input_dir):
        raise SystemExit(f"[错误] 输入目录不存在: {input_dir}")
    if not args.from_npz and not os.path.isfile(model_path):
        raise SystemExit(f"[错误] 权重文件不存在: {model_path}")

    image_paths = collect_images(input_dir)
    if not image_paths:
        raise SystemExit(f"[错误] 输入目录中没有图像: {input_dir}")
    print(f"[准备] 待处理图像 {len(image_paths)} 张:")
    for p in image_paths:
        print(f"        - {os.path.basename(p)}")

    os.makedirs(output_dir, exist_ok=True)
    if args.keep_images:
        stage_images(image_paths, output_dir)

    import torch
    from visual_util import predictions_to_glb

    # skyseg.onnx 用相对路径读取，切到 vggt-main 目录更稳妥
    os.chdir(VGGT_DIR)

    npz_path = os.path.join(output_dir, "predictions.npz")
    run_start = time.time()

    if args.from_npz:
        # 复用已有预测结果，只重新生成深度图 / GLB（调参时无需再跑一遍推理）
        if not os.path.isfile(npz_path):
            raise SystemExit(f"[错误] 未找到可复用的预测结果: {npz_path}")
        print(f"[复用] 从已有预测结果加载: {npz_path}")
        with np.load(npz_path, allow_pickle=True) as data:
            predictions = {k: data[k] for k in data.files if k != "pose_enc_list"}
        device = "cuda" if torch.cuda.is_available() else "cpu"
        # 继承上一轮真实推理的统计，避免被本轮的 0 覆盖
        stats = load_previous_inference_info(output_dir)
        if not stats:
            print("[提示] 未找到上一轮 run_info.json，本轮将不记录推理耗时 / 显存")
    else:
        from vggt.models.vggt import VGGT

        print(f"[模型] 加载 VGGT 权重: {model_path}")
        load_start = time.time()
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = VGGT()
        model.load_state_dict(torch.load(model_path, map_location=device))
        model.eval()
        model = model.to(device)
        model_load_seconds = time.time() - load_start
        print(f"[模型] 加载完成，耗时 {model_load_seconds:.2f} s，设备={device}")

        predictions, stats = run_model(output_dir, model, torch)

        # ---- 落盘原始预测 ----
        np.savez(npz_path, **predictions)
        print(f"[保存] 预测结果 -> {npz_path}")

    # ---- 深度图 ----
    depth_files = save_depth_images(predictions, output_dir)

    # ---- GLB ----
    glb_files = []
    modes = [m for m in (args.prediction_modes or "").split(",") if m.strip()]
    for raw_mode in modes:
        mode = normalize_prediction_mode(raw_mode)
        glb_path = build_glb_name(output_dir, args.conf_thres, args.frame_filter,
                                  args.mask_black_bg, args.mask_white_bg,
                                  args.show_cam, args.mask_sky, mode)
        print(f"[GLB] 导出分支 {mode} ...")
        glb_start = time.time()
        scene = predictions_to_glb(
            predictions,
            conf_thres=args.conf_thres,
            filter_by_frames=args.frame_filter,
            mask_black_bg=args.mask_black_bg,
            mask_white_bg=args.mask_white_bg,
            show_cam=args.show_cam,
            mask_sky=args.mask_sky,
            target_dir=output_dir,
            prediction_mode=mode,
        )
        scene.export(file_obj=glb_path)
        size_mb = os.path.getsize(glb_path) / (1024 ** 2)
        print(f"[GLB] 完成 {os.path.basename(glb_path)} ({size_mb:.1f} MB, {time.time() - glb_start:.1f} s)")
        glb_files.append(glb_path)

    # ---- 运行元信息 ----
    total_seconds = time.time() - run_start
    now = datetime.now().isoformat(timespec="seconds")
    if args.from_npz:
        inference_block = stats or {"note": "本轮未跑推理，且未找到上一轮统计"}
        mode = "regenerate_from_npz"
    else:
        inference_block = {
            "num_images": len(image_paths),
            "image_shape": list(np.asarray(predictions["images"]).shape),
            "depth_shape": list(np.asarray(predictions["depth"]).shape),
            "device": device,
            "model_load_seconds": round(model_load_seconds, 3),
            "recorded_at": now,
            **stats,
        }
        mode = "inference"

    run_info = {
        "input_dir": input_dir,
        "output_dir": output_dir,
        "model_path": model_path,
        "num_images": len(image_paths),
        "image_names": [os.path.basename(p) for p in image_paths],
        "inference": inference_block,
        "this_run": {
            "mode": mode,
            "seconds": round(total_seconds, 3),
            "recorded_at": now,
        },
        "glb_settings": {
            "conf_thres": args.conf_thres,
            "prediction_modes": [normalize_prediction_mode(m) for m in modes],
            "show_cam": args.show_cam,
            "mask_sky": args.mask_sky,
            "mask_black_bg": args.mask_black_bg,
            "mask_white_bg": args.mask_white_bg,
        },
        "depth_images": [os.path.relpath(p, output_dir) for p in depth_files],
        "glb_files": [os.path.relpath(p, output_dir) for p in glb_files],
        "predictions_npz": os.path.relpath(npz_path, output_dir),
    }
    info_path = os.path.join(output_dir, "run_info.json")
    with open(info_path, "w", encoding="utf-8") as f:
        json.dump(run_info, f, ensure_ascii=False, indent=2)
    print(f"[保存] 运行元信息 -> {info_path}")

    print("=" * 72)
    print(f"全部完成，总耗时 {total_seconds:.1f} s")
    print(f"  深度图 {len(depth_files)} 张: {os.path.join(output_dir, 'depth')}")
    for g in glb_files:
        print(f"  GLB      : {g}")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
