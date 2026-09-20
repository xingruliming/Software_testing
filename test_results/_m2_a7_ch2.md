### 2.1 运行条件与相关配置

- 操作系统：Windows 10/11，PowerShell 5.1 及以上（兼容 pwsh）；
- 硬件要求：NVIDIA GPU（CUDA 12.8）与模型权重 model.pt（约 5.02 GB，位于工程上一级目录）；9 帧推理峰值显存约 8.5 GB；
- 解释器探测顺序（run_tests.ps1 内置，命中即用）：命令行参数 -PythonExecutable → vggt-main\.venv → 工程根 .venv → D:\anaconda3\envs\Pytorch_Vggt\python.exe → 系统 PATH；
- 环境变量：脚本自动注入 PYTHONPATH（工程根 + vggt-main）与 M2_PYTHON（供测试内部调用子进程推理）；
- 数据就绪策略：M2_PREPARE=1（默认）时，缺失的 GPU 推理产物由 m2_tests/common.py 按需调用 run_vggt_inference.py 生成并缓存复用；用 -Prepare:$false 关闭自动生成，相关用例会被标记为「跳过」并给出生成办法；
- 归档配置：默认每次运行在 test_results/module2/ 生成 run_时间戳.log（UTF-8 文本）与同名 .xml（JUnit）；传 -NoLog 关闭归档；
- 用例匹配：-TestPattern 参数控制 unittest discover 的匹配模式，默认 test_m2_ai*.py。

### 2.2 测试脚本清单（功能与测试目的）

| 脚本 / 文件 | 功能与测试目的 |
| --- | --- |
| 一键运行模块二测试.bat | 双击入口：设置控制台 UTF-8 编码、查找本机 PowerShell、转发 run_tests.ps1 的退出码（0=全部通过、1=有失败或错误、2=测试工程不完整、3=无法导入被测模块） |
| run_tests.ps1 | 测试驱动：探测解释器与工程完整性、注入导入路径、执行 m2_tests 下全部用例、归档 JUnit XML 与 UTF-8 日志并打印统计摘要 |
| m2_tests/common.py | 公共设施：产物路径定位、直接调用 metrics.py 复算 G1–G4（带进程内缓存）、按需生成缺失的 GPU 推理产物、封装推理脚本的子进程调用 |
| m2_tests/junit_report.py | 运行期钩子：单次执行同时产出 JUnit XML（可供 CI 解析）与 UTF-8 文本日志，避免中文用例名被控制台码页二次编码 |
| m2_tests/test_m2_ai_001_005_frame_effect.py | 用例 M2-AI-001~005：基准场景四项指标与产物完整性、5 帧/2 帧自洽性退化、单帧 G4 不可用、帧数—指标单调性 |
| m2_tests/test_m2_ai_006_009_robustness.py | 用例 M2-AI-006~009：0.5 倍分辨率、高斯噪声 σ=10、遮挡 25% 面积的鲁棒性，以及重复运行逐位一致性 |
| m2_tests/test_m2_ai_010_012_scene_dependency.py | 用例 M2-AI-010~012：低置信竖构图场景在默认阈值下的可用性、阈值下探测量、补白正方形对照实验 |
| m2_tests/test_m2_ai_013_015_input_validation.py | 用例 M2-AI-013~015：以子进程真实调用推理入口，断言空目录/目录不存在/损坏图像三类输入的报错信息、退出码与残留产物 |
| tools/robustness_experiments.py | 数据准备：按固定随机种子（20260911）生成 7 个扰动变体，批量推理并计算指标，汇总为 vggt_output/exp/summary.json 与 summary.md |
| tools/m2_req_build.py、tools/_m2_req_check.py | 辅助脚本：模块二软件需求清单的生成与行高复核（不在测试执行链路上） |

### 2.3 账户与密码

本模块测试全部在本地执行，不访问网络服务，不涉及任何账户、密码或令牌。
