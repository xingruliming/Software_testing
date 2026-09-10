# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import os
import cv2
import torch
import numpy as np
import gradio as gr
import socket
import sys
import shutil
from datetime import datetime
import glob
import gc
import time

sys.path.append("vggt/")

from visual_util import predictions_to_glb
from vggt.models.vggt import VGGT
from vggt.utils.load_fn import load_and_preprocess_images
from vggt.utils.pose_enc import pose_encoding_to_extri_intri
from vggt.utils.geometry import unproject_depth_map_to_point_map


# -------------------------------------------------------------------------
# Windows 兼容：屏蔽 asyncio Proactor 的 ConnectionResetError 噪音
#   浏览器刷新/关闭页面时，keep-alive 连接被对端强制重置。asyncio 在
#   _ProactorBasePipeTransport._call_connection_lost 的 finally 里调用
#   sock.shutdown(SHUT_RDWR) 会抛 ConnectionResetError；由于该回调是经
#   loop.call_soon 调度的，asyncio 会把它当"未处理异常"打印出来：
#       Exception in callback _ProactorBasePipeTransport._call_connection_lost(None)
#       ConnectionResetError: [WinError 10054] 远程主机强迫关闭了一个现有的连接。
#   这是 CPython 已知问题(gh-93823)，不影响功能，但会反复刷屏。
#   下面把该场景的 ConnectionResetError 吃掉，并补完原本因异常被跳过的清理；
#   其他异常仍按原样抛出。
# -------------------------------------------------------------------------
def _patch_windows_asyncio_connection_reset():
    if sys.platform != "win32":
        return
    try:
        from asyncio import proactor_events

        _original = proactor_events._ProactorBasePipeTransport._call_connection_lost

        def _quiet_call_connection_lost(self, exc):
            try:
                return _original(self, exc)
            except ConnectionResetError:
                # 对端已强制断开。原方法在 finally 中抛错，导致后面的
                # close() / _called_connection_lost = True 都没跑到，这里补上。
                try:
                    if getattr(self, "_sock", None) is not None:
                        self._sock.close()
                except Exception:
                    pass
                self._sock = None
                server = getattr(self, "_server", None)
                if server is not None:
                    try:
                        server._detach()
                    except Exception:
                        pass
                    self._server = None
                self._called_connection_lost = True
                return None

        proactor_events._ProactorBasePipeTransport._call_connection_lost = _quiet_call_connection_lost
        print("[兼容] 已屏蔽 Windows asyncio 的 ConnectionResetError 噪音报错")
    except Exception as e:
        print(f"[兼容] 屏蔽 ConnectionResetError 未生效（不影响正常运行）: {e}")


_patch_windows_asyncio_connection_reset()

device = "cuda" if torch.cuda.is_available() else "cpu"

print("Initializing and loading VGGT model...")
# model = VGGT.from_pretrained("facebook/VGGT-1B")  # another way to load the model

model = VGGT()
model.load_state_dict(torch.load(r"E:\办公\研一\1软件实践\model.pt", map_location=device))
model.eval()
model = model.to(device)


# -------------------------------------------------------------------------
# 0) 产物备份配置
#     每次重建产生输出后，会把产物额外复制一份到 OUTPUT_BACKUP_DIR
# -------------------------------------------------------------------------
# 本脚本所在目录（即 vggt-main/）
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 产物备份根目录：默认是仓库上一级的 vggt_output/gradio/
# 想换地方，只改这一行即可
OUTPUT_BACKUP_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "vggt_output", "gradio"))

# 默认需要备份的产物（支持通配符）
BACKUP_FILE_PATTERNS = ["predictions.npz", "glbscene_*.glb"]

print(f"[备份] 重建产物将自动复制到: {OUTPUT_BACKUP_DIR}")


# -------------------------------------------------------------------------
# 预测模式映射
#   UI 的 Radio 用中文选项，但下游 visual_util.predictions_to_glb 是靠
#   `if "Pointmap" in prediction_mode` 来选分支的，中文直接传下去会
#   永远落到 Depthmap 分支（选"点云图分支"实际跑成深度图分支）。
#   所以传下去之前统一映射成英文规范值。
# -------------------------------------------------------------------------
PREDICTION_MODE_MAP = {
    "深度图与相机分支": "Depthmap and Camera Branch",
    "点云图分支": "Pointmap Branch",
    # 兼容英文/其他写法
    "Depthmap and Camera Branch": "Depthmap and Camera Branch",
    "Depthmap and Camera": "Depthmap and Camera Branch",
    "Pointmap Branch": "Pointmap Branch",
    "Pointmap Regression": "Pointmap Branch",
    "Predicted Pointmap": "Pointmap Branch",
}


