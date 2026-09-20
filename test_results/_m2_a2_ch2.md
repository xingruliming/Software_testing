### 2.1 运行环境与必备软件

- 操作系统：Windows 10/11（驱动脚本为 PowerShell 编写；macOS / Linux 用户可参考 2.5 节的手动命令，将路径分隔符换成 /）；
- Python：3.10（实测 Anaconda 环境 Pytorch_Vggt，解释器 D:\anaconda3\envs\Pytorch_Vggt\python.exe）；
- 必备依赖：PyTorch 2.8.0+cu128（CUDA 12.8）、numpy、Pillow；测试框架为 Python 标准库 unittest，无需额外安装；
- 模型权重：model.pt（约 5.02 GB，位于工程目录的上一级），仅推理类用例需要；
- 硬件：NVIDIA GPU；8 GB 显存实测可支持 9 帧推理（峰值约 8.5 GB）。

### 2.2 一键运行全部用例（推荐）

在 deliverables/module2 目录下双击「一键运行模块二测试.bat」，或在终端执行：

.\run_tests.ps1

程序按用例编号顺序自动执行全部 15 条用例（M2-AI-001 → M2-AI-015），单次运行同时产出 JUnit XML 与 UTF-8 日志并归档到 test_results/module2/。退出码含义：0=全部通过、1=有失败或错误、2=测试工程不完整、3=无法导入被测模块。

### 2.3 按用例编号顺序输入用例（分组 / 单条运行）

用例按编号分段放在四个测试文件中，测试发现按文件名排序，因此执行顺序与用例编号天然一致：

| 用例段 | 测试文件 |
| --- | --- |
| M2-AI-001 ~ 005 | m2_tests/test_m2_ai_001_005_frame_effect.py |
| M2-AI-006 ~ 009 | m2_tests/test_m2_ai_006_009_robustness.py |
| M2-AI-010 ~ 012 | m2_tests/test_m2_ai_010_012_scene_dependency.py |
| M2-AI-013 ~ 015 | m2_tests/test_m2_ai_013_015_input_validation.py |

只跑某一段（用 -TestPattern 指定文件模式）：

.\run_tests.ps1 -TestPattern "test_m2_ai_013_015*.py"

单独输入某一条用例（在 deliverables/module2 目录下执行；PYTHONPATH 需包含工程根与 vggt-main，一键脚本已自动注入）：

python -m unittest m2_tests.test_m2_ai_010_012_scene_dependency.TestSceneDependency.test_m2_ai_010_default_threshold_metrics_available -v

常用单条用例的完整路径示例：

- M2-AI-005（帧数—指标单调性）：m2_tests.test_m2_ai_001_005_frame_effect.TestFrameEffect.test_m2_ai_005_monotonic_improvement_with_frames
- M2-AI-009（重复运行确定性）：m2_tests.test_m2_ai_006_009_robustness.TestRobustness.test_m2_ai_009_determinism_bitwise_identical
- M2-AI-013（空输入目录）：m2_tests.test_m2_ai_013_015_input_validation.TestInputValidation.test_m2_ai_013_empty_input_directory
- M2-AI-015（损坏图像）：m2_tests.test_m2_ai_013_015_input_validation.TestInputValidation.test_m2_ai_015_damaged_image_friendly_error

### 2.4 运行模式与数据准备

- 默认模式（-Prepare:$true）：若缺少帧数、扰动变体或补白变体的 GPU 推理产物，程序会自动调用 run_vggt_inference.py 现场生成并缓存复用（首次约 6~10 分钟，之后直接复用）；
- 无 GPU 模式（-Prepare:$false）：不生成新产物，依赖新推理的用例会被标记为「跳过」，其余用例照常执行；
- 单独准备全部实验数据（可选，需要 GPU）：

python tools/robustness_experiments.py

### 2.5 底层程序单独运行（可选）

批量推理（输入图像目录 → 深度图 + npz + GLB）：

python run_vggt_inference.py --input-dir vggt_input/002_computer --output-dir vggt_output/002_computer

（--prediction-modes 留空则只出深度图与预测结果、不导出 GLB；--conf-thres 控制 GLB 点云的置信度过滤百分比；--from-npz 可复用已有 predictions.npz 只重出深度图与 GLB）

指标计算（不需要 GPU，可直接作用于已归档产物）：

python metrics.py vggt_output/002_computer/predictions.npz --conf-thres 3.0 --json vggt_output/002_computer/metrics.json

### 2.6 账户与密码

本程序全部在本地运行，不访问网络服务，不涉及任何账户、密码或令牌。
