# 模块一测试工程：算法坐标转换系统

## 一、被测对象

`vggt-main/vggt/utils/geometry.py`，共 8 个确定性函数，不加载模型权重、不需要 GPU。

## 二、用例规模

33 条自动化测试用例，对应附录1 测试用例清单中的 `M1-GEO-001 ~ M1-GEO-032`
（`M1-GEO-019` 额外含 1 条对照用例），按被测函数分组：

| 文件 | 用例编号 | 被测函数 | 条数 |
|---|---|---|---|
| `test_m1_geo_001_005_depth_to_cam.py` | 001–005 | `depth_to_cam_coords_points` | 5 |
| `test_m1_geo_006_010_inverse_se3.py` | 006–010 | `closed_form_inverse_se3` | 5 |
| `test_m1_geo_011_015_depth_to_world.py` | 011–015 | `depth_to_world_coords_points` | 5 |
| `test_m1_geo_016_019_unproject.py` | 016–019 | `unproject_depth_map_to_point_map` | 5 |
| `test_m1_geo_020_022_batch_project.py` | 020–022 | `project_world_points_to_camera_points_batch` | 3 |
| `test_m1_geo_023_026_img_from_cam.py` | 023–026 | `img_from_cam` | 4 |
| `test_m1_geo_027_029_project_to_cam.py` | 027–029 | `project_world_points_to_cam` | 3 |
| `test_m1_geo_030_032_cam_from_img.py` | 030–032 | `cam_from_img` | 3 |

设计方法沿用附录1 的标注：等价类划分、边界值分析、错误推测、判定表、组合覆盖。

## 三、目录结构

```text
tests/
├── __init__.py
├── README.md                      本文件
├── junit_report.py                执行一次并产出 JUnit XML + UTF-8 日志
└── module1_coordinate/
    ├── __init__.py
    ├── common.py                  共享断言与夹具（容差 atol=1e-6）
    └── test_m1_geo_*.py           按被测函数分组的 8 个用例文件
```

## 四、一键运行

在仓库根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\run_tests.ps1
```

日志与 JUnit XML 归档到 `test_results/module1/`。

`run_tests.ps1` 在检测到本目录下的 `junit_report.py` 时，会**改由该脚本统一执行一次**，
同时产出 `.log`、`.xml`，因此测试不会重复运行。若把 `junit_report.py` 移除，
脚本会退回直接调用 `unittest discover`，此时只产出日志、不产出 XML。

**为什么日志由 Python 写**：Windows PowerShell 5.1 捕获原生进程输出时会用控制台
ANSI 码页解码其 stderr，中文用例名会被双重编码成乱码（如 `两帧` → `涓ゅ抚`）。
因此 `junit_report.py` 用 `--log` 自己以 UTF-8 落盘，脚本只把运行横幅写入临时头文件、
由 `--header-file` 交给 Python 拼接。日志末尾的「退出码 / JUnit XML」两行由脚本在
测试结束后追加。

也可直接执行底层命令：

```powershell
$env:PYTHONPATH = "$PWD\vggt-main"
& "D:\anaconda3\envs\Pytorch_Vggt\python.exe" -m unittest discover `
    -s tests\module1_coordinate -p "test_m1_geo*.py" -t . -v
```

或单独生成 XML 与日志：

```powershell
python tests\junit_report.py --output test_results\module1\report.xml `
    --log test_results\module1\report.log `
    --start-dir tests\module1_coordinate --pattern "test_m1_geo*.py" --top-level .
```

## 五、运行现状（重要）

**33 条中 31 条通过，2 条失败**：`M1-GEO-016` 与 `M1-GEO-018`。

这两个失败是**有意为之、且是真实缺陷的证据**，不是用例写错：

- 函数文档声明 `depth_map` 支持 `(S, H, W)` 与 `(S, H, W, 1)` 两种形状；
- 实现中 `depth_map[frame_idx].squeeze(-1)` 在 `W == 1` 时会**删除宽度维**，
  随后 `H, W = depth_map.shape` 解包失败，抛出
  `ValueError: not enough values to unpack (expected 2, got 1)`；
- 该问题即已登记的缺陷 **`DEF-M1-001`**（复现记录见
  `test_results/module1/DEF-M1-001_reproduction.txt`），**当前尚未修复**。

两条用例按文档承诺的**预期结果**断言，因此缺陷修复前必然失败；修复后应自动转为通过，
无需改动用例。`M1-GEO-019` 的对照与越界断言改用四维输入，以绕开该缺陷、独立验证
「帧数与外参数量不一致」这一意图。

## 六、约定与约束

- 不导入 `demo_gradio_cn.py`：该脚本导入即加载模型权重并启动 Gradio。
- `vggt-main` 的导入路径由 `run_tests.ps1` 从外层通过 `PYTHONPATH` 注入，
  **不为可测性修改被测源码**。
- 浮点比较统一容差 `atol=1e-6`。
- 测试未通过 ≠ 有效缺陷；有效缺陷须经复现、分析、处理与复测并保留证据。
