# VGGT 缺陷修复验证测试

本目录保存 3 个已确认软件缺陷的复现证据、修复代码验证和独立自动化检查。专项检查与 `tests` 下原有的 15 条常规自动化用例分开，便于分别保留修复前、修复后的执行证据。

当前已确认 3 个有效缺陷：

- `load_and_preprocess_images_extreme_ratio/`：`DEF-IMG-001` 已修复并完成复测，极端宽高比图片不再产生零尺寸。
- `exif_orientation_not_applied/`：`DEF-IMG-002` 已修复并完成复测，两个图像预处理函数会在尺寸计算前应用 JPEG EXIF 方向。
- `palette_transparency_not_composited/`：`DEF-IMG-003` 已修复并完成复测，带透明索引的调色板 PNG 会合成到白色背景。

每个缺陷目录包含输入数据、复现代码、一键运行脚本、执行结果和中文说明。

## 一键验证全部缺陷修复

在项目根目录运行：

```powershell
.\tests\defect_tests\run_all_defect_tests.ps1
```

脚本会依次运行 3 个缺陷目录中的 9 条检查，并把修复后汇总证据写入 `results/all_defects_fix_verification.txt`。当前预期为 9 条检查全部通过；修复前的 `results/all_defects_reproduction.txt` 保留作为历史证据。随后还应运行 `tests/run_tests.ps1`，确认原有 15 条常规回归测试全部通过。
