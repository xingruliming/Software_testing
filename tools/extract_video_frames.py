#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把视频抽帧成图像序列，供 VGGT 推理使用。

抽帧约定**刻意与 VGGT 官方 demo 保持一致**（见 vggt-main/demo_gradio.py 的
``handle_uploads``）：``frame_interval = int(fps * frames_per_second)``，
计数器从 1 开始自增，``count % frame_interval == 0`` 时取该帧。
默认 1 帧/秒，因此 24.27 s / 30 fps 的视频会抽出 24 帧（count = 30,60,...,720）。

与官方实现的唯一差别：写盘用 ``cv2.imencode`` + ``open(...,'wb')``，
而不是 ``cv2.imwrite`` —— 后者在含中文的路径下会**静默失败**（不报错、不写文件），
这是本项目已记录的一个缺陷（见 MODULE2 缺陷盘点）。这里主动规避。

用法：
    python tools/extract_video_frames.py <video> <out_dir> [--fps 1] [--max-frames N]

产物：
    <out_dir>/000000.png, 000001.png, ...  按时间顺序
    <out_dir>/extract_info.json            抽帧元信息（源视频参数 + 选取规则 + 帧列表）
"""
import argparse
import json
import os
import sys

import cv2
import numpy as np


def imwrite_unicode(path: str, img: np.ndarray) -> None:
    """Unicode 安全的图像写盘（规避 cv2.imwrite 在中文路径下静默失败）。"""
    ext = os.path.splitext(path)[1] or ".png"
    ok, buf = cv2.imencode(ext, img)
    if not ok:
        raise RuntimeError(f"cv2.imencode 失败: {path}")
    with open(path, "wb") as f:
        f.write(buf.tobytes())


def extract(video_path: str, out_dir: str, fps_per_second: float = 1.0,
            max_frames: int = 0) -> dict:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise SystemExit(f"无法打开视频: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # 与官方 demo 一致：frame_interval = int(fps * frames_per_second)
    frame_interval = max(1, int(fps * fps_per_second))

    os.makedirs(out_dir, exist_ok=True)
    saved, count, idx = [], 0, 0
    while True:
        gotit, frame = cap.read()
        if not gotit:
            break
        count += 1
        if count % frame_interval == 0:
            name = f"{idx:06d}.png"
            imwrite_unicode(os.path.join(out_dir, name), frame)
            saved.append({"index": idx, "source_frame_count": count,
                          "source_frame_0based": count - 1, "file": name})
            idx += 1
            if max_frames and idx >= max_frames:
                break
    cap.release()

    info = {
        "video": os.path.abspath(video_path),
        "video_name": os.path.basename(video_path),
        "fps": fps,
        "total_frames": total,
        "duration_seconds": round(total / fps, 3) if fps else None,
        "resolution": [width, height],
        "aspect_ratio": round(width / height, 4) if height else None,
        "frames_per_second_selected": fps_per_second,
        "frame_interval": frame_interval,
        "selection_rule": "count += 1; if count % frame_interval == 0: save (count starts at 1)",
        "num_saved": len(saved),
        "output_dir": os.path.abspath(out_dir),
        "frames": saved,
    }
    with open(os.path.join(out_dir, "extract_info.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)
    return info


def main() -> None:
    ap = argparse.ArgumentParser(description="视频抽帧（与 VGGT 官方 demo 约定一致）")
    ap.add_argument("video", help="输入视频路径")
    ap.add_argument("out_dir", help="输出图像目录")
    ap.add_argument("--fps", type=float, default=1.0, dest="fps_per_second",
                    help="每秒抽取帧数，默认 1.0（官方 demo 约定）")
    ap.add_argument("--max-frames", type=int, default=0,
                    help="最多抽取多少帧，0 表示不限制")
    args = ap.parse_args()

    info = extract(args.video, args.out_dir, args.fps_per_second, args.max_frames)
    print(f"[视频] {info['video_name']}  {info['resolution'][0]}x{info['resolution'][1]}  "
          f"{info['fps']:.2f} fps  {info['total_frames']} 帧  "
          f"时长 {info['duration_seconds']} s")
    print(f"[抽帧] 每 {info['frame_interval']} 帧取 1（{info['frames_per_second_selected']} 帧/秒）"
          f" -> 共 {info['num_saved']} 张")
    print(f"[输出] {info['output_dir']}")
    print(f"[元信息] {os.path.join(info['output_dir'], 'extract_info.json')}")


if __name__ == "__main__":
    main()
