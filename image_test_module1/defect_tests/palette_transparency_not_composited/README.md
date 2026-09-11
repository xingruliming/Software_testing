# DEF-IMG-003 调色板 PNG 透明区域未正确合成

## 缺陷现象

两个函数只在 `img.mode == "RGBA"` 时执行白色背景合成。带 `transparency` 信息的 `P` 模式 PNG 同样具有透明像素，但代码直接调用 `convert("RGB")`，透明区域因此变成调色板中的红色，而不是白色。

## 复现输入与步骤

1. 运行 `generate_input.py`，生成全透明红色索引的 P 模式 PNG，以及全透明 RGBA 对照 PNG。
2. 分别调用 `load_and_preprocess_images()`，比较透明区域的输出像素。
3. 调用 `load_and_preprocess_images_square()` 处理 P 模式 PNG。
4. 运行 `run_defect_test.ps1` 保存完整输出。

## 预期与实际

- RGBA 对照输入被合成到白色背景，当前通过。
- P 模式全透明输入也应输出全白张量；实际输出为红色张量。
- 标准函数与 square 函数均受影响。

## 修复及验证标准

不要只判断 `RGBA`；应通过 `img.getbands()` 或 `img.info.get("transparency")` 识别透明度，并先转换为 RGBA、合成到白色背景，再转换为 RGB。修复后本目录 3 条检查应全部通过，并重新执行原有 15 条回归测试。

```powershell
.\tests\defect_tests\palette_transparency_not_composited\run_defect_test.ps1
```
