# VGGT 软件测试与质量保证实践

本仓库以 VGGT 的几何坐标转换模块为模块一被测对象，并保留 VGGT 中文可视化程序用于功能演示。教师已明确许可 AI 参与模块一用例设计。

**模块一坐标转换（A 线）已完成**：32 条正式用例（另含 1 条对照，共 33 条）已全部实现为 `unittest` 自动化代码，一键入口 `run_tests.ps1` / `双击运行模块一测试.bat` 可直接运行并归档结果。当前实测 **33 条中 31 条通过、2 条失败**，失败项指向已登记且尚未修复的缺陷 `DEF-M1-001`。

## 当前阶段

- 模块一坐标转换（A 线）已完成用例设计、自动化实现与正式执行；缺陷记录与报告在 `deliverables/module1/`。
- 模块一图像处理（B 线）已有 3 个完成修复验证的缺陷，产物在 `image_test_module1/`。
- 模块二（AI 融合实践）产物在 `deliverables/module2/`。
- `vggt-main/` 作为被测软件基线，默认不修改。
- `VGGT测试方案.md` 偏向 AI 系统鲁棒性分析，作为模块二储备材料，不计入模块一用例与结果。

## 被测对象

模块一被测对象为 `vggt-main/vggt/utils/geometry.py`，主要包含深度图反投影、相机/世界坐标转换、SE(3) 变换求逆、三维点投影和畸变处理等确定性功能。该模块约 324 行，可以在不加载 VGGT 大模型的情况下进行单元测试。

模块一不覆盖：

- 模型训练流程；
- 论文精度指标复现；
- 完整 10 亿参数模型的自动化性能测试；
- Gradio 页面端到端自动化；
- 模块二的 AI 鲁棒性、公平性和安全性测试。

## 目录结构

```text
Software_testing/
├── README.md
├── 双击运行模块一测试.bat       # 模块一（坐标转换）双击即跑的入口（调 run_tests.ps1）
├── run_tests.ps1              # 模块一（坐标转换）一键测试入口
├── run_vggt_demo.ps1          # 从正确工作目录启动现有可视化程序
├── run_vggt_inference.py      # 无界面推理：输入图像目录 -> 深度图 + GLB
├── metrics.py                 # 无真值自洽性指标工具（G1–G4）
├── cv2_unicode.py             # OpenCV 中文路径兼容层（cv2.imread / cv2.imwrite）
├── tests/                     # 模块一坐标转换测试工程（8 文件 / 33 条用例）
├── test_results/
│   ├── module1/               # 模块一执行日志、JUnit XML、DEF-M1-001 复现记录
│   └── module2/               # 模块二缺陷复现记录
├── deliverables/
│   ├── module1/               # 附录1 用例清单、附录2 缺陷报告、操作手册、检查清单
│   └── module2/               # 模块二报告、用例清单、缺陷报告
├── image_test_module1/        # 模块一图像处理（B 线）用例、缺陷测试与报告
├── vggt_input/                # 演示输入素材
├── vggt_output/               # 可再生的运行产物
└── vggt-main/                 # 被测软件与中文可视化程序
```

## 环境准备

当前已知环境：

- Windows；
- Conda 环境：`Pytorch_Vggt`（`D:\anaconda3\envs\Pytorch_Vggt\python.exe`）；
- Python：3.10.20；
- CUDA 版 PyTorch：2.8.0+cu128；
- GPU：NVIDIA GeForce RTX 3070 Laptop（8 GB）；
- 模型权重：`E:\0_work\1shijian\model.pt`（约 5.0 GB，位于本工程**上一级**）。

请勿将 `model.pt`、运行产生的点云/GLB、缓存或本地证书提交到 Git。若权重位置改变，`run_vggt_demo.ps1` / `run_vggt_inference.py` 的 `--model` 默认值及 `demo_gradio_cn.py` 中的既有权重路径需同步处理；模块一默认不修改该脚本。

## 启动 VGGT 可视化

推荐在 PowerShell 中从仓库根目录运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\run_vggt_demo.ps1
```

如果需要指定 Python：

```powershell
.\run_vggt_demo.ps1 -PythonExecutable "D:\anaconda3\envs\Pytorch_Vggt\python.exe"
```

也可以直接运行原程序，但必须先进入它所在的目录，以保证相对路径有效：

```powershell
Set-Location "E:\0_work\1shijian\Software_testing\vggt-main"
& "D:\anaconda3\envs\Pytorch_Vggt\python.exe" ".\demo_gradio_cn.py"
```

启动后按终端输出访问本地 Gradio 地址。结束服务时在启动终端按 `Ctrl+C`。

## 无界面批量推理（深度图 + GLB）

`run_vggt_inference.py` 复制了 `demo_gradio_cn.py` 的推理与产物逻辑，但完全不启动 Gradio，适合批量跑用例和自动化归档。

```powershell
& "D:\anaconda3\envs\Pytorch_Vggt\python.exe" .\run_vggt_inference.py `
    --input-dir  "vggt_input/001_watercup" `
    --output-dir "vggt_output/001_watercup"
