# -*- coding: utf-8 -*-
"""生成《软件需求清单_模块二.xlsx》：以附录1 模板为底板，样式对齐模块一交付件。

模块二被测对象：VGGT 输出层（深度图 / npz 点云 / 相机参数）+ 批量推理入口
run_vggt_inference.py + 输入加载预处理 load_fn.py + 点云导出 visual_util.py
+ 图像读写工具链（OpenCV 兼容层）。

关联：15 条用例 M2-AI-001~015；缺陷 DEF-M2-001~005。
"""
import shutil

import openpyxl
from openpyxl.styles import Alignment, Border, Font, Side

TEMPLATE = r"E:\0_work\1shijian\实践作业-文档模板2025\附录1：软件需求清单模板.xlsx"
MODULE1 = r"E:\0_work\1shijian\Software_testing\deliverables\module1\软件需求清单_模块一.xlsx"
TARGET = r"E:\0_work\1shijian\Software_testing\deliverables\module2\软件需求清单_模块二.xlsx"

ROWS = [
    # A 功能模块名, B 子模块名, C 功能描述, D 备注
    (
        "VGGT 推理输出（深度图与 npz 点云）",
        "深度图与逐像素置信度输出（depth / depth_conf）",
        "单次前馈为每帧输出相机 z 向深度图 (S,H,W,1) 与逐像素置信度 (S,H,W)：深度值应全部有限、形状与帧数一致；置信度应能反映像素可靠程度，低置信像素占比随场景难度上升；"
        "当置信度上界低于计算阈值时，依赖置信度筛选的指标应报告「不可用」并给出降级提示，而不是静默跳过。",
        "关联用例 M2-AI-010（低置信竖构图场景默认阈值下 G1/G2/G4 全部因有效像素为 0 被判不可用）、M2-AI-011（阈值下探至 1.0 后可统计但显著劣化）。"
        "登记 DEF-M2-003：置信度绝对值随场景漂移，固定阈值 3.0 跨场景失效。",
    ),
    (
        "VGGT 推理输出（深度图与 npz 点云）",
        "点云双路径输出（world_points / world_points_from_depth）",
        "点图头直接回归的世界坐标点云与由「深度 + 相机参数」反投影得到的点云应互相自洽：两路径逐像素欧氏距离按场景尺度归一化后相对误差应小于 5e-3；"
        "输出形状 (S,H,W,3)；多视角冗余增加时自洽性应单调改善（1/2/5/9 帧的 G1 相对误差 4.130e-3 → 3.062e-3 → 2.093e-3 → 1.585e-3）。",
        "关联用例 M2-AI-001（基线四指标）、M2-AI-002/003（5 帧、2 帧退化）、M2-AI-005（帧数-指标单调性）；"
        "指标 G1 由 metrics.py 计算，不依赖外部真值。",
    ),
    (
        "VGGT 推理输出（深度图与 npz 点云）",
        "相机内外参与参考系约定（extrinsic / intrinsic）",
        "外参 (S,3,4) 遵循 OpenCV world→cam 约定，首帧被定义为场景参考系（与单位阵的偏差应为浮点噪声量级）；内参 (S,3,3) 以像素为单位且主点位于图像中心；"
        "将点云按该组参数重投影回自身像素网格应收敛（G2 平均重投影误差小于 5 px，且 99% 以上像素不超过 5 px）。",
        "关联用例 M2-AI-001（G2 2.171 px、<5 px 占 99.45%；extrinsic 首帧偏差 1.2e-4、主点 (259,259)）、"
        "M2-AI-004（单帧时 G4 因无帧对应报告不可用）。",
    ),
    (
        "VGGT 推理输出（深度图与 npz 点云）",
        "输出确定性与可复现性",
        "相同输入、独立进程重复推理时，depth、world_points、extrinsic、intrinsic 四个关键输出应逐位一致（max_abs_diff = 0）；"
        "跨运行、跨场景比较只能比较相对位姿与归一化后的几何量，绝对位姿因首帧参考系约定不可直接对比。",
        "关联用例 M2-AI-009（两次独立进程四字段 identical=true）；对应 exp/det2 与基线预测的逐位比对。",
    ),
    (
        "VGGT 推理输出（深度图与 npz 点云）",
        "鲁棒性与退化可观测性",
        "对像素级扰动应保持稳定、对多视角对应关系的破坏应出现可量化退化：0.5 倍降采样与 σ=10 高斯噪声下指标应与基线同量级；"
        "遮挡 25% 面积时应出现显著退化（G4 光度一致性 NCC 由 0.8729 降至 0.5536，降幅 36.6%；低置信像素占比由 21.90% 升至 40.19%）；"
        "退化必须能通过指标量化暴露，而不是静默通过。",
        "关联用例 M2-AI-006（0.5 倍分辨率，未显著退化）、M2-AI-007（高斯噪声 σ=10，未显著退化）、M2-AI-008（遮挡 25%，唯一显著退化项）。",
    ),
    (
        "VGGT 批量推理入口（run_vggt_inference.py）",
        "输入目录校验与异常处理一致性",
        "对三类异常输入应给出一致、面向用户的中文提示并以非零退出码结束，且不残留半成品产物：输入目录不存在、目录中没有任何图像、图像文件无法解码；"
        "异常不应以原始堆栈形式暴露内部调用链。",
        "关联用例 M2-AI-013（空目录）、M2-AI-014（目录不存在）、M2-AI-015（损坏图像）。登记 DEF-M2-001：损坏图像抛出未捕获 PIL.UnidentifiedImageError 且残留 images/，"
        "与另两类异常处理不一致（待修复）。",
    ),
    (
        "VGGT 批量推理入口（run_vggt_inference.py）",
        "产物归档与运行元信息记录",
        "每次运行应归档：逐帧伪彩色深度图（张数等于帧数）、predictions.npz（含 depth / world_points / 相机参数等）、可选的两个预测分支 GLB，以及 run_info.json；"
        "run_info.json 应记录帧数、预处理后张量形状、模型加载与前馈耗时、峰值显存、GLB 导出参数与产物清单，保证结果可追溯、可复算。",
        "关联用例 M2-AI-001（深度图 9/9、GLB 两份、峰值显存 8.467 GB、端到端约 40 s）；"
        "归档结构见 vggt_output/<场景>/。",
    ),
    (
        "VGGT 输入加载与预处理（vggt.utils.load_fn）",
        "多视图图像加载与尺寸归一化（load_and_preprocess_images）",
        "读取图像序列并统一转为 RGB，按 crop / pad 模式缩放至宽 518、高按 14 像素对齐（9 帧实测 (9,3,392,518)）；应支持 RGB / RGBA / 灰度 / 调色板等颜色模式；"
        "预处理不得静默改变输入视野：发生裁切时应给出告警或记录有效区域范围。",
        "关联用例 M2-AI-010~012（竖构图场景可用性、阈值下探、补白正方形对照）。登记 DEF-M2-002：crop 模式对 3:4 竖构图静默裁切 24.5% 纵向视野且无提示（待修复）；"
        "对照实验表明裁切不是质量退化的主因，但属静默信息丢失。",
    ),
    (
        "VGGT 点云导出与后处理（visual_util）",
        "置信度过滤与点云裁剪（--conf-thres）",
        "GLB 导出的置信度过滤行为应与参数语义一致（百分比语义下保留率应落在总量一半附近）；当数据分布导致目标保留率无法达成时，应给出告警而非静默输出；"
        "低置信场景不应默认导出全量点云。",
        "登记 DEF-M2-003：009_arbus N32 场景 86.4% 的像素置信度等于地板值，百分比过滤退化为全量保留，与参数声明严重不符（待修复）。",
    ),
    (
        "VGGT 点云导出与后处理（visual_util）",
        "背景剔除与预测分支选择",
        "导出应能按目标掩码裁剪点云（或提供可传入自定义掩码的入口），而不是仅依赖颜色阈值；预测分支（点云图分支 / 深度图与相机分支）应被正确区分，"
        "不得因分支名本地化而落错分支。",
        "登记 DEF-M2-004：输出未区分目标与背景，内置背景剔除仅支持颜色阈值且无法处理抗锯齿边缘（低优先级，工程内已有替代方案）。"
        "已修复项：中文分支名映射（demo_gradio_cn.py 的 PREDICTION_MODE_MAP），不计入有效缺陷。",
    ),
    (
        "VGGT 图像读写工具链（opencv-python / cv2_unicode）",
        "中文（非 ASCII）路径下的图像读写",
        "在含中文的目录或文件名下读写图像应正常完成；若底层 cv2.imwrite 在非 ASCII 路径下静默失败（返回 True 但未写出文件），工具链应提供兼容层保证产物落盘并可读回。",
        "登记 DEF-M2-005：OpenCV 4.13.0 在中文路径下 imwrite 静默失败（四类路径组合仅 ASCII/ASCII 成功），工程内兼容层 cv2_unicode.py 已提供规避方案（待修复）。",
    ),
]


