"""模块一：算法坐标转换系统 自动化测试工程。

被测对象：``vggt-main/vggt/utils/geometry.py``
用例编号：M1-GEO-001 ~ M1-GEO-032（与附录1测试用例清单一一对应）

运行方式（仓库根目录）：::

    powershell -ExecutionPolicy Bypass -File .\\run_tests.ps1

也可直接用底层命令：::

    $env:PYTHONPATH = "$PWD\\vggt-main"
    & "D:\\anaconda3\\envs\\Pytorch_Vggt\\python.exe" -m unittest discover `
        -s tests\\module1_coordinate -p "test_m1_geo*.py" -t . -v

约定：
- 不导入 ``demo_gradio_cn.py``（该脚本导入即加载模型并启动 Gradio）。
- ``vggt-main`` 的导入路径由外层注入，不修改被测源码。
- 浮点比较容差 ``atol=1e-6``。
"""