def normalize_prediction_mode(prediction_mode):
    """把界面上的预测模式（中文）映射成 visual_util 能正确识别的英文规范值。"""
    if not prediction_mode:
        return "Depthmap and Camera Branch"
    return PREDICTION_MODE_MAP.get(prediction_mode, prediction_mode)


# -------------------------------------------------------------------------
# 启动参数
#   share=True 会去连 gradio.app 的中继服务器（frpc）生成公网分享链接，
#   国内网络通常连不通，会报:
#     login to server failed: connection write timeout
#     Could not create share link.
#   所以默认关闭 share，只用本地地址访问。
#   确实需要公网链接时，把 ENABLE_SHARE 改成 True（需能访问 gradio.app），
#   或改用 ngrok / cloudflared 之类的内网穿透工具。
# -------------------------------------------------------------------------
ENABLE_SHARE = False
SERVER_NAME = "127.0.0.1"  # 想让同一局域网的其他设备访问，改成 "0.0.0.0"
SERVER_PORT = 7860         # 端口被占用时会自动往后找空闲端口；填 None 表示完全交给 Gradio 自动选择


def is_port_free(port, host="127.0.0.1"):
    """
    检测端口是否空闲。

    注意：这里**故意不设** SO_REUSEADDR。Windows 上 SO_REUSEADDR 的语义和 Linux 不同，
    设了之后即使端口已被占用也能 bind 成功，会导致误判为"空闲"。
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False


# -------------------------------------------------------------------------
# 1) Core model inference
# -------------------------------------------------------------------------
def run_model(target_dir, model) -> dict:
    """
    Run the VGGT model on images in the 'target_dir/images' folder and return predictions.
    """
    print(f"Processing images from {target_dir}")

    # Device check
    device = "cuda" if torch.cuda.is_available() else "cpu"
    if not torch.cuda.is_available():
        raise ValueError("CUDA is not available. Check your environment.")

    # Move model to device
    model = model.to(device)
    model.eval()

    # Load and preprocess images
    image_names = glob.glob(os.path.join(target_dir, "images", "*"))
    image_names = sorted(image_names)
    print(f"Found {len(image_names)} images")
    if len(image_names) == 0:
        raise ValueError("No images found. Check your upload.")

    images = load_and_preprocess_images(image_names).to(device)
    print(f"Preprocessed images shape: {images.shape}")

    # Run inference
    print("Running inference...")
    dtype = torch.bfloat16 if torch.cuda.get_device_capability()[0] >= 8 else torch.float16

    with torch.no_grad():
        with torch.amp.autocast("cuda",dtype=dtype):
            predictions = model(images)

    # Convert pose encoding to extrinsic and intrinsic matrices
    print("Converting pose encoding to extrinsic and intrinsic matrices...")
    extrinsic, intrinsic = pose_encoding_to_extri_intri(predictions["pose_enc"], images.shape[-2:])
    predictions["extrinsic"] = extrinsic
    predictions["intrinsic"] = intrinsic

    # Convert tensors to numpy
    for key in predictions.keys():
        if isinstance(predictions[key], torch.Tensor):
            predictions[key] = predictions[key].cpu().numpy().squeeze(0)  # remove batch dimension
    predictions['pose_enc_list'] = None # remove pose_enc_list

    # Generate world points from depth map
    print("Computing world points from depth map...")
    depth_map = predictions["depth"]  # (S, H, W, 1)
    world_points = unproject_depth_map_to_point_map(depth_map, predictions["extrinsic"], predictions["intrinsic"])
    predictions["world_points_from_depth"] = world_points

    # Clean up
    torch.cuda.empty_cache()
    return predictions


# -------------------------------------------------------------------------
# 1.5) 深度图可视化
# -------------------------------------------------------------------------
# 伪彩色配色（cv2 的 colormap 名称，可选 INFERNO / TURBO / MAGMA / VIRIDIS / JET）
DEPTH_COLORMAP = "INFERNO"
# 最多渲染多少帧，避免输入帧数过多时生成过慢
DEPTH_MAX_FRAMES = 64


def save_depth_images(predictions, target_dir, max_frames=DEPTH_MAX_FRAMES):
    """
    把 predictions["depth"] 逐帧渲染成伪彩色深度图 PNG，存到 target_dir/depth/ 下。

    返回 [(图片路径, 说明文字), ...]，可直接喂给 gr.Gallery 展示。

    每帧用 2%~98% 分位数做归一化，避免个别极远/极近的离群点把整体对比度压平。
    """
    depth = predictions.get("depth")
    if depth is None:
        print("[深度图] predictions 中没有 depth，跳过")
        return []

    depth = np.asarray(depth, dtype=np.float32)
    if depth.ndim == 4:      # (S, H, W, 1) -> (S, H, W)
        depth = depth[..., 0]
    if depth.ndim == 2:      # 单帧 -> 补一维
        depth = depth[None]

    out_dir = os.path.join(target_dir, "depth")
    os.makedirs(out_dir, exist_ok=True)

    colormap = getattr(cv2, f"COLORMAP_{DEPTH_COLORMAP}", cv2.COLORMAP_INFERNO)
    results = []
    num_frames = min(depth.shape[0], max_frames)

    for i in range(num_frames):
        d = depth[i]
        # 分位数归一化，抗离群值
        lo, hi = np.nanpercentile(d, 2), np.nanpercentile(d, 98)
        if not (np.isfinite(lo) and np.isfinite(hi)) or hi - lo < 1e-6:
            lo, hi = np.nanmin(d), np.nanmax(d)
        if not (np.isfinite(lo) and np.isfinite(hi)) or hi - lo < 1e-6:
            lo, hi = 0.0, 1.0
        d_norm = np.nan_to_num((d - lo) / (hi - lo), nan=0.0, posinf=1.0, neginf=0.0)
        d_norm = np.clip(d_norm, 0.0, 1.0)

        color = cv2.applyColorMap((d_norm * 255).astype(np.uint8), colormap)
        out_path = os.path.join(out_dir, f"{i:06d}.png")
        cv2.imwrite(out_path, color)
        results.append((out_path, f"帧 {i}"))

    print(f"[深度图] 已生成 {len(results)} 张 -> {out_dir}")
    return results


# -------------------------------------------------------------------------
# 2) Handle uploaded video/images --> produce target_dir + images
# -------------------------------------------------------------------------
def handle_uploads(input_video, input_images):
    """
    Create a new 'target_dir' + 'images' subfolder, and place user-uploaded
    images or extracted frames from video into it. Return (target_dir, image_paths).
    """
    start_time = time.time()
    gc.collect()
    torch.cuda.empty_cache()

    # Create a unique folder name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    target_dir = f"input_images_{timestamp}"
    target_dir_images = os.path.join(target_dir, "images")

    # Clean up if somehow that folder already exists
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)
    os.makedirs(target_dir)
    os.makedirs(target_dir_images)

    image_paths = []

    # --- Handle images ---
    if input_images is not None:
        for file_data in input_images:
            if isinstance(file_data, dict) and "name" in file_data:
                file_path = file_data["name"]
            else:
                file_path = file_data
            dst_path = os.path.join(target_dir_images, os.path.basename(file_path))
            shutil.copy(file_path, dst_path)
            image_paths.append(dst_path)

    # --- Handle video ---
    if input_video is not None:
        if isinstance(input_video, dict) and "name" in input_video:
            video_path = input_video["name"]
        else:
            video_path = input_video

        vs = cv2.VideoCapture(video_path)
        fps = vs.get(cv2.CAP_PROP_FPS)
        frame_interval = int(fps * 1)  # 1 frame/sec

        count = 0
        video_frame_num = 0
        while True:
            gotit, frame = vs.read()
            if not gotit:
                break
            count += 1
            if count % frame_interval == 0:
                image_path = os.path.join(target_dir_images, f"{video_frame_num:06}.png")
                cv2.imwrite(image_path, frame)
                image_paths.append(image_path)
                video_frame_num += 1

    # Sort final images for gallery
    image_paths = sorted(image_paths)

    end_time = time.time()
    print(f"Files copied to {target_dir_images}; took {end_time - start_time:.3f} seconds")
    return target_dir, image_paths


# -------------------------------------------------------------------------
# 产物备份：每次产生输出后，把产物复制一份到 OUTPUT_BACKUP_DIR
# -------------------------------------------------------------------------
def backup_outputs(target_dir, files=None):
    """
    把本次重建产生的产物复制一份到 OUTPUT_BACKUP_DIR/<本次运行标识>/ 下。

    参数:
        target_dir: 本次运行的工作目录（形如 input_images_<时间戳>）
        files: 显式指定要备份的文件列表；为 None 时按 BACKUP_FILE_PATTERNS 自动收集

    返回:
        备份目录路径；没有可备份文件或备份失败时返回 None（不影响主流程）。
    """
    if not target_dir or target_dir == "None" or not os.path.isdir(target_dir):
        return None

    # --- 收集要备份的文件 ---
    if files is None:
        collected = []
        for pattern in BACKUP_FILE_PATTERNS:
            collected.extend(glob.glob(os.path.join(target_dir, pattern)))
    else:
        collected = list(files)

    files_to_copy = sorted({os.path.abspath(f) for f in collected if f and os.path.isfile(f)})
    if not files_to_copy:
        print(f"[备份] 在 {target_dir} 未找到可备份的产物，跳过")
        return None

    # --- 用去掉 input_images_ 前缀后的时间戳作为本次运行的备份目录名 ---
    run_name = os.path.basename(os.path.normpath(target_dir))
    if run_name.startswith("input_images_"):
        run_name = run_name[len("input_images_"):]
    backup_dir = os.path.join(OUTPUT_BACKUP_DIR, run_name)

    # --- 复制（失败只提示，不打断主流程）---
    try:
        os.makedirs(backup_dir, exist_ok=True)
        for src in files_to_copy:
            shutil.copy2(src, os.path.join(backup_dir, os.path.basename(src)))
        print(f"[备份] 已复制 {len(files_to_copy)} 个产物 -> {backup_dir}")
        return backup_dir
    except Exception as e:
        print(f"[备份] 复制产物失败: {e}")
        return None


# -------------------------------------------------------------------------
# 3) Update gallery on upload
# -------------------------------------------------------------------------
def update_gallery_on_upload(input_video, input_images):
    """
    Whenever user uploads or changes files, immediately handle them
    and show in the gallery. Return (target_dir, image_paths).
    If nothing is uploaded, returns "None" and empty list.
    """
    if not input_video and not input_images:
        return None, None, None, None, None
    target_dir, image_paths = handle_uploads(input_video, input_images)
    return None, target_dir, image_paths, "上传完成. 点击'Reconstruct'开始3D重建.", None


# -------------------------------------------------------------------------
# 4) Reconstruction: uses the target_dir plus any viz parameters
# -------------------------------------------------------------------------
def gradio_demo(
    target_dir,
    conf_thres=3.0,
    frame_filter="All",
    mask_black_bg=False,
    mask_white_bg=False,
    show_cam=True,
    mask_sky=False,
    prediction_mode="Pointmap Regression",
):
    """
    Perform reconstruction using the already-created target_dir/images.
    """
    if not os.path.isdir(target_dir) or target_dir == "None":
        return None, "No valid target directory found. Please upload first.", None, None

    # 中文预测模式 -> 英文规范值（下游靠 "Pointmap" 关键字选分支）
    prediction_mode = normalize_prediction_mode(prediction_mode)

    start_time = time.time()
    gc.collect()
    torch.cuda.empty_cache()

    # Prepare frame_filter dropdown
    target_dir_images = os.path.join(target_dir, "images")
    all_files = sorted(os.listdir(target_dir_images)) if os.path.isdir(target_dir_images) else []
    all_files = [f"{i}: {filename}" for i, filename in enumerate(all_files)]
    frame_filter_choices = ["All"] + all_files

    print("Running run_model...")
    with torch.no_grad():
        predictions = run_model(target_dir, model)

    # Save predictions
    prediction_save_path = os.path.join(target_dir, "predictions.npz")
    np.savez(prediction_save_path, **predictions)

    # Handle None frame_filter
    if frame_filter is None:
        frame_filter = "All"

    # Build a GLB file name
    glbfile = os.path.join(
        target_dir,
        f"glbscene_{conf_thres}_{frame_filter.replace('.', '_').replace(':', '').replace(' ', '_')}_maskb{mask_black_bg}_maskw{mask_white_bg}_cam{show_cam}_sky{mask_sky}_pred{prediction_mode.replace(' ', '_')}.glb",
    )

    # Convert predictions to GLB
    glbscene = predictions_to_glb(
        predictions,
        conf_thres=conf_thres,
        filter_by_frames=frame_filter,
        mask_black_bg=mask_black_bg,
        mask_white_bg=mask_white_bg,
        show_cam=show_cam,
        mask_sky=mask_sky,
        target_dir=target_dir,
        prediction_mode=prediction_mode,
    )
    glbscene.export(file_obj=glbfile)

    # 渲染深度图，供界面上的"深度图"展示框使用
    depth_images = save_depth_images(predictions, target_dir)

    # 每次产生输出后，把产物（predictions.npz + glbscene_*.glb）复制一份到输出目录
    backup_dir = backup_outputs(target_dir)

    # Cleanup
    del predictions
    gc.collect()
    torch.cuda.empty_cache()

    end_time = time.time()
    print(f"Total time: {end_time - start_time:.2f} seconds (including IO)")
    log_msg = f"Reconstruction Success ({len(all_files)} frames). Waiting for visualization."
    if backup_dir:
        log_msg += " ｜ 产物已备份"

    return (
        glbfile,
        log_msg,
        gr.Dropdown(choices=frame_filter_choices, value=frame_filter, interactive=True),
        depth_images,
    )


# -------------------------------------------------------------------------
# 5) Helper functions for UI resets + re-visualization
# -------------------------------------------------------------------------
def clear_fields():
    """
    Clears the 3D viewer, the stored target_dir, and empties the gallery.
    """
    return None


def update_log():
    """
    Display a quick log message while waiting.
    """
    return "Loading and Reconstructing..."


def update_visualization(
    target_dir, conf_thres, frame_filter, mask_black_bg, mask_white_bg, show_cam, mask_sky, prediction_mode, is_example
):
    """
    Reload saved predictions from npz, create (or reuse) the GLB for new parameters,
    and return it for the 3D viewer. If is_example == "True", skip.
    """

    # If it's an example click, skip as requested
    if is_example == "True":
        return None, "No reconstruction available. Please click the Reconstruct button first."

    if not target_dir or target_dir == "None" or not os.path.isdir(target_dir):
        return None, "No reconstruction available. Please click the Reconstruct button first."

    # 中文预测模式 -> 英文规范值（与 gradio_demo 保持一致，避免 glb 缓存对不上）
    prediction_mode = normalize_prediction_mode(prediction_mode)

    predictions_path = os.path.join(target_dir, "predictions.npz")
    if not os.path.exists(predictions_path):
        return None, f"No reconstruction available at {predictions_path}. Please run 'Reconstruct' first."

    key_list = [
        "pose_enc",
        "depth",
        "depth_conf",
        "world_points",
        "world_points_conf",
        "images",
        "extrinsic",
        "intrinsic",
        "world_points_from_depth",
    ]

    loaded = np.load(predictions_path)
    predictions = {key: np.array(loaded[key]) for key in key_list}

    glbfile = os.path.join(
        target_dir,
        f"glbscene_{conf_thres}_{frame_filter.replace('.', '_').replace(':', '').replace(' ', '_')}_maskb{mask_black_bg}_maskw{mask_white_bg}_cam{show_cam}_sky{mask_sky}_pred{prediction_mode.replace(' ', '_')}.glb",
    )

    if not os.path.exists(glbfile):
        glbscene = predictions_to_glb(
            predictions,
            conf_thres=conf_thres,
            filter_by_frames=frame_filter,
            mask_black_bg=mask_black_bg,
            mask_white_bg=mask_white_bg,
            show_cam=show_cam,
            mask_sky=mask_sky,
            target_dir=target_dir,
            prediction_mode=prediction_mode,
        )
        glbscene.export(file_obj=glbfile)
        # 新参数新生成的 glb 也一并备份一份
        backup_outputs(target_dir, files=[glbfile])

    return glbfile, "Updating Visualization"


# -------------------------------------------------------------------------
# Example images
# -------------------------------------------------------------------------

great_wall_video = "examples/videos/great_wall.mp4"
colosseum_video = "examples/videos/Colosseum.mp4"
room_video = "examples/videos/room.mp4"
kitchen_video = "examples/videos/kitchen.mp4"
fern_video = "examples/videos/fern.mp4"
single_cartoon_video = "examples/videos/single_cartoon.mp4"
single_oil_painting_video = "examples/videos/single_oil_painting.mp4"
pyramid_video = "examples/videos/pyramid.mp4"


# -------------------------------------------------------------------------
# 6) Build Gradio UI
# -------------------------------------------------------------------------
theme = gr.themes.Ocean()
theme.set(
    checkbox_label_background_fill_selected="*button_primary_background_fill",
    checkbox_label_text_color_selected="*button_primary_text_color",
)

with gr.Blocks(
    theme=theme,
    css="""
    .custom-log * {
        font-style: italic;
        font-size: 22px !important;
        background-image: linear-gradient(120deg, #0ea5e9 0%, #6ee7b7 60%, #34d399 100%);
        -webkit-background-clip: text;
        background-clip: text;
        font-weight: bold !important;
        color: transparent !important;
        text-align: center !important;
    }
    
    .example-log * {
        font-style: italic;
        font-size: 16px !important;
        background-image: linear-gradient(120deg, #0ea5e9 0%, #6ee7b7 60%, #34d399 100%);
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent !important;
    }
    
    #my_radio .wrap {
        display: flex;
        flex-wrap: nowrap;
        justify-content: center;
        align-items: center;
    }

    #my_radio .wrap label {
        display: flex;
        width: 50%;
        justify-content: center;
        align-items: center;
        margin: 0;
        padding: 10px 0;
        box-sizing: border-box;
    }
    """,
) as demo:
    # Instead of gr.State, we use a hidden Textbox:
    is_example = gr.Textbox(label="is_example", visible=False, value="None")
    num_images = gr.Textbox(label="num_images", visible=False, value="None")

    gr.HTML(
        """
    <h1>🏛️ VGGT: 视觉几何定位 Transformer</h1>
    <p>
    <a href="https://github.com/facebookresearch/vggt">🐙 GitHub 仓库</a> |
    <a href="#">项目页面</a>
    </p>

    <div style="font-size: 16px; line-height: 1.5;">
    <p>上传视频或一组图片来创建场景或物体的 3D 重建。VGGT 将处理这些图片并生成 3D 点云以及估计的相机位姿。</p>

    <h3>使用步骤：</h3>
    <ol>
        <li><strong>上传数据：</strong> 使用左侧的"上传视频"或"上传图片"按钮来提供输入。视频将被自动拆分为单帧（每秒一帧）。</li>
        <li><strong>预览：</strong> 已上传的图片将显示在左侧的图库中。</li>
        <li><strong>重建：</strong> 点击"Reconstruct"按钮开始 3D 重建过程。</li>
        <li><strong>可视化：</strong> 3D 重建结果将显示在右侧的查看器中。您可以旋转、平移和缩放来探索模型，并可下载 GLB 文件。注意：当输入图片数量较多时，3D 点的可视化可能会较慢。</li>
        <li>
        <strong>调整可视化（可选）：</strong>
        重建完成后，您可以使用以下选项微调可视化效果
        <details style="display:inline;">
            <summary style="display:inline;">（<strong>点击展开</strong>）：</summary>
            <ul>
            <li><em>置信度阈值：</em> 根据置信度过滤点的显示。</li>
            <li><em>显示指定帧的点：</em> 选择特定帧在点云中显示。</li>
            <li><em>显示相机：</em> 切换是否显示估计的相机位置。</li>
            <li><em>过滤天空 / 过滤黑色背景：</em> 移除天空或黑色背景的点。</li>
            <li><em>选择预测模式：</em> 在"深度图与相机分支"或"点图分支"之间选择。</li>
            </ul>
        </details>
        </li>
    </ol>
    <p><strong style="color: #0ea5e9;">请注意：</strong> <span style="color: #0ea5e9; font-weight: bold;">VGGT 通常在不到 1 秒内完成场景重建。然而，3D 点的可视化可能需要数十秒，这是由于第三方渲染所致，与 VGGT 的处理时间无关。</span></p>
    </div>
    """
    )

    target_dir_output = gr.Textbox(label="Target Dir", visible=False, value="None")

    with gr.Row():
        with gr.Column(scale=2):
            input_video = gr.Video(label="Upload Video", interactive=True)
            input_images = gr.File(file_count="multiple", label="Upload Images", interactive=True)

            image_gallery = gr.Gallery(
                label="Preview",
                columns=4,
                height="300px",
                show_download_button=True,
                object_fit="contain",
                preview=True,
            )

        with gr.Column(scale=4):
            with gr.Column():
                gr.Markdown("**3D 重建 (点云和相机位姿)**")
                log_output = gr.Markdown(
                    "请上传视频或图片, 然后点击'Reconstruct'开始3D重建.", elem_classes=["custom-log"]
                )
                reconstruction_output = gr.Model3D(height=520, zoom_speed=0.5, pan_speed=0.5)

            # ---- 深度图展示框 ----
            with gr.Column():
                gr.Markdown("**深度图 (Depth Map)**")
                depth_gallery = gr.Gallery(
                    label="深度图",
                    columns=4,
                    height="260px",
                    show_download_button=True,
                    object_fit="contain",
                    preview=True,
                )

            with gr.Row():
                submit_btn = gr.Button("Reconstruct", scale=1, variant="primary")
                clear_btn = gr.ClearButton(
                    [
                        input_video,
                        input_images,
                        reconstruction_output,
                        log_output,
                        target_dir_output,
                        image_gallery,
                        depth_gallery,
                    ],
                    scale=1,
                )

            with gr.Row():
                prediction_mode = gr.Radio(
                    ["深度图与相机分支", "点云图分支"],
                    label="选择预测模式",
                    value="深度图与相机分支",
                    scale=1,
                    elem_id="my_radio",
                )

            with gr.Row():
                conf_thres = gr.Slider(minimum=0, maximum=100, value=50, step=0.1, label="置信度阈值 (%)")
                frame_filter = gr.Dropdown(choices=["All"], value="All", label="显示指定帧的点")
                with gr.Column():
                    show_cam = gr.Checkbox(label="显示相机", value=True)
                    mask_sky = gr.Checkbox(label="过滤天空", value=False)
                    mask_black_bg = gr.Checkbox(label="过滤黑色背景", value=False)
                    mask_white_bg = gr.Checkbox(label="过滤白色背景", value=False)

    # ---------------------- Examples section ----------------------
    examples = [
        [colosseum_video, "22", None, 20.0, False, False, True, False, "深度图与相机分支", "True"],
        [pyramid_video, "30", None, 35.0, False, False, True, False, "深度图与相机分支", "True"],
        [single_cartoon_video, "1", None, 15.0, False, False, True, False, "深度图与相机分支", "True"],
        [single_oil_painting_video, "1", None, 20.0, False, False, True, True, "深度图与相机分支", "True"],
        [room_video, "8", None, 5.0, False, False, True, False, "深度图与相机分支", "True"],
        [kitchen_video, "25", None, 50.0, False, False, True, False, "深度图与相机分支", "True"],
        [fern_video, "20", None, 45.0, False, False, True, False, "深度图与相机分支", "True"],
    ]

    def example_pipeline(
        input_video,
        num_images_str,
        input_images,
        conf_thres,
        mask_black_bg,
        mask_white_bg,
        show_cam,
        mask_sky,
        prediction_mode,
        is_example_str,
    ):
        """
        1) Copy example images to new target_dir
        2) Reconstruct
        3) Return model3D + logs + new_dir + updated dropdown + gallery
        We do NOT return is_example. It's just an input.
        """
        target_dir, image_paths = handle_uploads(input_video, input_images)
        # Always use "All" for frame_filter in examples
        frame_filter = "All"
        glbfile, log_msg, dropdown, depth_images = gradio_demo(
            target_dir, conf_thres, frame_filter, mask_black_bg, mask_white_bg, show_cam, mask_sky, prediction_mode
        )
        return glbfile, log_msg, target_dir, dropdown, image_paths, depth_images

    gr.Markdown("Click any row to load an example.", elem_classes=["example-log"])

    gr.Examples(
        examples=examples,
        inputs=[
            input_video,
            num_images,
            input_images,
            conf_thres,
            mask_black_bg,
            mask_white_bg,
            show_cam,
            mask_sky,
            prediction_mode,
            is_example,
        ],
        outputs=[reconstruction_output, log_output, target_dir_output, frame_filter, image_gallery, depth_gallery],
        fn=example_pipeline,
        cache_examples=False,
        examples_per_page=50,
    )

    # -------------------------------------------------------------------------
    # "Reconstruct" button logic:
    #  - Clear fields
    #  - Update log
    #  - gradio_demo(...) with the existing target_dir
    #  - Then set is_example = "False"
    # -------------------------------------------------------------------------
    submit_btn.click(fn=clear_fields, inputs=[], outputs=[reconstruction_output]).then(
        fn=update_log, inputs=[], outputs=[log_output]
    ).then(
        fn=gradio_demo,
        inputs=[
            target_dir_output,
            conf_thres,
            frame_filter,
            mask_black_bg,
            mask_white_bg,
            show_cam,
            mask_sky,
            prediction_mode,
        ],
        outputs=[reconstruction_output, log_output, frame_filter, depth_gallery],
    ).then(
        fn=lambda: "False", inputs=[], outputs=[is_example]  # set is_example to "False"
    )

    # -------------------------------------------------------------------------
    # Real-time Visualization Updates
    # -------------------------------------------------------------------------
    conf_thres.change(
        update_visualization,
        [
            target_dir_output,
            conf_thres,
            frame_filter,
            mask_black_bg,
            mask_white_bg,
            show_cam,
            mask_sky,
            prediction_mode,
            is_example,
        ],
        [reconstruction_output, log_output],
    )
    frame_filter.change(
        update_visualization,
        [
            target_dir_output,
            conf_thres,
            frame_filter,
            mask_black_bg,
            mask_white_bg,
            show_cam,
            mask_sky,
            prediction_mode,
            is_example,
        ],
        [reconstruction_output, log_output],
    )
    mask_black_bg.change(
        update_visualization,
        [
            target_dir_output,
            conf_thres,
            frame_filter,
            mask_black_bg,
            mask_white_bg,
            show_cam,
            mask_sky,
            prediction_mode,
            is_example,
        ],
        [reconstruction_output, log_output],
    )
    mask_white_bg.change(
        update_visualization,
        [
            target_dir_output,
            conf_thres,
            frame_filter,
            mask_black_bg,
            mask_white_bg,
            show_cam,
            mask_sky,
            prediction_mode,
            is_example,
        ],
        [reconstruction_output, log_output],
    )
    show_cam.change(
        update_visualization,
        [
            target_dir_output,
            conf_thres,
            frame_filter,
            mask_black_bg,
            mask_white_bg,
            show_cam,
            mask_sky,
            prediction_mode,
            is_example,
        ],
        [reconstruction_output, log_output],
    )
    mask_sky.change(
        update_visualization,
        [
            target_dir_output,
            conf_thres,
            frame_filter,
            mask_black_bg,
            mask_white_bg,
            show_cam,
            mask_sky,
            prediction_mode,
            is_example,
        ],
        [reconstruction_output, log_output],
    )
    prediction_mode.change(
        update_visualization,
        [
            target_dir_output,
            conf_thres,
            frame_filter,
            mask_black_bg,
            mask_white_bg,
            show_cam,
            mask_sky,
            prediction_mode,
            is_example,
        ],
        [reconstruction_output, log_output],
    )

    # -------------------------------------------------------------------------
    # Auto-update gallery whenever user uploads or changes their files
    # -------------------------------------------------------------------------
    input_video.change(
        fn=update_gallery_on_upload,
        inputs=[input_video, input_images],
        outputs=[reconstruction_output, target_dir_output, image_gallery, log_output, depth_gallery],
    )
    input_images.change(
        fn=update_gallery_on_upload,
        inputs=[input_video, input_images],
        outputs=[reconstruction_output, target_dir_output, image_gallery, log_output, depth_gallery],
    )

    # 端口被占用时不要硬报错，交给 Gradio 自动往后找空闲端口
    if SERVER_PORT is None:
        launch_port = None
        print("[启动] 由 Gradio 自动选择空闲端口")
    elif is_port_free(SERVER_PORT):
        launch_port = SERVER_PORT
    else:
        launch_port = None
        print(f"[启动] 端口 {SERVER_PORT} 已被占用（常见原因：上一次运行没关干净），"
              f"改为让 Gradio 自动往后找空闲端口")

    demo.queue(max_size=20).launch(
        server_name=SERVER_NAME,
        server_port=launch_port,
        show_error=True,
        share=ENABLE_SHARE,
        inbrowser=True,
    )
