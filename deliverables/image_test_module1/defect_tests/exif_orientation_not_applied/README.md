# DEF-IMG-002 JPEG EXIF 方向未应用（已修复并复测通过）

## 缺陷现象

两个图像预处理函数使用 `Image.open()` 后直接读取尺寸并缩放，没有执行 `ImageOps.exif_transpose()`。相机 JPEG 使用 EXIF Orientation 标记旋转方向时，函数仍按文件存储方向处理，造成输出形状、图像方向及 `original_coords` 坐标错误。

## 复现输入与步骤

1. 运行 `generate_input.py`，生成无 EXIF 的 `40×20` 对照图和存储尺寸为 `40×20`、Orientation=6 的 JPEG。
2. 用 `load_and_preprocess_images(..., mode="crop")` 处理两张图。
3. 用 `load_and_preprocess_images_square(..., target_size=140)` 处理 EXIF 图片并检查坐标。
4. 运行 `run_defect_test.ps1` 保存完整输出。

## 修复前结果

- 对照图应保持横向并返回 `(1,3,252,518)`，当前通过。
- Orientation=6 图片显示尺寸应为 `20×40`，标准函数应按竖向图处理并返回 `(1,3,518,518)`；实际仍返回 `(1,3,252,518)`。
- square 函数预期坐标为 `[35,0,105,140,20,40]`；实际按存储方向得到 `[0,35,140,105,40,20]`。

## 修复方案与验证结果

已在两个公开加载函数共用的内部预处理步骤中执行 `ImageOps.exif_transpose(img)`，并确保方向修正发生在尺寸读取、缩放和坐标计算之前。

- 本目录 3 条专项检查全部通过；
- Orientation=6 图片按显示尺寸 `20×40` 处理；
- 标准函数返回 `(1,3,518,518)`；
- square 函数坐标为 `[35,0,105,140,20,40]`；
- 原有 15 条常规回归测试全部通过。

修复前证据保留在 `results/DEF-IMG-002_reproduction.txt`，修复后证据保存至 `results/DEF-IMG-002_fix_verification.txt`。

```powershell
.\tests\defect_tests\exif_orientation_not_applied\run_defect_test.ps1
```
