# -*- coding: utf-8 -*-
"""
从模板 `华科蓝.pptx` 重做「模块一测试工作汇报」PPT —— 包级手术（v2）。

做法：解包模板 → 逐页只替换 <a:t> 运行文本 → 保留全部形状/母版/配图/主题。
绝不重建版式，因此视觉与模板 100% 一致。

本版（v6）P07「等价类+边界值」正文改为具体用例示例（001/004/003/014/025/022/028/019/005），
四卡正文字号 16pt→12pt（14 页 → 15 页维持 v5 页序）：
  · P13 修复建议页保留（tpl slide4 复制件）
  · 清单标注口径不变：等价类 19 / 边界值 5 / 组合覆盖 4 / 错误推测 2 / 判定表 2，无场景法

页序 -> 模板页：
  P01 slide1(封面) P02 slide2(目录) P03 slide3(扉页01) P04 slide4(三行编号)
  P05 slide7(双栏图文) P06 slide6(扉页02)
  P07 slide5(四卡)              P08 slide4 复制件(三行)
  P09 slide5 复制件(四卡,KPI)   P10 slide8(四卡图文) P11 slide4 复制件(自动化)
  P12 slide7 复制件(缺陷)       P13 slide4 复制件(修复建议,新) P14 slide5 复制件(结论)
  P15 slide15(结束页)

⚠️ 三个必须遵守的坑（详见技能 slidep-pptx-build-verify）：
  1. 每个复制页必须有自己的 ppt/tags/tagN.xml 部件，否则 PowerPoint 拒开。
  2. rels 根元素必须用正则取 <Relationships\b[^>]*>，不能用 find('<Relationship')。
  3. 形状一律按 id 定位，不能按 XML 出现顺序（顺序 != 视觉顺序）。
"""
import os
import re
import shutil
import zipfile

TPL = r"E:\0_work\PPT模版\华科蓝.pptx"
OUT = r"E:\0_work\1shijian\Software_testing\deliverables\模块一测试工作汇报\模块一测试工作汇报.pptx"
WORK = r"C:\Users\LENOVO\AppData\Local\Temp\ppt_work\build2"

VERBOSE = True


# ------------------------------------------------------------------ 基础工具
def txts_of(xml):
    return re.findall(r"<a:t>(.*?)</a:t>", xml, re.S)


def sp_block(xml, shape_id):
    """取出指定 id 的 <p:sp> 整块；找不到返回 None。"""
    pat = re.compile(
        r"<p:sp>(?:(?!</p:sp>).)*?<p:cNvPr id=\"%d\"(?:(?!</p:sp>).)*?</p:sp>" % shape_id,
        re.S)
    m = pat.search(xml)
    return m


def set_shape_text(xml, shape_id, new_texts):
    """把指定 id 的 <p:sp> 内 <a:t> 依次写成 new_texts，多余的清空。
    换行用 '\\n' 表示（写入为 <a:br/> 由调用方保证不出现；这里用竖线分隔多行文本时
    同属一个 run 的换行由 XML 中的 <a:br/> 承担，本函数只做纯文本替换）。
    """
    m = sp_block(xml, shape_id)
    if not m:
        raise RuntimeError("shape id=%s not found" % shape_id)
    blk = m.group(0)
    originals = re.findall(r"<a:t>(.*?)</a:t>", blk, re.S)
    if len(new_texts) > len(originals):
        raise RuntimeError("shape id=%s: %d 个 <a:t> 放不下 %d 段文本" %
                           (shape_id, len(originals), len(new_texts)))
    # ⚠️ 写入 <a:t> 的文本必须做 XML 实体转义，否则 & < > 会让整个部件 XML 非法
    def esc(s):
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    texts = list(new_texts) + [""] * (len(originals) - len(new_texts))
    it = iter(esc(t) for t in texts)
    newblk = re.sub(r"<a:t>.*?</a:t>", lambda mm: "<a:t>%s</a:t>" % next(it),
                    blk, flags=re.S)
    return xml[:m.start()] + newblk + xml[m.end():]


