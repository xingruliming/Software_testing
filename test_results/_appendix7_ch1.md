本项目模块一采用 Python 标准库 unittest 作为自动化测试框架，配合 PowerShell 脚本实现一键运行；全部工具均随 Python 环境自带或经 conda/pip 安装，无独立下载地址。

- 测试框架：unittest（Python 3.10.20 标准库内置，版本随解释器）；
- 运行时环境：Python 3.10.20 + PyTorch 2.8.0+cu128（conda 环境 Pytorch_Vggt）；
- 第三方依赖：numpy（数组运算）、Pillow（图像构造与读取，B 线使用）；
- 一键入口：双击运行模块一测试.bat（Windows 批处理）→ run_tests.ps1（PowerShell 5.1+）；
- 结果工具：tests\junit_report.py（unittest 运行期钩子，产出 JUnit XML 与 UTF-8 日志）。

说明：本模块测试为接口级功能测试（直接调用被测函数并断言返回值），不涉及 GUI 自动化，故本文档仅覆盖功能测试脚本的运行配置。
