**A 线最近一次一键执行（2026-09-15 19:42，conda 环境 Pytorch_Vggt）**

- 执行 33 条用例、耗时 0.101 秒：31 条通过，2 条错误（M1-GEO-016/018 触发未修复缺陷 DEF-M1-001 的 ValueError），退出码 1，符合预期；
- 控制台逐条输出进度（. 表示通过、E 表示错误），失败用例附完整调用栈，可定位至 geometry.py 具体行号；
- 归档产物：test_results\module1\run_20260915_194243.log（文本日志）与 run_20260915_194243.xml（JUnit，tests=33、errors=2）。

**B 线存档结果（2026-09-11，迁移前布局）**

- 15 条图像预处理用例全部通过；
- DEF-IMG-001/002/003 三个缺陷的复现与修复验证各 9/9 通过，记录存档于 deliverables\image_test_module1\defect_tests\results\。

如需界面证据，可在 PowerShell 窗口运行一键命令后截图控制台输出（含统计行 Ran 33 tests 与 FAILED (errors=2)），并打开归档 .log 文件截图关键片段。
