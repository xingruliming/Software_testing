# VGGT 模块二 · AI 输出单元测试（方案 1「测 AI」）

本目录是《VGGT 模块二测试用例清单》15 条用例（**M2-AI-001 ~ M2-AI-015**）的
自动化实现。测试对象是 VGGT 单次前馈的输出层——**深度图（depth / depth_conf）**
与 **npz 点云（world_points / world_points_from_depth）**，以及批量推理入口
`run_vggt_inference.py` 的输入校验行为。

测试框架为 Python 标准库 `unittest`（无第三方依赖），一键入口已内置
JUnit XML 与 UTF-8 日志归档。

---

## 1 快速开始

在**本目录**下双击或执行：

```
双击运行模块二测试.bat          # Windows 双击入口
```

或直接用 PowerShell：

```powershell
.\run_tests.ps1                 # 跑全部 15 条用例
```

脚本会自动完成：探测 Python 解释器 → 检查工程完整性 → 注入导入路径 →
运行 `m2_tests/` 下全部 `test_m2_ai*.py` → 归档结果到
`<仓库根>/test_results/module2/run_<时间戳>.log|.xml`。

**退出码**：`0`=全部通过｜`1`=存在失败或错误｜`2`=测试工程不完整｜`3`=无法导入被测模块。

> 首次运行若 `vggt_output/exp/` 缺少帧数与扰动变体，脚本会现场调用
> `run_vggt_inference.py` 生成（**约 6–10 分钟，需要 CUDA 与 model.pt**）。
> 生成一次后会被复用，后续运行只需秒级到一分钟。

---

## 2 目录结构

```
deliverables/module2/
├── README.md                      ← 本文档
├── 一键运行模块二测试.bat           ← 双击入口（纯 ASCII，只负责转发）
├── run_tests.ps1                  ← 一键驱动（解释器探测 / 导入路径 / 归档）
├── run_all_cases.py               ← 用例统一运行器（按编号驱动 / 逐条判定 / 缺陷折算）
└── m2_tests/
    ├── __init__.py
    ├── common.py                  ← 公共设施：产物定位、指标计算、推理调用、数据按需生成
    ├── junit_report.py            ← 单次运行同时产出 JUnit XML 与 UTF-8 日志
    ├── test_m2_ai_001_005_frame_effect.py       ← 帧数效应（001~005）
    ├── test_m2_ai_006_009_robustness.py         ← 鲁棒性扰动与确定性（006~009）
    ├── test_m2_ai_010_012_scene_dependency.py   ← 场景依赖与裁切假说（010~012）
    └── test_m2_ai_013_015_input_validation.py   ← 推理入口输入校验（013~015）
```

被测对象与被复用工具（均位于仓库根，**未做任何修改**）：

| 文件 | 作用 |
| --- | --- |
| `run_vggt_inference.py` | 无界面批量推理入口（被测的调用链入口） |
| `metrics.py` | 无真值几何自洽性指标 G1–G4 计算（测试直接导入其 `compute_all`） |
| `tools/robustness_experiments.py` | 帧数扫描与扰动矩阵生成（测试按需复用它生成缺失变体） |
| `vggt-main/` | VGGT 官方基线（被测软件本体） |

---

## 3 环境要求

| 项 | 要求 |
| --- | --- |
| 操作系统 | Windows 10/11 + PowerShell 5.1 及以上（兼容 pwsh） |
| Python | 3.10（实测 Anaconda 环境 `Pytorch_Vggt`：Python 3.10.20 + torch 2.8.0+cu128） |
| 依赖 | numpy、Pillow、torch（GPU 用例需要）；**unittest 为标准库，无需 pip 安装** |
| 权重 | `model.pt`（约 5.02 GB，位于仓库上一级目录），仅 GPU 用例需要 |
| 显存 | 9 帧推理峰值约 8.5 GB（RTX 3070 Laptop 8 GB 实测上限） |

