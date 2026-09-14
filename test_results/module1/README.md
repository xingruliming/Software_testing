# 模块一测试结果目录

本目录保存模块一（算法坐标转换系统）的测试执行证据。

## 目录内容

| 文件 | 说明 |
|---|---|
| `run_<时间戳>.log` | 一次完整执行的 UTF-8 控制台日志（含运行横幅、用例输出、退出码） |
| `run_<时间戳>.xml` | 同一次执行的 JUnit XML，供报告统计用例数/通过数/失败数 |
| `DEF-M1-001_reproduction.txt` | DEF-M1-001 缺陷复现记录（环境、步骤、实际结果、定位结论） |
| `README.md` | 本文件 |

## 如何产生

在仓库根目录执行一键入口：

```powershell
powershell -ExecutionPolicy Bypass -File .\run_tests.ps1
```

脚本调用 `tests/junit_report.py` **只执行一次**测试，同时产出 `.log` 与 `.xml`。

## 当前执行状态

最近一次执行：`run_20260914_172031.log` / `run_20260914_172031.xml`

- 用例总数 33（M1-GEO-001 ~ M1-GEO-032 加一条对照用例）
- 通过 31，失败 0，错误 2
- 退出码 1

两条错误用例为 **M1-GEO-016** 与 **M1-GEO-018**，均为 **DEF-M1-001 的真实缺陷证据**
（`depth_to_cam_coords_points` 对文档声明的 `(S, H, W)` 三维输入解包失败），
不是测试代码本身的问题。

## 关于编码

`.log` 由 `tests/junit_report.py` 以 UTF-8 直接落盘，**不经过 PowerShell 的子进程输出捕获**。
Windows PowerShell 5.1 会用控制台 ANSI 码页解码原生进程的 stderr，导致中文用例名双重编码成乱码；
因此横幅与运行信息由脚本写入临时头文件后交给 Python 拼接，而不是由 PowerShell 拼接后再写日志。

## 注意

`DEF-M1-001_reproduction.txt` 记录的是 2026-09-10 的一次手工复现，其中的缺陷在
`vggt-main` 基线中**仍未修复**——测试用例 016/018 持续失败即为证据。请勿把未实际
执行的结果填写为已完成测试。