def shrink_shape_font(xml, shape_id, new_sz):
    """把指定 id 形状内所有 run 的字号统一改为 new_sz（百分之一磅）。"""
    m = sp_block(xml, shape_id)
    if not m:
        raise RuntimeError("shape id=%s not found" % shape_id)
    blk = m.group(0)
    newblk = re.sub(r'sz="\d+"', 'sz="%d"' % new_sz, blk)
    return xml[:m.start()] + newblk + xml[m.end():]


# 需要缩小字号的页面：{页序(1-based): {形状 id: 新字号}}
# P07 四卡正文 16pt→12pt，为容纳具体用例示例
FONT_SHRINKS = {
    7: {17: 1200, 42: 1200, 48: 1200, 53: 1200},
}


# ================================================================= 页面内容表
# (模板页号, {形状 id: [文本段...]})
# 注意：多段落写进同一个 <a:t> 时用 "\n" 会被转义，故这里只做「一个 <a:t> = 一段」的映射；
# 需要多行的正文形状，用模板自带的多个 <a:t> 承担（slide7 的正文有 17 个）。
# ================================================================= 页面内容表
# 按「页序」列出（1-based），每项 = (模板页号, 是否复制件, {形状 id: [文本段...]})
# 注意：一个 <a:t> = 一段文本；段数不能超过该形状原有的 <a:t> 个数。
# 形状一律按 id 定位（XML 出现顺序 != 视觉顺序）。
PAGES = [
    # ---------------------------------------- P01 封面 (tpl slide1)
    # id27=3 runs；id28=7 runs；id29=5 runs
    (1, False, {
        27: ["VGGT", "模块一", "测试汇报"],
        28: ["汇报人丨黄国宸 曹钧杰", "  ", "时间丨", "2026", ".", "9", ""],
        29: ["32 条用例 · 2 种方法", " | ", "0 权重 0 GPU", " | ", "1 个缺陷"],
    }),
    # ---------------------------------------- P02 目录 (tpl slide2) 动态生成
    (2, False, {}),
    # ---------------------------------------- P03 章节扉页 01 (tpl slide3)
    (3, False, {
        69: ["被测对象核心功能"],
        70: ["TEST OBJECT & CORE FUNCTIONS"],
    }),
    # ---------------------------------------- P04 三行编号版式 (tpl slide4)
    (4, False, {
        11: ["被测对象：VGGT 的几何计算层"],
        29: ["TEST OBJECT & CORE FUNCTIONS"],
        30: ["被测", "对象"],
        32: ["前馈式三维大模型"],
        33: ["FEED-FORWARD", " | ", "1B PARAMS"],
        34: ["VGGT 是 Meta AI 与牛津大学的三维视觉大模型、CVPR 2025 最佳论文；"
             "单次前向即可从一至数百张图像预测相机内外参、深度图、点图与三维轨迹，约 10 亿参数。"],
        38: ["核心功能链"],
        39: ["COORDS CHAIN", " | ", "CAM · WORLD · PIXEL"],
        40: ["geometry.py 324 行 8 个函数（NumPy/PyTorch 混合），做深度图/相机/世界/像素坐标"
             "互转：unproject → depth_to_world → depth_to_cam（L15/47/87）。"],
        44: ["绝对位姿不可比"],
        45: ["GAUGE FREEDOM", " | ", "RELATIVE ONLY"],
        47: ["第一帧外参被固定为单位阵，以首帧相机作场景参考系。"
             "跨运行比较绝对位姿没有意义，断言只能取相对量或闭式解析解。"],
    }),
    # ---------------------------------------- P05 双栏图文 (tpl slide7)
    (7, False, {
        11: ["文档承诺与实现不一致，是最值得测的位置"],
        29: ["DOC CONTRACT VS IMPLEMENTATION"],
        19: ["函数契约（第 22 行）"],
        21: ["docstring 明文声明：depth_map 的形状可为 (S, H, W, 1) 或 (S, H, W)。"],
        37: ["实际实现（第 39 行）"],
        39: ["但实现第 39 行对每一帧无条件执行 squeeze(-1)，实质只兼容四维输入。"],
    }),
    # ---------------------------------------- P06 章节扉页 02 (tpl slide6)
    (6, False, {
        12: ["主要测试策略"],
        13: ["MAIN TEST STRATEGY"],
    }),
    # ---------------------------------------- P07 四卡：两种经典方法 + 三类加固 (tpl slide5)
    # v6：正文改为具体用例示例（用户反馈原版太抽象），字号 16pt→12pt 以容纳更长文案。
    # 12pt / 宽 2.14in → 每行约 12 全角字，正文控制在 ≈5 行（60 字以内更稳）。
    (5, False, {
        11: ["等价类 + 边界值：两种经典方法打底"],
        29: ["TWO CORE METHODS"],
        3:  ["等价类划分"],
        17: ["例 001：单像素深度反投影，应精确回到原像素；例 004：内参尺寸非法应抛错。合法/非法各成一类，共 19 条。"],
        20: ["边界值分析"],
        42: ["例 003：全零深度图即深度下界；例 014：深度恰等于 eps 无效、大于才有效；例 025：z=0。共 5 条。"],
        22: ["组合覆盖"],
        48: ["例 022：同一世界点经两帧外参投影得不同坐标；例 028：平移 (1,2,0)×非单位内参叠加。共 4 条。"],
        52: ["错误推测"],
        53: ["例 019：帧数多于外参应抛错而非部分结果；例 005：非零 skew。判定表另固化 2 条。"],
    }),
    # --------- P08 新增：用例→方法映射（tpl slide4 复制件，三行版式）
    # 长度预算（实测）：正文 14pt / 宽 8.04in → 每行约 52 个全角字符；行距 1.5in
    # → 正文最多 3 行（约 150 字）。英文副标 8pt / 宽 2.92in → 最多约 14 个半角字符。
    (4, True, {
        11: ["每条用例都标了方法，可以逐条对账"],
        29: ["CASE TO METHOD MAPPING"],
        30: ["测试", "方法"],
        32: ["等价类划分"],
        33: ["EQUIVALENCE · 19 CASES", " | ", "M1-GEO-001~030"],
        34: ["切割依据是输入维度、坐标系、输入类型与合法性四组维度。"
             "001/004/006/007/008/009/011/012/013/016/017/018 等 19 条。"],
        38: ["边界值分析"],
        39: ["BOUNDARY · 5 CASES", " | ", "M1-GEO-002~025"],
        40: ["取每个等价类的上下界与临界点：002 图像四角、003 深度下界 0、010 矩阵尺寸、"
             "014 eps−/eps/eps+ 三点夹逼、025 Z=0 除零。"],
        44: ["其余标注"],
        45: ["OTHER · 8 CASES", " | ", "M1-GEO-005~032"],
        47: ["组合覆盖 4 条：015/022/028/031；错误推测 2 条：005/019；判定表 2 条：029/032。"
             "32 条全部有方法标注，与清单备注列一致。"],
    }),
    # ---------------------------------- P09 四卡图文形状矩阵 (tpl slide8)
    (8, False, {
        11: ["用最小输入逼出两类失败"],
        29: ["SHAPE MATRIX OF TEST SAMPLES"],
        12: ["失败②：W > 1 时对非单位轴 squeeze，直接抛错。"],
        14: ["通过：正常返回 (2, 1, 1, 3)。这是声明的另一种形状。"],
        41: ["通过：正常返回 (2, 1, 2, 3)。与左格同源，缺陷只在三维分支。"],
        27: ["失败①：W = 1 时宽度维被删，H, W 解包失败。"],
        31: ["(2,1,1)"], 42: ["(2,1,2)"], 43: ["(2,1,1,1)"], 44: ["(2,1,2,1)"],
    }),
    # --------- P10 新增：自动化设计与实施（tpl slide4 复制件，三行版式）
    (4, True, {
        11: ["一条命令跑完的自动化测试工程"],
        29: ["TEST AUTOMATION"],
        30: ["自动", "化"],
        32: ["一键运行的测试工程"],
        33: ["8 FILES", " | ", "33 EXECUTIONS"],
        34: ["tests/module1_coordinate/ 下 8 个用例文件对应 8 个函数；run_tests.ps1 一键运行 "
             "33 条用例（32 清单 + 1 对照），PYTHONPATH 注入被测模块，不改基线一行代码。"],
        38: ["一次运行双产出"],
        39: ["JUNIT XML", " | ", "UTF-8 LOG"],
        40: ["junit_report.py 单次运行同时产出 JUnit XML 与 UTF-8 运行日志；单次执行约 0.02 秒；"
             "退出码 0/1/2/3 明确区分全过、有失败、无工程、不可导入四种状态。"],
        44: ["结果逐位一致"],
        45: ["CPU ONLY", " | ", "DETERMINISTIC"],
        47: ["测试不依赖模型权重与 GPU；跨运行结果逐位一致，"
             "任何人一条命令即可复现全部 33 次执行与 2 个错误的现场。"],
    }),
    # ---------------------------------- P11 四卡 KPI（tpl slide5 复制件）
    (5, True, {
        11: ["一次真实执行：33 条执行，31 通过"],
        29: ["ONE REAL RUN · 93.9% PASS"],
        3:  ["33"],
        17: ["条自动化用例执行，覆盖全部 8 个函数。"],
        20: ["31"],
        42: ["条通过，含 1 条专门设计的绕障对照用例。"],
        22: ["2"],
        48: ["条失败：M1-GEO-016 与 018，traceback 逐层一致。"],
        52: ["93.9%"],
        53: ["用例通过率 = 31 / 33，退出码 1，与约定一致。"],
    }),
    # ---------------------------------- P12 缺陷（tpl slide7 复制件）
    (7, True, {
        11: ["DEF-M1-001：一根被删掉的宽度维"],
        29: ["DEFECT LOCATION"],
        19: ["现象与影响"],
        21: ["输入 (2, 1, 1) 三维深度图即抛 ValueError；docstring 声明的全部 (S, H, W) 输入都不可用。"],
        37: ["根因与处置"],
        39: ["根因是第 39 行无条件 squeeze(-1)。已登记并给出修复建议，按约定未改动基线。"],
    }),
    # --------- P13 新增：修复建议（tpl slide4 复制件，三行版式）
    # 复用三行版式长度预算：行标题 ≤8 全角字；正文 14pt/宽 8.04in ≤2 行(约 70 字)；
    # 英文副标 8pt ≤22 半角字符左右。
    (4, True, {
        11: ["修复建议：文档与实现必须有一个让步"],
        29: ["FIX SUGGESTION & REGRESSION"],
        30: ["修复", "方案"],
        32: ["条件式 squeeze"],
        33: ["NDIM-AWARE", " | ", "1-LINE FIX"],
        34: ["第 39 行前判断 ndim==4 且末维为 1 再取 [..., 0]；用 ndim 判断而非看末维"
             "是否为 1，避免误伤 W=1 的合法三维输入。"],
        38: ["入口防御"],
        39: ["INPUT VALIDATION", " | ", "CONTRACT ALIGN"],
        40: ["入口校验 ndim∈{3,4}，非法形状抛出带形状信息的明确错误；若不改代码则须把 "
             "docstring 收窄为仅 (S, H, W, 1)，文档与实现二者必居其一。"],
        44: ["回归验证"],
        45: ["REGRESSION", " | ", "33 ALL GREEN"],
        47: ["修复后重跑一键测试：33 条应全部通过（016/018 转绿、017 不回归）；"
             "按课程约定基线未改，本页仅作修复方案留档演示。"],
    }),
    # --------- P14 新增：测试结论（tpl slide5 复制件，四卡版式）
    (5, True, {
        11: ["四条结论，每条都有数据支撑"],
        29: ["CONCLUSIONS"],
        3:  ["质量结论"],
        17: ["31/33 通过，唯一失败同源于一个缺陷；被测模块质量整体可信。"],
        20: ["缺陷处置"],
        42: ["DEF-M1-001 已登记并给出修复建议；按约定未改动被测基线。"],
        22: ["方法结论"],
        48: ["等价类 + 边界值满足 ≥2 种要求，五类标注 32 条全部对得上账。"],
        52: ["工程结论"],
        53: ["一条命令复现、逐位一致，可长期作为该模块的回归基线。"],
    }),
    # ---------------------------------------- P15 结束页 (tpl slide15)
    (15, False, {
        27: ["谢谢观看"],
        28: ["汇报人丨黄国宸 曹钧杰", "  ", "时间丨", "2026", ".", "9", ""],
        29: ["脱离权重单测", " | ", "用例自动转绿", " | ", "一条命令复现"],
    }),
]