解释器探测顺序（命中即用）：显式参数 `-PythonExecutable` →
`vggt-main\.venv` → 仓库根 `.venv` → `D:\anaconda3\envs\Pytorch_Vggt\python.exe`
（硬编码兜底）→ 系统 `PATH`。

---

## 4 运行方式

### 4.1 一键运行全部用例

```powershell
.\run_tests.ps1                                    # 默认：15 条全跑，缺失数据自动生成
```

### 4.2 无 GPU / 只做快速回归

```powershell
.\run_tests.ps1 -Prepare:$false
```

关闭自动生成后，依赖新推理产物的用例会被标记为 **skipped** 并在消息里给出
生成办法；其余用例（基线断言、低置信场景、输入校验）照常执行。

### 4.3 只跑部分用例

```powershell
.\run_tests.ps1 -TestPattern "test_m2_ai_013_015*.py"   # 只跑输入校验三条
.\run_tests.ps1 -TestPattern "test_m2_ai_00*.py"        # 只跑帧数效应五条
```

### 4.4 显式指定解释器 / 不写归档

```powershell
.\run_tests.ps1 -PythonExecutable "D:\anaconda3\envs\Pytorch_Vggt\python.exe"
.\run_tests.ps1 -NoLog
```

### 4.5 直接使用 unittest（不经过驱动脚本）

```powershell
cd <仓库根>\deliverables\module2
$env:PYTHONPATH = "<仓库根>;<仓库根>\vggt-main"
D:\anaconda3\envs\Pytorch_Vggt\python.exe -m unittest discover -s m2_tests -t . -p "test_m2_ai*.py" -v
```

单独跑某一条用例：

```powershell
python -m unittest m2_tests.test_m2_ai_010_012_scene_dependency.TestSceneDependency.test_m2_ai_010_default_threshold_metrics_available -v
```

### 4.6 按用例编号驱动（run_all_cases.py）

`run_tests.ps1` 是「整包一次跑 + 一份 JUnit XML」；`run_all_cases.py` 是纯 Python 的
用例运行器，补上它没有的能力：**按编号驱动、逐条独立判定与计时、缺陷折算、多格式归档**。
二者互不替代，共用同一套 `m2_tests/` 用例。

```powershell
python run_all_cases.py                        # 跑全部 15 条（一键）
python run_all_cases.py --list                 # 只列清单与数据就绪情况，不执行任何测试
python run_all_cases.py --cases 010-012,015    # 只跑指定编号
python run_all_cases.py --from 006 --to 009    # 按编号区间
python run_all_cases.py --no-prepare           # 无 GPU：缺失数据标记为跳过
python run_all_cases.py --isolated --timeout 900    # 每条用例独立子进程 + 硬超时
python run_all_cases.py --strict               # 关闭缺陷折算，用于修复后的全绿验收
```

每条用例的结论含义：

| 结论 | 含义 |
| --- | --- |
| `PASS` | 通过 |
| `FAIL` / `ERROR` | 非预期失败 / 错误（回归） |
| `SKIP` | 依赖产物缺失，用例跳过（消息里给出补齐办法） |
| `XFAIL` | 「预期失败」用例按预期失败（复现 DEF-M2-003 / DEF-M2-001），**不算回归** |
| `XPASS` | 「预期失败」用例却通过了 —— 缺陷疑似已修复，需复核缺陷报告与清单 |

退出码：`0`=全部符合预期｜`1`=存在非预期失败或错误｜`2`=测试工程不完整｜
`3`=环境问题｜`4`=用例发现不完整（清单 15 条未全部落地）。

归档输出到 `test_results/module2/run_all_<时间戳>.txt|.json|.csv`
（csv 为 UTF-8-SIG，可直接用 Excel 打开后粘进测试报告）。

---

## 5 用例与断言对照表

15 条用例一一对应 15 个测试方法（方法名内含用例编号）。

