本项目模块二采用 Python 标准库 unittest 作为自动化测试框架，测试脚本以「单元测试套件 + 一键运行驱动脚本」的形式组织，全部工具均随 Python 环境自带或经 conda/pip 安装，无独立下载地址。

- 测试框架：unittest（Python 3.10.20 标准库内置，版本随解释器）；
- 被测软件：VGGT（vggt-main/ 官方基线，测试期间未修改）与自建批量推理入口 run_vggt_inference.py；
- 运行时环境：Python 3.10.20 + PyTorch 2.8.0+cu128（conda 环境 Pytorch_Vggt）；
- 第三方依赖：numpy（数组与指标计算）、Pillow（图像构造与读取）、torch（推理链路）；
- 一键入口：一键运行模块二测试.bat（Windows 批处理）→ run_tests.ps1（PowerShell 5.1+）；
- 结果工具：m2_tests/junit_report.py（unittest 运行期钩子，单次运行同时产出 JUnit XML 与 UTF-8 日志）；
- 数据准备工具：tools/robustness_experiments.py（生成帧数与扰动变体、批量推理并计算指标）。

说明：本模块为接口级功能测试（对模型输出与推理入口的行为做断言），不涉及 GUI 自动化，故本文档仅覆盖功能测试脚本的运行配置。