TOC_ITEMS = ["被测对象", "测试策略", "自动化实施", "结果与结论"]  # 目录框一行仅容 5 字，完整表述在扉页/内容页


def build_toc_mapping(xml):
    """目录页：4 个编号圆(id 34/39/43/47) + 4 条标题矩形(id 35/40/44/48)。
    标题矩形在模板里的 y 坐标被写成了占位值，因此直接按 id 顺序配对（1→35, 2→40…），
    不要用 y 排序。"""
    title_ids = [35, 40, 44, 48]
    mapping = {}
    for text, sid in zip(TOC_ITEMS, title_ids):
        mapping[sid] = [text]
    if VERBOSE:
        print("  目录条目 ->", list(zip(title_ids, TOC_ITEMS)))
    return mapping


def unzip(path, dest):
    if os.path.isdir(dest):
        shutil.rmtree(dest, ignore_errors=True)
    os.makedirs(dest, exist_ok=True)
    with zipfile.ZipFile(path) as z:
        z.extractall(dest)


def main():
    # 1) 解包模板
    tpl_dir = os.path.join(WORK, "tpl")
    unzip(TPL, tpl_dir)
    slides_dir = os.path.join(tpl_dir, "ppt", "slides")
    tags_dir = os.path.join(tpl_dir, "ppt", "tags")
    ct_path = os.path.join(tpl_dir, "[Content_Types].xml")

    # 读出模板所有页 xml
    tpl_xml = {}
    for f in os.listdir(slides_dir):
        if re.fullmatch(r"slide\d+\.xml", f):
            n = int(re.search(r"\d+", f).group())
            tpl_xml[n] = open(os.path.join(slides_dir, f), encoding="utf-8").read()

    # 2) 统计现有 tags，准备为新复制页生成独立 tag
    existing_tags = [f for f in os.listdir(tags_dir) if f.startswith("tag")]
    next_tag = max(int(re.search(r"\d+", t).group()) for t in existing_tags) + 1 \
        if existing_tags else 1

    # 3) 生成内容页
    page_xmls = []          # [(xml, 来源模板页号, 是否为复制件)]
    for idx, (tplno, is_dup, mapping_in) in enumerate(PAGES, 1):
        xml = tpl_xml[tplno]
        mapping = dict(mapping_in)
        if tplno == 2:
            mapping = build_toc_mapping(xml)
        for sid, texts in mapping.items():
            xml = set_shape_text(xml, sid, texts)
        for sid, sz in FONT_SHRINKS.get(idx, {}).items():
            xml = shrink_shape_font(xml, sid, sz)
        page_xmls.append((xml, tplno, is_dup))
        if VERBOSE:
            ts = [t for t in txts_of(xml) if t.strip()]
            print("  P%02d <- tpl%-2d%s :: %s" % (idx, tplno, " (复制)" if is_dup else "", " | ".join(ts)[:95]))

    # 4) 写回：新页面按序命名 slide1..slideN
    #    先清空模板原有 slide + rels，再逐页写出
    for f in list(os.listdir(slides_dir)):
        p = os.path.join(slides_dir, f)
        if os.path.isfile(p):
            os.remove(p)
    rels_dir = os.path.join(slides_dir, "_rels")
    if os.path.isdir(rels_dir):
        shutil.rmtree(rels_dir, ignore_errors=True)
    os.makedirs(rels_dir, exist_ok=True)

    # 读出模板每页的 rels（按页号）
    tpl_rels = {}
    # 需在删除前读——所以改为从 tpl 解包目录的另一个备份读
    # 这里重新解包一次到 orig 目录专供 rels 取用
    orig = os.path.join(WORK, "orig")
    unzip(TPL, orig)
    for f in os.listdir(os.path.join(orig, "ppt", "slides", "_rels")):
        mm = re.fullmatch(r"slide(\d+)\.xml\.rels", f)
        if mm:
            tpl_rels[int(mm.group(1))] = \
                open(os.path.join(orig, "ppt", "slides", "_rels", f), encoding="utf-8").read()

    tag_assign = []          # 每页分配到的 tag 文件名（复制件新生成）
    used_tags = []
    for idx, (xml, tplno, is_dup) in enumerate(page_xmls, 1):
        p = os.path.join(slides_dir, "slide%d.xml" % idx)
        open(p, "w", encoding="utf-8", newline="").write(xml)

        rels = tpl_rels.get(tplno, "")
        if is_dup:
            # 复制件必须换用独立的 tag 部件
            newname = "tag%d.xml" % next_tag
            next_tag += 1
            # 复制源 tag 内容
            src_tag = None
            for t in re.findall(r'Target="\.\./tags/(tag\d+\.xml)"', rels):
                src_tag = t
            if src_tag is None:
                # 源页没有 tag 关系也要建一个空的
                open(os.path.join(tags_dir, newname), "w", encoding="utf-8").write(
                    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
                    '<p:tags xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"/>')
            else:
                shutil.copyfile(os.path.join(tags_dir, src_tag),
                                os.path.join(tags_dir, newname))
            rels = rels.replace(src_tag, newname)
            used_tags.append(newname)
        # 取该页用到的 tag（供 Content_Types / 记录）
        for t in re.findall(r'Target="\.\./tags/(tag\d+\.xml)"', rels):
            tag_assign.append(t)
        rp = os.path.join(rels_dir, "slide%d.xml.rels" % idx)
        open(rp, "w", encoding="utf-8", newline="").write(rels)

    # 5) 重写 presentation.xml 的 sldIdLst
    pres_path = os.path.join(tpl_dir, "ppt", "presentation.xml")
    pres = open(pres_path, encoding="utf-8").read()
    presrels_path = os.path.join(tpl_dir, "ppt", "_rels", "presentation.xml.rels")
    presrels = open(presrels_path, encoding="utf-8").read()

    n = len(page_xmls)
    # 保留非 slide 的关系，重建 slide 关系。
    # ⚠️ 不能用 '/slides/slide' not in r 过滤：模板里 Target 写作 "slides/slideN.xml"
    #    （无前导斜杠），该判断会漏掉全部旧 slide 关系，导致指向已删除页面的悬空关系。
    #    改为解析 Type 属性末尾，只保留非 slide 类型。
    other_rels = []
    slide_rel_ids = []
    for r in re.findall(r"<Relationship\b[^>]*/>", presrels):
        ty = re.search(r'Type="[^"]*?/?([A-Za-z]+)"', r)
        kind = ty.group(1) if ty else ""
        rid = re.search(r'Id="([^"]+)"', r)
        if kind.lower() == "slide":
            if rid:
                slide_rel_ids.append(rid.group(1))
            continue
        other_rels.append(r)
    slide_rels = []
    for i in range(1, n + 1):
        slide_rels.append(
            '<Relationship Id="rIdSlide%d" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" '
            'Target="slides/slide%d.xml"/>' % (i, i))
    # rels 根元素必须用正则精确定位（find('<Relationship') 会撞上 <Relationships）
    mroot = re.search(r"<Relationships\b[^>]*>", presrels)
    head = presrels[:mroot.end()]
    newpresrels = head + "".join(slide_rels + other_rels) + "</Relationships>"
    open(presrels_path, "w", encoding="utf-8", newline="").write(newpresrels)
    if VERBOSE:
        print("  剔除旧 slide 关系 %d 条，保留其他 %d 条" %
              (len(slide_rel_ids), len(other_rels)))

    # sldIdLst
    sldids = "".join('<p:sldId id="%d" r:id="rIdSlide%d"/>' % (256 + i, i)
                     for i in range(1, n + 1))
    pres = re.sub(r"<p:sldIdLst>.*?</p:sldIdLst>",
                  "<p:sldIdLst>%s</p:sldIdLst>" % sldids, pres, flags=re.S)
    open(pres_path, "w", encoding="utf-8", newline="").write(pres)

    # 6) Content_Types：幻灯片重编号后，要为「实际存在的」slide 与 tag 全部声明 Override。
    #    ⚠️ 不能只声明被引用的 tag：模板自带的 tag 文件仍在包里，
    #    Content_Types 缺声明会让 PowerPoint 判定包损坏。
    ct = open(ct_path, encoding="utf-8").read()
    ct = re.sub(r'<Override PartName="/ppt/slides/slide\d+\.xml"[^>]*/>', "", ct)
    ct = re.sub(r'<Override PartName="/ppt/tags/tag\d+\.xml"[^>]*/>', "", ct)
    add = []
    for i in range(1, n + 1):
        add.append('<Override PartName="/ppt/slides/slide%d.xml" '
                   'ContentType="application/vnd.openxmlformats-officedocument.'
                   'presentationml.slide+xml"/>' % i)
    # 磁盘上实际存在的所有 tag 文件（含新生成的复制件）
    disk_tags = sorted([f for f in os.listdir(tags_dir)
                        if re.fullmatch(r"tag\d+\.xml", f)],
                       key=lambda x: int(re.search(r"\d+", x).group()))
    for t in disk_tags:
        add.append('<Override PartName="/ppt/tags/%s" '
                   'ContentType="application/vnd.openxmlformats-officedocument.'
                   'presentationml.tags+xml"/>' % t)
    ct = ct.replace("</Types>", "".join(add) + "</Types>")
    open(ct_path, "w", encoding="utf-8", newline="").write(ct)
    if VERBOSE:
        print("  Content_Types: 声明 %d 页 + %d 个 tag" % (n, len(disk_tags)))

    # 7) 打包（沙箱禁用 os.remove，故写到临时文件再由外层覆盖）
    tmp_out = os.path.join(WORK, "out.pptx")
    if os.path.exists(tmp_out):
        os.remove(tmp_out)
    files = []
    for root, dirs, fs in os.walk(tpl_dir):
        for f in fs:
            full = os.path.join(root, f)
            rel = os.path.relpath(full, tpl_dir).replace("\\", "/")
            files.append((full, rel))
    files.sort(key=lambda x: (x[1] != "[Content_Types].xml", x[1]))
    with zipfile.ZipFile(tmp_out, "w", zipfile.ZIP_DEFLATED) as z:
        for full, rel in files:
            z.write(full, rel)
    print("\n已写出临时包: %s" % tmp_out)
    print("页数: %d  大小: %.1f KB" % (n, os.path.getsize(tmp_out) / 1024))
    print("目标: %s" % OUT)


if __name__ == "__main__":
    main()
