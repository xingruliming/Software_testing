**1.1 被测程序（vggt-main 目录，测试期间未做任何修改）**

- vggt-main\vggt\utils\geometry.py：A 线（坐标转换）被测模块，324 行共 8 个函数，覆盖深度图→三维点图反投影、深度图→相机/世界坐标点、SE3 变换求逆、世界点批量投影、像素↔相机坐标转换等接口；
- vggt-main\vggt\utils\load_fn.py：B 线（图像预处理）被测模块，核心函数 load_and_preprocess_images 负责图像读取、色彩空间转换、长宽比调整与 518×518 尺寸归一化；
- 模块一为函数级测试：不加载模型权重 model.pt，不执行完整重建流程，无需 GPU。

**1.2 测试工程（Software_testing 目录）**

- 双击运行模块一测试.bat / run_tests.ps1：A 线一键运行入口（Windows）；
- tests\module1_coordinate\：A 线自动化用例 33 条，按功能分 8 个 test_m1_geo_*.py 文件，docstring 内标注用例编号；
- tests\junit_report.py：运行期钩子，单次执行同时产出 JUnit XML 与 UTF-8 文本日志；
- deliverables\image_test_module1\：B 线（图像预处理）测试包，含 15 条用例（load_and_preprocess_images 与 load_and_preprocess_images_square 两个子包）、defect_tests\（3 个缺陷的复现与修复验证脚本）、input\（版本化图像夹具）；
- test_results\module1\：A 线执行结果归档（run_时间戳.log 与同名 .xml）；
- tools\：测试辅助脚本（推理驱动、指标计算、结果可视化等）。
