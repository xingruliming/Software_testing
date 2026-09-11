# test_results/module2/ — 模块二测试证据

本目录保存模块二（AI 融合实践 · 方案 1「测 AI」）在执行测试过程中产生的**缺陷复现记录**。

## 文件说明

| 文件 | 对应缺陷 | 内容 |
|---|---|---|
| `DEF-M2-001_reproduction.txt` | DEF-M2-001 | 损坏图像文件导致未捕获 `PIL.UnidentifiedImageError`，异常处理不一致且残留半成品产物；定位 `vggt-main/vggt/utils/load_fn.py:140` |
| `DEF-M2-002_reproduction.txt` | DEF-M2-002 | `load_and_preprocess_images(mode="crop")` 对非 1:1 输入静默裁切，竖构图纵向视野丢弃 24.5%；含裁切量核算与补白对照实验 |
| `README.md` | — | 本说明 |

## 与实验室产物的对应关系

复现记录是**归档摘要**，原始现场与批量实验产物在 `vggt_output/` 下，两者互相引用：

| 位置 | 内容 |
|---|---|
| `vggt_output/exp/` | 帧数与扰动变体的批量实验产物（7 次推理），含 `summary.json` / `summary.md` 汇总 |
| `vggt_output/exp/_abnormal/` | 异常输入用例的失败现场与 `inference.log`（空目录、目录不存在、损坏 jpg） |
| `vggt_output/exp/sq001/` | DEF-M2-002 的补白对照实验产物 |
| `vggt_output/002_computer/`、`vggt_output/001_watercup/` | 基准场景与跨场景对照的推理产物与 `metrics.json` |
| `vggt_output/*_run.log` | 各场景的运行日志 |

## 可复现性

两个缺陷均为**已复现**状态，复现步骤见各记录文件；复现过程未修改 `vggt-main/` 中任何源文件
（符合「被测基线默认不修改」的项目约定）。

复现依赖：`Pytorch_Vggt` 环境、模型权重 `E:\0_work\1shijian\model.pt`（约 5.02 GB，不纳入 Git）、
`vggt_input/` 下的输入图像。指标计算（`metrics.py`）为离线纯 NumPy 计算，不需要 GPU。
