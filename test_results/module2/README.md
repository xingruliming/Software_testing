# test_results/module2/ — 模块二测试证据

本目录保存模块二（AI 融合实践 · 方案 1「测 AI」）在执行测试过程中产生的**缺陷复现记录**。

## 文件说明

| 文件 | 对应缺陷 | 内容 |
|---|---|---|
| `DEF-M2-001_reproduction.txt` | DEF-M2-001 | 损坏图像文件导致未捕获 `PIL.UnidentifiedImageError`，异常处理不一致且残留半成品产物；定位 `vggt-main/vggt/utils/load_fn.py:140` |
| `DEF-M2-002_reproduction.txt` | DEF-M2-002 | `load_and_preprocess_images(mode="crop")` 对非 1:1 输入静默裁切，竖构图纵向视野丢弃 24.5%；含裁切量核算与补白对照实验 |
| `DEF-M2-003_reproduction.txt` | DEF-M2-003 | 低置信场景下置信度过滤（`--conf-thres`）静默失效：置信度地板值 1.0 占比过高时中位数即 1.0，过滤率变为 0% 且无告警；4 个场景实测（含 009_arbus 保留率 100.00%） |
| `DEF-M2-004_reproduction.txt` | DEF-M2-004 | 输出未区分目标与背景；内置背景剔除仅支持颜色阈值，抗锯齿边缘残留 79,958 点（占保留点 14.05%）；含阈值扫描与工程内替代方案 |
| `DEF-M2-005_reproduction.txt` | DEF-M2-005 | OpenCV 4.13.0 在非 ASCII（中文）路径下静默写失败，`cv2.imwrite` **返回 True 却未写出文件**（连续 5 次复现），返回值不可信 |
| `README.md` | — | 本说明 |

## 测试工具自身缺陷（不计入被测软件缺陷数）

| 编号 | 位置 | 缺陷 |
|---|---|---|
| T-M2-001 | `run_aircraft_batch.py::relative_pose_metrics` | 相对旋转用 c2w 构造，不是规范不变量，误差被全局坐标系旋转污染（虚高至 40~107°，修正后 0.38~0.59°） |
| T-M2-002 | 同上 | 相对平移未按尺度对齐，凭空多出约 75% 误差（修正后 0.89~2.79%） |
| T-M2-003 | 同上 | 真值配对错误：散点抽样下误用 `gt_w2c[:n]`，应写 `[gt_w2c[i] for i in sel]` |

自检脚本（均不需 GPU）：`tools/verify_pose_metric.py`、`tools/verify_translation_metric.py`、
`tools/diag_arbus_convention.py`、`tools/diag_arbus_pose.py`。

## 与实验室产物的对应关系

复现记录是**归档摘要**，原始现场与批量实验产物在 `vggt_output/` 下，两者互相引用：

| 位置 | 内容 |
|---|---|
| `vggt_output/exp/` | 帧数与扰动变体的批量实验产物（7 次推理），含 `summary.json` / `summary.md` 汇总 |
| `vggt_output/exp/_abnormal/` | 异常输入用例的失败现场与 `inference.log`（空目录、目录不存在、损坏 jpg） |
| `vggt_output/exp/sq001/` | DEF-M2-002 的补白对照实验产物 |
| `vggt_output/002_computer/`、`vggt_output/001_watercup/` | 基准场景与跨场景对照的推理产物与 `metrics.json` |
| `vggt_output/009_arbus_sweep/` | 帧数扫描（N=1/2/4/8/16/32）产物；含各档 `metrics_gt.json`、DEF-M2-003/004 的 `aircraft_only/` 与 `Nxx_whitebg/`、三方案对比图 `_background_filter_compare.png` |
| `vggt_output/*_run.log` | 各场景的运行日志 |

## 可复现性

五个缺陷均为**已复现**状态，复现步骤见各记录文件；复现过程未修改 `vggt-main/` 中任何源文件
（符合「被测基线默认不修改」的项目约定）。

注意 DEF-M2-005（OpenCV 中文路径）需要**人为构造含中文的路径**才能触发 ——
当前工作副本路径已是纯 ASCII，不会再被仓库路径自动触发，验证时勿误判为「已修复」。

复现依赖：`Pytorch_Vggt` 环境、模型权重 `E:\0_work\1shijian\model.pt`（约 5.02 GB，不纳入 Git）、
`vggt_input/` 下的输入图像。指标计算（`metrics.py`）为离线纯 NumPy 计算，不需要 GPU。