| 用例 | 测试方法 | 数据来源 | 断言要点 |
| --- | --- | --- | --- |
| M2-AI-001 | `test_m2_ai_001_baseline_self_consistency` | `vggt_output/002_computer` | 四项指标可统计：G1 rel < 5e-3、G2 < 5 px 且 5 px 内占比 > 95%、G3 置信均值 > 5、G4 NCC > 0.8；深度图 9/9、两个 GLB 非空、峰值显存 ≤ 8.6 GB |
| M2-AI-002 | `test_m2_ai_002_five_frames_degrade` | `exp/N5` | 5 帧的 G1 相对误差大于 9 帧基线，且仍可统计 |
| M2-AI-003 | `test_m2_ai_003_two_frames_degrade_further` | `exp/N2` | 2 帧的 G1 相对误差大于 5 帧 |
| M2-AI-004 | `test_m2_ai_004_single_frame_g4_unavailable` | `exp/N1` | 单帧时 G4 报「不可用」；G1–G3 仍可统计 |
| M2-AI-005 | `test_m2_ai_005_monotonic_improvement_with_frames` | `N1/N2/N5/BASE` | 1→2→5→9 帧：G1 相对误差严格单调下降、G3 置信均值严格单调上升 |
| M2-AI-006 | `test_m2_ai_006_resolution_half_not_degraded` | `exp/res50` | 0.5 倍分辨率下 G2 变化 < 30%、G4 变化 < 15%（实测未显著退化，与用例原预期相反） |
| M2-AI-007 | `test_m2_ai_007_gaussian_noise_not_degraded` | `exp/noise10` | 高斯噪声 σ=10 下 G2/G4 与基线同量级（同上，实测未退化） |
| M2-AI-008 | `test_m2_ai_008_occlusion_significant_degradation` | `exp/occ25` | 遮挡 25% 面积后 G4 NCC 降幅 > 20%、低置信占比上升 > 5 个百分点 |
| M2-AI-009 | `test_m2_ai_009_determinism_bitwise_identical` | `exp/det2` vs 基线 | depth / world_points / extrinsic / intrinsic 四字段逐位一致（max_abs_diff = 0） |
| M2-AI-010 | `test_m2_ai_010_default_threshold_metrics_available` | `vggt_output/001_watercup`（conf=3.0） | 期望四项指标可统计 —— **当前失败**，复现 DEF-M2-003 |
| M2-AI-011 | `test_m2_ai_011_loose_threshold_shows_degradation` | `001_watercup`（conf=1.0） | 指标可统计但显著劣化：G1 > 5×基线、G2 > 10 px、G4 NCC < 0.70 |
| M2-AI-012 | `test_m2_ai_012_square_padding_does_not_improve` | `exp/sq4096` | 补白成正方形后 G1 改善 < 20%（否证「裁切是主因」假说），关联 DEF-M2-002 |
| M2-AI-013 | `test_m2_ai_013_empty_input_directory` | 现场调用推理脚本 | 退出码非 0、提示「输入目录中没有图像」、不创建输出目录 |
| M2-AI-014 | `test_m2_ai_014_missing_input_directory` | 现场调用推理脚本 | 退出码非 0、提示「输入目录不存在」 |
| M2-AI-015 | `test_m2_ai_015_damaged_image_friendly_error` | 现场调用推理脚本（需 CUDA+权重） | 期望：中文友好报错且不残留半成品 —— **当前失败**，复现 DEF-M2-001 |

### 为什么有 2 条用例「预期失败」

M2-AI-010 与 M2-AI-015 在用例清单中的判定即为 **NG**，它们是模块二的有效缺陷入口：

* **M2-AI-010 → DEF-M2-003**：低置信场景下 `--conf-thres` 静默失效。
  近景特写场景的深度置信最大值仅 2.187，低于默认阈值 3.0，
  导致 G1/G2/G4 因「有效像素为 0」被跳过，而程序不给出任何降级提示。