```

产物（默认 `vggt_output/<输入目录名>/`）：

| 路径 | 内容 |
|---|---|
| `images/` | 输入图像副本 |
| `depth/000000.png ...` | 逐帧伪彩色深度图（INFERNO，2%~98% 分位数归一化） |
| `predictions.npz` | 完整预测（`depth`、`depth_conf`、`world_points`、`extrinsic`、`intrinsic`、`world_points_from_depth` …） |
| `glbscene_*.glb` | 3D 场景（点云 + 相机），每个预测分支一个 |
| `run_info.json` | `inference` 块记录帧数、耗时、峰值显存；`this_run` 记录本轮的运行模式与耗时 |

常用参数：

- `--prediction-modes "深度图与相机分支,点云图分支"`：要导出 GLB 的分支，逗号分隔；留空则只出深度图和 npz。
- `--conf-thres 50.0`：GLB 点云置信度过滤百分比，与界面默认值一致。
- `--from-npz`：复用输出目录里已有的 `predictions.npz`，跳过推理，只重出深度图 / GLB（调参时用，秒级完成）。此时 `run_info.json` 的 `inference` 块会继承首轮的真实统计，不会被清零。
- `--mask-sky` / `--mask-white-bg` / `--mask-black-bg` / `--no-show-cam`：同界面上的可视化选项。

### 中文路径兼容层 `cv2_unicode.py`

> ⚠️ **已知缺陷：`cv2.imwrite` / `cv2.imread` 在含中文的路径下静默失败。**
> Windows 上 OpenCV 按 ANSI 码页处理路径：`imwrite` 返回 `False` 且不抛异常、`imread` 返回 `None` 只打一条 WARN。
> 只要路径含非 ASCII 字符（如中文目录名或中文文件名）即会触发，调用方若不检查返回值就会「日志说成功、磁盘上没文件」。

`cv2_unicode.py` 用 `np.fromfile` + `cv2.imdecode` 读、`cv2.imencode` + 文件对象写来绕开该问题：

```python
import cv2_unicode
cv2_unicode.patch()          # 全局替换，原代码里的 cv2.imread / cv2.imwrite 自动生效
cv2_unicode.unpatch()        # 还原原生实现，用于复现缺陷
```

`run_vggt_inference.py` 已接入该兼容层，深度图写盘不再静默失败。

**待办（本轮未处理）**：被测程序 `vggt-main/` 基线内部的调用点仍存在同一问题 ——
`demo_gradio_cn.py` 的 `save_depth_images()`、上传视频抽帧的 `cv2.imwrite()`，
以及 `visual_util.segment_sky()` 的 `cv2.imread()` / `cv2.imwrite()`。
它们只影响可视化界面（深度图画廊为空、天空过滤失效），不影响深度图与 GLB 结果本身。
按「基线默认不修改」的约定，这些位置留作缺陷记录，后续可用兼容层统一处理。

## 模块一测试接入

1. ~~评审附录1中现有的 32 条用例，并建立测试编号与 pytest 函数的对应关系。~~
   —— 已完成：`tests/module1_coordinate/` 按 `M1-GEO-001 ~ 032` 编号实现。
2. ~~至少实现 24 条自动化，建议将当前 32 条可自动化用例全部实现。~~
   —— 已完成：33 条（32 条正式用例 + `M1-GEO-019` 的 1 条对照）。
3. ~~保留 Excel 中已经标注的等价类、边界值、错误推测、判定表和组合覆盖方法。~~
   —— 已完成，标注写入各用例 docstring。
4. ~~创建根目录 `run_tests.ps1`~~ —— 已创建，见下方「模块一一键测试入口」。
5. 只记录经过真实复现的有效缺陷；模块一缺陷报告至少需要 3 个有效缺陷及修复验证记录。
   —— 进行中：坐标转换线（A 线）现有 `DEF-M1-001`（见下）；图像处理线（B 线）已有 3 个已完成修复验证的缺陷。

### 当前执行结果（2026-09-14）

在仓库根目录执行 `run_tests.ps1` 的结果：**33 条中 31 条通过、2 条失败**。

失败的两条是 `M1-GEO-016`、`M1-GEO-018`，二者指向同一个**已登记且尚未修复**的缺陷
**`DEF-M1-001`**：`unproject_depth_map_to_point_map` 的文档声明支持 `(S,H,W)` 三维
深度图，但实现里 `depth_map[frame_idx].squeeze(-1)` 在 `W == 1` 时会删掉宽度维，
导致 `H, W = depth_map.shape` 解包失败。两条用例按文档承诺的**预期结果**断言，
因此缺陷修复前必然失败——这正是要暴露的问题；修复后应自动转为通过。

证据：`test_results/module1/DEF-M1-001_reproduction.txt`（复现记录）、
`test_results/module1/run_<时间戳>.log`（本次执行日志）。

具体操作顺序和填报要求见 `deliverables/module1/测试操作手册.docx`。

## 模块一一键测试入口

### 方式一：双击运行（推荐给现场演示）

直接双击仓库根目录的 **`双击运行模块一测试.bat`** 即可。它会自动切换码页与工作目录、
定位 PowerShell、调用 `run_tests.ps1`，跑完暂停窗口以便查看结果，并按退出码给出结论。

> 该 `.bat` 本体为 **纯 ASCII + UTF-8 无 BOM + CRLF**。这是刻意的：`cmd.exe` 按 DBCS 字节
> 偏移解析批处理，`chcp 65001` 中途改码页会让紧随其后的多字节字符被拆到读缓冲两端、
> 行尾泄漏成命令（实测 611 B 小文件报错、6.7 KB 同内容文件干净，属字节对齐而非体积问题）。
> 因此中文界面全部由 `run_tests.ps1` 与 Python 输出，`.bat` 只保留 ASCII 骨架。
> **请勿用编辑器把它另存为「带 BOM」或「LF 行尾」，否则报错会复发。**

### 方式二：命令行运行

`run_tests.ps1` 只负责模块一坐标转换系统（被测对象 `vggt-main/vggt/utils/geometry.py`，
用例 `M1-GEO-001 ~ M1-GEO-032`），不涉及模块二与 `image_test_module1/`。

在仓库根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\run_tests.ps1
```

