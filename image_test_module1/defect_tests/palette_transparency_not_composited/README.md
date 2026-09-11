# DEF-IMG-003 调色板 PNG 透明区域未正确合成（已修复并复测通过）

## 缺陷现象

两个函数只在 `img.mode == "RGBA"` 时执行白色背景合成。带 `transparency` 信息的 `P` 模式 PNG 同样具有透明像素，但代码直接调用 `convert("RGB")`，透明区域因此变成调色板中的红色，而不是白色。

## 复现输入与步骤

1. 运行 `generate_input.py`，生成全透明红色索引的 P 模式 PNG，以及全透明 RGBA 对照 PNG。
2. 分别调用 `load_and_preprocess_images()`，比较透明区域的输出像素。
3. 调用 `load_and_preprocess_images_square()` 处理 P 模式 PNG。
4. 运行 `run_defect_test.ps1` 保存完整输出。

## 修复前结果

- RGBA 对照输入被合成到白色背景，当前通过。
- P 模式全透明输入也应输出全白张量；实际输出为红色张量。
- 标准函数与 square 函数均受影响。

## 修复方案与验证结果

已统一识别带 alpha 通道的图片，以及包含 `transparency` 信息的 P 模式 PNG。透明图片先转换为 RGBA、合成到白色背景，再转换为 RGB；两个公开加载函数共用同一处理步骤。

- 本目录 3 条专项检查全部通过；
- RGBA 对照输入仍输出全白张量；
- P 模式透明 PNG 在标准函数和 square 函数中均输出全白张量；
- 原有 15 条常规回归测试全部通过。

修复前证据保留在 `results/DEF-IMG-003_reproduction.txt`，修复后证据保存至 `results/DEF-IMG-003_fix_verification.txt`。

```powershell
.\tests\defect_tests\palette_transparency_not_composited\run_defect_test.ps1
```
