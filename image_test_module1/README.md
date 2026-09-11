# VGGT 图像预处理模块自动化测试说明

## 一、测试对象

本测试工程用于验证 VGGT 图像加载与预处理模块中的以下两个函数：

- `load_and_preprocess_images()`：完成图片读取、RGB 转换、缩放、裁剪、补边和批量张量生成；
- `load_and_preprocess_images_square()`：将图片居中补成正方形、缩放到目标尺寸，并返回原图区域坐标。

## 二、测试规模与设计方法

当前初始版本共有 15 条自动化测试用例，采用以下两种测试用例设计方法：

- 等价类划分：9 条；
- 边界值分析：6 条。

测试内容包括合法 RGB 图片、RGBA 透明图片、灰度图片、多图片批处理、非法模式、无图片输入、最小图片尺寸、横图、竖图、无效路径以及目标尺寸边界等。

## 三、目录结构

```text
tests/
├── common.py
├── README.md
├── run_tests.ps1
├── input/
│   ├── pillow_hopper_rgb.jpg
│   ├── pillow_hopper_rgb.png
│   └── pillow_hopper_gray_4bpp.tif
├── load_and_preprocess_images/
│   ├── test_equivalence.py
│   └── test_boundary.py
└── load_and_preprocess_images_square/
    ├── test_equivalence.py
    └── test_boundary.py
```

其中：

- `common.py`：负责创建测试所需的临时图片，测试结束后自动清理；
- `input/`：保存来自 Pillow 官方测试资源的固定输入图片及来源说明；
- `test_equivalence.py`：存放等价类划分测试；
- `test_boundary.py`：存放边界值测试；
- `run_tests.ps1`：一键运行全部测试用例。

## 四、运行环境

- 操作系统：Windows；
- 项目目录：`D:\codex\vggt\vggt-main`；
- Python 环境：项目自带的 `.venv`；
- 测试框架：Python 标准库 `unittest`；
- 主要依赖：PyTorch、torchvision、Pillow。

本测试工程不需要加载 VGGT 模型权重，也不需要使用 GPU。

普通格式、颜色模式和批处理用例优先使用 `input/` 中的固定真实图片；`1×1`、`518×14`等必须精确控制尺寸或颜色的边界用例，仍由测试程序临时生成。

## 五、一键运行全部用例

打开 PowerShell，进入项目目录：

```powershell
cd D:\codex\vggt\vggt-main
```

执行一键测试脚本：

```powershell
.\tests\run_tests.ps1
```

也可以直接执行底层测试命令：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## 六、结果说明

每条用例后显示 `ok`，表示该用例通过；显示 `FAIL` 或 `ERROR`，表示该用例失败或执行出错。

全部通过时，末尾会显示类似结果：

```text
Ran 15 tests
OK
```

其含义为：共执行 15 条测试用例，所有用例均通过。
