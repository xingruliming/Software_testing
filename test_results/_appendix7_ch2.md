### 2.1 运行条件与相关配置

- 操作系统：Windows 10/11，PowerShell 5.1 及以上（兼容 pwsh）；macOS/Linux 可参考附录2 第 2.4 节的手动命令；
- 解释器探测顺序（run_tests.ps1 内置，命中即用）：命令行参数 -PythonExecutable 显式指定 → vggt-main\.venv\Scripts\python.exe → 项目 .venv → D:\anaconda3\envs\Pytorch_Vggt\python.exe → 系统 PATH；
- 环境变量：脚本自动将 vggt-main 注入 PYTHONPATH 使被测模块可导入，不修改被测基线源码；
- 归档配置：默认每次运行在 test_results\module1\ 生成 run_时间戳.log（UTF-8 文本）与同名 .xml（JUnit）；传 -NoLog 关闭归档；
- 用例匹配：-TestPattern 参数控制 unittest discover 的文件匹配模式，默认 test_m1_geo*.py。

### 2.2 测试脚本清单（功能与测试目的）

| 脚本 / 文件 | 功能与测试目的 |
| --- | --- |
| 双击运行模块一测试.bat | A 线一键入口：设置控制台 UTF-8 编码、查找本机 PowerShell、转发退出码（0=全部通过、1=有失败、2=测试工程缺失、3=无法导入被测模块） |
| run_tests.ps1 | A 线测试驱动：前置检查被测文件存在性与模块可导入性，unittest discover 执行 33 条用例，调用 junit_report 归档结果 |
| tests\junit_report.py | 运行期钩子：单次执行同时产出 JUnit XML（可供 CI 解析）与 UTF-8 文本日志 |
| tests\module1_coordinate\test_m1_geo_001_005 至 _030_032（共 8 个文件） | M1-GEO-001~032 用例实现：深度图转相机/世界坐标、SE3 变换求逆、深度反投影、世界点批量投影、img_from_cam、project_to_cam、cam_from_img 等接口的功能、边界与异常测试 |
| deliverables\image_test_module1\run_tests.ps1 | B 线测试驱动（15 条图像预处理用例）；目录迁移后暂不可直接运行，详见附录2 第 2.3 节 |
| deliverables\image_test_module1\defect_tests\run_all_defect_tests.ps1 及各缺陷目录下的 run_defect_test.ps1 | B 线缺陷复现与修复验证脚本（DEF-IMG-001/002/003，各含复现与修复验证两类检查）；同上，需恢复旧布局后运行 |

### 2.3 账户与密码

本模块测试全部在本地执行，不访问网络服务，不涉及任何账户、密码或令牌。
