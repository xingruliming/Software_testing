### 2.1 环境要求

- 操作系统：Windows 10/11（脚本基于 PowerShell 编写；macOS/Linux 可参考 2.4 节手动命令，将路径分隔符替换为 /）；
- Python 3.10 及以上 + PyTorch（本机实测：conda 环境 Pytorch_Vggt，Python 3.10.20、torch 2.8.0+cu128）；
- 第三方依赖：numpy、Pillow（PIL）；
- 无需 GPU、无需模型权重。

### 2.2 A 线一键运行（推荐）

1. 双击工程根目录下的「双击运行模块一测试.bat」；或在 PowerShell 中执行 `powershell -ExecutionPolicy Bypass -File run_tests.ps1`；
2. 可选参数：-PythonExecutable 指定解释器路径；-TestPattern 指定用例文件匹配模式（默认 test_m1_geo*.py）；-NoLog 关闭结果归档；
3. 脚本自动按以下顺序探测 Python 解释器（命中即用）：命令行显式指定 → vggt-main\.venv\Scripts\python.exe → 项目 .venv → D:\anaconda3\envs\Pytorch_Vggt\python.exe → PATH。

退出码含义：

| 退出码 | 含义 |
| --- | --- |
| 0 | 全部用例通过 |
| 1 | 存在未通过用例 |
| 2 | 测试工程目录缺失 |
| 3 | 被测模块无法导入（请检查 vggt-main 是否位于工程根目录） |

执行结果归档至 test_results\module1\run_时间戳.log（UTF-8 文本日志）与同名 .xml（JUnit 格式）。

当前预期结果：33 条用例执行、31 条通过；M1-GEO-016 与 M1-GEO-018 失败（ValueError），对应已报告、按课程约定未修复的缺陷 DEF-M1-001（geometry.py 第 39 行无条件 squeeze），属预期现象而非环境问题。

### 2.3 B 线运行说明（image_test_module1，目录迁移后暂不可直接运行）

B 线脚本按旧目录布局（tests 包结构）编写。2026-09-11 在原布局下验证：15 条用例全部通过，3 个缺陷（DEF-IMG-001/002/003）复现与修复验证 9/9 通过。2026-09-14 测试工程整体迁移至 deliverables\image_test_module1\ 后，脚本内部的相对路径与包名仍指向旧布局，当前布局下直接运行会失败：

- 运行 run_tests.ps1 报错「未找到项目 Python 环境」：脚本按旧布局上溯查找 .venv；
- 手动执行 unittest discover 报 ModuleNotFoundError: No module named 'tests'：测试文件导入 from tests.common 依赖旧包结构。

迁移前的设计用法（恢复布局后可参考）：

- 15 条用例：进入 image_test_module1 目录执行 run_tests.ps1；
- 缺陷验证：执行 defect_tests\run_all_defect_tests.ps1（自动生成边界输入、执行 9 项检查，汇总写入 defect_tests\results\all_defects_fix_verification.txt）；
- 单个缺陷验证：执行 defect_tests\〈缺陷目录〉\run_defect_test.ps1。

恢复方法（三选一）：① 将该目录挂回 tests 包布局后运行；② 将脚本与测试文件中的包名、相对路径改为当前布局；③ 增设 tests 兼容包。迁移前的完整执行记录已存档于 defect_tests\results\（复现与修复验证各 9/9 通过，2026-09-11）。

### 2.4 手动运行单个用例（A 线）

在工程根目录、PYTHONPATH 包含 vggt-main 的前提下执行：

`python -m unittest tests.module1_coordinate.test_m1_geo_016_019_unproject -v`
