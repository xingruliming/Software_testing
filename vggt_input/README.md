# vggt_input/ — VGGT 输入素材

本目录集中存放 VGGT 的**输入数据**（图像序列 / 视频），内容复制自 `vggt-main/examples/`。

> 原目录 `vggt-main/examples/` 保持不动，因为 `demo_viser.py` 等脚本的默认参数写死了 `examples/kitchen/images/` 这类相对路径。

## 目录结构

```
vggt_input/
├── <场景名>/images/      # 多视角图像序列，按场景分文件夹
├── videos/               # 输入视频（demo 会自动抽帧）
└── README.md
```

## 图像序列场景（共 6 个，68 张图）

| 场景 | 路径 | 图片数 |
|---|---|---|
| kitchen | `vggt_input/kitchen/images/` | 25 |
| llff_fern | `vggt_input/llff_fern/images/` | 20 |
| llff_flower | `vggt_input/llff_flower/images/` | 25 |
| room | `vggt_input/room/images/` | 8 |
| single_cartoon | `vggt_input/single_cartoon/images/` | 1 |
| single_oil_painting | `vggt_input/single_oil_painting/images/` | 1 |

## 视频（共 8 个）

`Colosseum.mp4`、`fern.mp4`、`great_wall.mp4`、`kitchen.mp4`、`pyramid.mp4`、`room.mp4`、`single_cartoon.mp4`、`single_oil_painting.mp4`

## 各脚本的输入参数对应关系

| 脚本 | 参数 | 取值示例（在 `vggt-main/` 下执行） |
|---|---|---|
| `demo_viser.py` | `--image_folder` | `../vggt_input/room/images/` |
| `demo_colmap.py` | `--scene_dir` | `../vggt_input/room`（脚本内部拼接 `images/`） |
| `demo_gradio.py` | 网页上传 | 手动选择 `vggt_input/` 下的图片或视频 |
| `demo_gradio_cn.py` | 网页上传 | 同上（中文界面版） |
| `main.py` | 硬编码路径 | 直接改 `image_names` 列表里的路径 |

运行示例：

```bash
cd "E:/办公/研一/1软件实践/Software_testing/vggt-main"
python demo_viser.py --image_folder ../vggt_input/room/images/
python demo_colmap.py --scene_dir ../vggt_input/room
```

## ⚠️ 两个容易踩的坑

1. **`demo_colmap.py` 是"就地输出"**：它不写到独立的输出目录，而是直接往 `{scene_dir}/` 下塞 `sparse/` 子目录和 `points.ply`。
   所以如果直接把 `--scene_dir` 指向本目录，重建结果会污染输入素材。
   **建议**：先把场景复制一份到 `vggt_output/colmap_work/<场景>/`，再对该副本运行。

2. **`demo_viser.py --mask_sky` 会写旁路目录**：开启后会在 `{image_folder}` 同级生成 `<image_folder>_sky_masks/`，也就是 `vggt_input/room/images_sky_masks/`。
   不想让输入目录变脏的话，同样建议对 `vggt_output/` 下的副本来跑。
