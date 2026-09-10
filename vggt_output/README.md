# vggt_output/ — VGGT 输出结果

本目录专门用于存放 VGGT 各脚本的**运行产物**，与输入素材 `vggt_input/` 分离，方便测试时对比、归档和清理。

初始为空（仅保留 `.gitkeep` 占位）。

## 建议的归档子结构

```
vggt_output/
├── colmap/          # demo_colmap.py 的 COLMAP 格式重建结果
├── gradio/          # demo_gradio.py / demo_gradio_cn.py 的网络结果
├── viser/           # demo_viser.py 的可视化产物
└── ply/             # export_ply.py 导出的点云
```

## 各脚本实际输出内容

### 1. `demo_colmap.py`

```bash
python demo_colmap.py --scene_dir ../vggt_output/colmap_work/room
```

输出**就地写进 `scene_dir`**：

```
<scene_dir>/
├── sparse/
│   ├── cameras.bin       # 相机参数（COLMAP 格式）
│   ├── images.bin        # 每张图像的位姿
│   ├── points3D.bin      # 三维点
│   └── points.ply        # 点云可视化文件
└── visuals/              # 可视化输出（TODO，源码中尚未实现）
```

### 2. `demo_gradio.py` / `demo_gradio_cn.py`

上传图片或视频后，脚本会在**当前工作目录**新建 `input_images_<时间戳>/`，内含：

| 文件 | 说明 |
|---|---|
| `images/` | 上传图片或从视频抽出的帧（帧名形如 `000001.png`） |
| `predictions.npz` | 模型预测结果（点图、深度图、相机位姿等） |
| `predictions.ply` | 点云文件（`demo_gradio.py` 生成） |
| `glbscene_*.glb` | 三维场景模型，网页中可旋转查看 |

> 注意：目录前缀是 `input_images_`，但它是**输出工作目录**，会直接建在 `vggt-main/` 根目录下。
> 测试时建议跑完手动移动到 `vggt_output/gradio/` 统一管理。

#### ✅ 已改造：`demo_gradio_cn.py` 会自动备份产物（2026-09-10）

`demo_gradio_cn.py` 里新增了 `backup_outputs()`，**每次产生输出后自动把产物复制一份**到本目录下：

```
vggt_output/gradio/<本次运行时间戳>/
├── predictions.npz
└── glbscene_*.glb
```

行为说明：

| 触发时机 | 复制内容 |
|---|---|
| 点击 `Reconstruct` 重建完成 | `predictions.npz` + 该次全部 `glbscene_*.glb` |
| 调整参数（置信度/显示相机/过滤天空等）生成**新的** glb | 仅新生成的 `glbscene_*.glb`，追加到同一次运行的目录 |

- 备份目录名 = 去掉 `input_images_` 前缀的时间戳，一次运行一个目录，不会互相覆盖
- 源文件**仍保留在** `vggt-main/input_images_<时间戳>/`，是复制不是移动
- 备份失败只打印提示，不会中断重建主流程
- 想改备份位置：修改 `demo_gradio_cn.py` 顶部的 `OUTPUT_BACKUP_DIR` 常量
- 想改备份哪些文件：修改同处的 `BACKUP_FILE_PATTERNS`

> `demo_gradio.py`（英文版）未做此改造，仍是原行为。

### 3. `demo_viser.py`

viser 网页可视化服务（默认端口 8080），本身不落盘为最终结果。
但加了 `--mask_sky` 后会在图像目录旁生成 `<image_folder>_sky_masks/`。

### 4. `export_ply.py`

从 gradio 产出的 `predictions.npz` 单独导出点云：

```bash
python export_ply.py ../vggt_output/gradio/<某次运行>/predictions.npz -o ../vggt_output/ply/room.ply -c 50
```

| 参数 | 说明 |
|---|---|
| `npz_path` | `predictions.npz` 路径（必填） |
| `-o / --output` | 输出 PLY 路径，默认与 npz 同目录同名 `.ply` |
| `-c / --conf` | 置信度阈值百分比，默认 50 |
| `-m / --mode` | `pointmap`（默认）或 `depth` |

## 清理

输出内容均为可再生结果，确认不再需要时可直接清空本目录（保留 `.gitkeep` 即可）。
