# DEF-IMG-001 极端宽高比图片导致预处理崩溃（已修复并复测通过）

## 测试对象

`vggt.utils.load_fn.load_and_preprocess_images()`

## 缺陷说明

函数会把缩放后的尺寸四舍五入到 `14` 的整数倍。对于 `518×1` 图片，缩放高度的计算结果为：

```text
round(1 × (518 / 518) / 14) × 14 = 0
```

随后 Pillow 收到 `(518, 0)` 的缩放尺寸并抛出：

```text
ValueError: height and width must be > 0
```

## 目录结构

```text
load_and_preprocess_images_extreme_ratio/
├── input/
│   ├── extreme_wide_518x1.png
│   ├── valid_boundary_518x14.png
│   └── README.md
├── results/
│   ├── DEF-IMG-001_reproduction.txt
│   └── DEF-IMG-001_fix_verification.txt
├── expected_behavior_checks.py
├── generate_input.py
├── run_defect_test.ps1
└── README.md
```

## 检查内容

1. `518×14`、`crop`：有效边界对照，应返回 `(1,3,14,518)`，当前通过。
2. `518×1`、`crop`：函数不再生成零高度，返回高度至少为 `14` 的有效张量，当前通过。
3. `518×1`、`pad`：函数返回 `(1,3,518,518)`，当前通过。

## 一键执行

在项目根目录运行：

```powershell
.\tests\defect_tests\load_and_preprocess_images_extreme_ratio\run_defect_test.ps1
```

修复后的预期结果为 `Ran 3 tests`、`OK`，脚本退出码为 `0`。修复验证输出会保存到 `results/DEF-IMG-001_fix_verification.txt`；原来的 `DEF-IMG-001_reproduction.txt` 保留为修复前证据。

## 修复验证标准

当前已在补丁对齐计算后增加最小尺寸保护，crop 与 pad 的短边至少为 `14`。修复验证要求及结果如下：

- 三条检查全部通过；
- crop 模式输出高度至少为一个补丁单位 `14`；
- pad 模式输出为 `(1,3,518,518)`；
- 原有 15 条自动化测试仍全部通过。

当前上述条件均已满足，`DEF-IMG-001` 修复验证通过；`DEF-IMG-002` 和 `DEF-IMG-003` 未在本次修改范围内。
