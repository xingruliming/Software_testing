# VGGT 缺陷复现测试

本目录保存已经确认的软件缺陷及其独立复现工程。缺陷测试与 `tests` 下原有的 15 条常规自动化用例分开，避免一键执行正常回归测试时被“预期失败”的缺陷用例干扰。

当前已确认 3 个有效缺陷：

- `load_and_preprocess_images_extreme_ratio/`：复现 `load_and_preprocess_images()` 处理极端宽高比图片时把缩放高度计算为 0 的问题。
- `exif_orientation_not_applied/`：复现两个图像预处理函数未应用 JPEG EXIF 方向，导致图像方向、输出形状及原图坐标错误的问题。
- `palette_transparency_not_composited/`：复现两个函数未把带透明索引的调色板 PNG 合成到白色背景，透明区域被错误保留为调色板颜色的问题。

每个缺陷目录包含输入数据、复现代码、一键运行脚本、执行结果和中文说明。

## 一键复现全部缺陷

在项目根目录运行：

```powershell
.\tests\defect_tests\run_all_defect_tests.ps1
```

脚本会依次运行 3 个缺陷目录中的 9 条检查，并把汇总证据写入 `results/all_defects_reproduction.txt`。修复前预期为 3 条对照检查通过、6 条期望行为检查失败。