* **M2-AI-015 → DEF-M2-001**：损坏图像的异常处理不一致。
  抛出未捕获的 `PIL.UnidentifiedImageError` 原始堆栈，
  并在输出目录残留 `images/`（半成品产物）。

修复这两条缺陷后，本套脚本无需改动即可转为全绿：

```powershell
.\run_tests.ps1          # 期望：15 项执行、15 通过、退出码 0
```

---

## 6 数据与产物

### 6.1 测试读取的数据

| 路径 | 内容 | 用途 |
| --- | --- | --- |
| `vggt_output/002_computer/` | 9 帧基线产物（predictions.npz、depth/、GLB、run_info.json） | 001/002/003/005/006/007/008/009 的对照基准 |
| `vggt_output/001_watercup/` | 8 帧竖构图场景产物 | 010/011/012 |
| `vggt_output/exp/N1|N2|N5|res50|noise10|occ25|det2/` | 帧数与扰动变体 | 002~009 |
| `vggt_output/exp/sq4096/` | 竖构图补白成正方形的变体 | 012 |

`exp/` 下产物缺失时由 `m2_tests/common.py` **按需生成**（复用
`tools/robustness_experiments.py` 的变体生成与推理封装），生成过程与
`tools/robustness_experiments.py` 全量批跑一致，随机种子固定为 20260911。

### 6.2 测试自身的产物

| 路径 | 内容 |
| --- | --- |
| `test_results/module2/run_<时间戳>.log` | UTF-8 运行日志（含逐条用例结果） |
| `test_results/module2/run_<时间戳>.xml` | JUnit XML（tests / failures / errors / skipped） |
| `test_results/module2/run_all_<时间戳>.txt\|.json\|.csv` | `run_all_cases.py` 的汇总归档（人读 / 机读 / 可贴表） |
| `test_results/module2/case_list_preview.txt` | `run_all_cases.py --list` 的清单预览（只读模式产物） |
| `test_results/module2/tmp/` | 013~015 的临时输入输出目录（失败现场保留供排查） |

### 6.3 指标口径

测试**不读取历史 `metrics.json`**，而是直接调用 `metrics.compute_all()` 对
当前磁盘上的 `predictions.npz` 现场计算 G1–G4，保证断言针对「当前产物」。
同一 `(npz, 阈值)` 在一次运行内只计算一次（进程内缓存），因此多条用例共享
基准指标时不会重复耗时。

G1 相对误差以场景尺度（高置信点云包围盒对角线）归一化，因此可跨场景比较；
G4 光度一致性在单帧输入下无有效帧对，按设计报告「不可用」。

---

## 7 常见问题

**Q：没有 GPU，能跑吗？**
A：可以。用 `.\run_tests.ps1 -Prepare:$false`，依赖新推理的用例会标记 skipped，
基线断言（001/010/011）与输入校验（013/014）正常执行。

**Q：一键运行要多久？**
A：数据齐全时约 1–3 分钟（主要是 9 帧 npz 的指标计算）；需要现场生成
`exp/` 变体时额外约 6–10 分钟（7 次 GPU 推理 + 补白变体）。

**Q：为什么 M2-AI-010 / M2-AI-015 失败？**
A：这正是本套脚本要暴露的缺陷（DEF-M2-003 / DEF-M2-001）。参见第 5 节末尾。

**Q：能否在 CI 里用？**
A：可以。`run_tests.ps1` 的退出码与 JUnit XML 可直接被 CI 消费；
无 GPU 的 CI 建议加 `-Prepare:$false`。

**Q：中文用例名在日志里乱码怎么办？**
A：日志由 `m2_tests/junit_report.py` 以 UTF-8 直接写盘（不经过 PowerShell
的码页解码），不会出现双重编码；若用 `>` 重定向控制台输出则仍可能乱码，
请以归档 `.log` 为准。
