# DEF-IMG-001 极端宽高比图片导致预处理崩溃

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
│   └── DEF-IMG-001_reproduction.txt
├── expected_behavior_checks.py
├── generate_input.py
├── run_defect_test.ps1
└── README.md
```

## 检查内容

1. `518×14`、`crop`：有效边界对照，应返回 `(1,3,14,518)`，当前通过。
2. `518×1`、`crop`：函数不应生成零高度，当前抛出异常。
3. `518×1`、`pad`：函数应返回 `(1,3,518,518)`，当前抛出异常。

## 一键执行

在项目根目录运行：

```powershell
.\tests\defect_tests\load_and_preprocess_images_extreme_ratio\run_defect_test.ps1
```

在缺陷修复前，预期结果为 `1 passed, 2 errors`，脚本退出码为非零。这表示被测功能没有满足期望行为，不是测试脚本自身损坏。执行输出会保存到 `results/DEF-IMG-001_reproduction.txt`。

## 修复验证标准

当前源码尚未修复，crop 与 pad 的两个期望行为检查仍抛出 `ValueError`，因此当前修复验证状态为未通过。完成修复后要求：

- 三条检查全部通过；
- crop 模式输出高度至少为一个补丁单位 `14`；
- pad 模式输出为 `(1,3,518,518)`；
- 原有 15 条自动化测试仍全部通过。
