# -*- coding: utf-8 -*-
"""按字段名定位：列出所有「缺陷编号」「缺陷标题」后的取值，还原 5+3 个缺陷条目。"""
import re

SRC = r"E:\0_work\1shijian\Software_testing\test_results\_m2_defect_doc.txt"
OUT = r"E:\0_work\1shijian\Software_testing\test_results\_m2_defect_summary.txt"

text = open(SRC, encoding="utf-8", errors="replace").read()
flat = re.sub(r"[\s\u3000]+", " ", text)

lines = []
lines.append("总长度: %d 字符" % len(flat))
lines.append("")

for field, win in [("缺陷编号", 40), ("缺陷标题", 130), ("用例编号", 40)]:
    lines.append("=" * 72)
    lines.append("字段: %s" % field)
    lines.append("=" * 72)
    for i, m in enumerate(re.finditer(field, flat)):
        seg = flat[m.end(): m.end() + win].strip()
        lines.append("  #%02d  %s" % (i + 1, seg))
    lines.append("")

open(OUT, "w", encoding="utf-8").write("\n".join(lines))
print("WROTE", OUT)