def estimate_height(values, widths):
    """按列宽估算换行数，返回行高（pt）。CJK 记 1.0、其他记 0.55 字符宽。"""
    max_lines = 1
    for text, width in zip(values, widths):
        if not text:
            continue
        units = 0.0
        for ch in str(text):
            units += 1.0 if ord(ch) > 0x2E80 else 0.55
        per_line = max(8.0, width - 1.5)
        max_lines = max(max_lines, int(units / per_line) + 1)
    return round(max_lines * 17.5 + 14, 1)


# ---- 1. 读取模块一的样式，保证两份文档外观一致 ----
style_wb = openpyxl.load_workbook(MODULE1)
style_ws = style_wb["软件需求清单"]
sample = style_ws.cell(row=2, column=1)
font_style = sample.font
if font_style and font_style.name:
    body_font = Font(name=font_style.name, size=font_style.size, bold=font_style.bold)
else:
    body_font = Font(name="等线", size=10)
body_align = Alignment(wrap_text=True, vertical="top", horizontal="left")
thin = Side(style="thin", color="666666")
body_border = Border(left=thin, right=thin, top=thin, bottom=thin)

widths = []
for col in ("A", "B", "C", "D"):
    widths.append((style_ws.column_dimensions[col].width or 22.7))

# ---- 2. 复制模板并填充 ----
shutil.copy2(TEMPLATE, TARGET)
wb = openpyxl.load_workbook(TARGET)
ws = wb["软件需求清单"]

for col, width in zip(("A", "B", "C", "D"), widths):
    ws.column_dimensions[col].width = width

for i, row in enumerate(ROWS, start=2):
    for j, value in enumerate(row, start=1):
        cell = ws.cell(row=i, column=j, value=value)
        cell.font = body_font
        cell.alignment = body_align
        cell.border = body_border
    ws.row_dimensions[i].height = estimate_height(row, widths)

wb.save(TARGET)
print("WROTE", TARGET)
print("需求条数:", len(ROWS))
for i, r in enumerate(ROWS, start=2):
    print("  R%02d  %s / %s" % (i, r[0][:24], r[1][:30]))