也可显式指定解释器：

```powershell
.\run_tests.ps1 -PythonExecutable "D:\anaconda3\envs\Pytorch_Vggt\python.exe"
```

脚本行为：

1. **自动探测解释器**：依次尝试 `vggt-main\.venv`、仓库根 `.venv`、conda 环境
   `Pytorch_Vggt`，最后回退到 PATH 上的 `python`；也可用 `-PythonExecutable` 指定。
2. **前置检查**：确认基线目录、`geometry.py`、`tests\` 测试工程存在，并从外层验证
   能 import 被测模块（不导入 `demo_gradio_cn.py`，避免触发模型加载）。
3. **执行用例**：以 `tests\module1_coordinate\`（若不存在则退回 `tests\`）为发现起点，
   用 `unittest discover -p test_m1_geo*.py` 运行；从外层通过 `PYTHONPATH` 注入
   `vggt-main` 导入路径，**不修改被测源码**。
4. **归档结果**：控制台日志写入 `test_results\module1\run_<时间戳>.log`；
   若 `tests\junit_report.py` 存在则同时生成 `run_<时间戳>.xml`（JUnit XML）。
   **日志由 Python 以 UTF-8 直接落盘**，不经 PowerShell 文本捕获，避免中文双重编码。
5. **退出码**：`0` = 全部通过；`1` = 有失败/错误；`2` = 未找到测试工程；
   `3` = 无法导入被测模块。（`双击运行模块一测试.bat` 另用 `9` 表示前置条件不满足。）

参数：`-PythonExecutable <路径>`、`-TestPattern <glob>`（默认 `test_m1_geo*.py`）、
`-NoLog`（只打印不归档）。

> 注意：`.gitignore` 默认忽略 `test_results/module1/` 下的运行产物（仅跟踪 `README.md`），
> 需要提交测试证据时请显式 `git add -f` 或在 `module1/README.md` 中登记。

## Git 提交要求

- 每位小组成员使用自己的账号提交实际完成的工作。
- 不代替其他成员提交，也不重写历史伪造贡献。
- 提交信息清楚说明修改内容，例如测试方法、测试脚本、缺陷修复或文档更新。
- 提交前确认测试日志、报告统计和成员贡献说明能够相互对应。
