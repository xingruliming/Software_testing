# VGGT 软件测试与质量保证实践

本仓库以 VGGT 的几何坐标转换模块为模块一被测对象，并保留 VGGT 中文可视化程序用于功能演示。教师后来已明确许可 AI 参与模块一用例设计；当前已形成 32 条测试用例，自动化测试代码、正式执行结果和缺陷结论尚未完成。

## 当前阶段

- 当前只处理模块一的外围结构、运行保护、文档模板和坐标转换测试用例设计。
- `vggt-main/` 作为被测软件基线，默认不修改。
- `VGGT测试方案.md` 偏向 AI 系统鲁棒性分析，暂作为模块二储备材料，不计入模块一用例与结果。
- 附录1填报版已包含 32 条模块一测试用例，全部标记为可自动化；当前仍不包含 pytest 测试脚本或正式执行结果。

## 被测对象

模块一建议选择 `vggt-main/vggt/utils/geometry.py`，主要包含深度图反投影、相机/世界坐标转换、SE(3) 变换求逆、三维点投影和畸变处理等确定性功能。该模块约 324 行，可以在不加载 VGGT 大模型的情况下进行单元测试。

模块一暂不覆盖：

- 模型训练流程；
- 论文精度指标复现；
- 完整 10 亿参数模型的自动化性能测试；
- Gradio 页面端到端自动化；
- 模块二的 AI 鲁棒性、公平性和安全性测试。

## 目录结构

```text
Software_testing/
├── README.md
├── run_vggt_demo.ps1          # 从正确工作目录启动现有可视化程序
├── tests/                     # 小组成员人工编写的模块一测试工程
├── test_results/module1/      # 人工执行后保存日志、JUnit XML、截图等
├── deliverables/module1/      # 附录模板副本、操作手册和检查清单
├── vggt_input/                # 演示输入素材
├── vggt_output/               # 可再生的运行产物
├── metrics.py                 # 模块二可继续使用的无真值指标工具
└── vggt-main/                 # 被测软件与中文可视化程序
```

## 环境准备

当前已知环境：

- Windows；
- Conda 环境：`Pytorch_Vggt`；
- Python：3.10；
- CUDA 版 PyTorch；
- 模型权重：`E:\办公\研一\1软件实践\model.pt`。

请勿将 `model.pt`、运行产生的点云/GLB、缓存或本地证书提交到 Git。若权重位置改变，当前 `demo_gradio_cn.py` 中的既有权重路径也需要同步处理；模块一默认不修改该脚本。

## 启动 VGGT 可视化

推荐在 PowerShell 中从仓库根目录运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\run_vggt_demo.ps1
```

如果需要指定 Python：

```powershell
.\run_vggt_demo.ps1 -PythonExecutable "D:\anaconda3\envs\Pytorch_Vggt\python.exe"
```

也可以直接运行原程序，但必须先进入它所在的目录，以保证相对路径有效：

```powershell
Set-Location "E:\办公\研一\1软件实践\Software_testing\vggt-main"
& "D:\anaconda3\envs\Pytorch_Vggt\python.exe" ".\demo_gradio_cn.py"
```

启动后按终端输出访问本地 Gradio 地址。结束服务时在启动终端按 `Ctrl+C`。

## 模块一测试接入

后续仍需完成以下内容：

1. 评审附录1中现有的 32 条用例，并建立测试编号与 pytest 函数的对应关系。
2. 至少实现 24 条自动化，建议将当前 32 条可自动化用例全部实现。
3. 保留 Excel 中已经标注的等价类、边界值、错误推测、判定表和组合覆盖方法。
4. 创建根目录 `run_tests.ps1`，使其能一次运行全部自动化用例，并把 JUnit XML 和日志保存到 `test_results/module1/`。
5. 只记录经过真实复现的有效缺陷；模块一缺陷报告至少需要 3 个有效缺陷及修复验证记录。

具体操作顺序和填报要求见 `deliverables/module1/测试操作手册.md`。

## Git 提交要求

- 每位小组成员使用自己的账号提交实际完成的工作。
- 不代替其他成员提交，也不重写历史伪造贡献。
- 提交信息清楚说明修改内容，例如测试方法、测试脚本、缺陷修复或文档更新。
- 提交前确认测试日志、报告统计和成员贡献说明能够相互对应。
