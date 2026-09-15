# -*- coding: utf-8 -*-
"""探针：复现 P07 处理后 sp_block 找不到 id=42 的问题。"""
import os
import re
import sys

sys.path.insert(0, r"E:\0_work\1shijian\Software_testing\tools")
import importlib.util

spec = importlib.util.spec_from_file_location(
    "rb", r"E:\0_work\1shijian\Software_testing\tools\_rebuild_deck.py")
rb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rb)  # 只加载定义，不执行 main（__name__ != __main__）

import zipfile

with zipfile.ZipFile(rb.TPL) as z:
    xml = z.read("ppt/slides/slide5.xml").decode("utf-8")

print("id=42 in tpl xml:", 'id="42"' in xml)

mapping = {
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
}
for sid, texts in mapping.items():
    before = 'id="%d"' % sid in xml
    try:
        xml = rb.set_shape_text(xml, sid, texts)
        ok = "OK"
    except Exception as e:
        ok = "FAIL: %s" % e
    print("set %-3d before=%s %s" % (sid, before, ok))

for sid in (17, 42, 48, 53):
    print("after: id=%d exists: %s" % (sid, 'id="%d"' % sid in xml))
    m = rb.sp_block(xml, sid)
    print("after: sp_block(%d): %s" % (sid, "found" if m else "NOT FOUND"))

print("---- shrink 链路复现 ----")
xml2 = z_read = None
with zipfile.ZipFile(rb.TPL) as z:
    xml2 = z.read("ppt/slides/slide5.xml").decode("utf-8")
for sid, texts in mapping.items():
    xml2 = rb.set_shape_text(xml2, sid, texts)
for sid, sz in rb.FONT_SHRINKS[7].items():
    m = rb.sp_block(xml2, sid)
    print("shrink %d: %s (blk len=%s)" % (sid, "found" if m else "NOT FOUND",
                                         len(m.group(0)) if m else "-"))
    if m:
        xml2 = rb.shrink_shape_font(xml2, sid, sz)
    else:
        # 打印当前 xml 里所有 cNvPr id，辅助定位
        ids = re.findall(r'<p:cNvPr id="(\d+)"', xml2)
        print("  remaining ids:", ids)
        break
