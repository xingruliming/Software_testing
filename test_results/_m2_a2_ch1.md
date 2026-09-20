模块二的测试程序由「被测软件 + 自建测试工具链」两部分构成，全部为命令行程序，可通过参数顺序输入用例、逐个或批量执行，无界面依赖。

**1.1 被测软件（vggt-main 目录，测试期间未做任何修改）**

- vggt-main/vggt/utils/load_fn.py：图像加载与预处理模块。核心函数 load_and_preprocess_images 负责读取图像、转 RGB、按 crop / pad 模式缩放至宽 518 且高按 14 像素对齐；
- vggt-main/visual_util.py：点云导出与后处理模块。核心函数 predictions_to_glb 负责置信度过滤、背景剔除与预测分支选择，并导出 GLB 场景；
- vggt-main/vggt/models/vggt.py 与 vggt/heads/：模型本体与四个预测头（深度头、点图头、相机头、跟踪头）。

**1.2 自建测试程序（工程根目录与交付目录）**

- run_vggt_inference.py（389 行）：无界面批量推理入口。输入图像目录 → 输出逐帧深度图、predictions.npz、两个预测分支的 GLB 与 run_info.json；内置输入目录校验与中文报错；
- metrics.py（476 行）：无真值几何自洽性指标计算（G1 点图与深度反投影一致性、G2 点图与相机头一致性、G3 置信度分布、G4 相邻帧光度一致性）；纯 NumPy 实现，不需要 GPU，可直接对已归档的 predictions.npz 复算；
- cv2_unicode.py（123 行）：OpenCV 中文路径兼容层；
- tools/robustness_experiments.py（247 行）：帧数与扰动矩阵批量实验驱动，一次完成「生成变体输入 → 批量推理 → 计算指标 → 汇总」；
- deliverables/module2/m2_tests/（899 行）：15 条用例的单元测试实现（unittest 框架，按用例编号分段组织）；
- deliverables/module2/run_tests.ps1 与「一键运行模块二测试.bat」：测试一键入口（探测解释器、注入导入路径、顺序执行并归档结果）。

**1.3 目录与产物结构**

- vggt_input/〈场景〉/：输入图像目录（002_computer 9 帧横构图、001_watercup 8 帧竖构图等）；
- vggt_output/〈场景〉/：推理产物（depth/ 逐帧伪彩色深度图、predictions.npz、GLB、run_info.json）；
- vggt_output/exp/〈变体〉/：帧数与扰动变体的推理产物（N1 / N2 / N5 / res50 / noise10 / occ25 / det2 等）；
- test_results/module2/：测试运行归档（run_时间戳.log 与同名 .xml）及临时输入输出目录。
