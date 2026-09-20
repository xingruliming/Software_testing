# -*- coding: utf-8 -*-
"""把 Word 提取的纯文本（段落以 \r 分隔）切成多行，便于按段阅读与定位。"""
import re

SRC = r"E:\0_work\1shijian\Software_testing\test_results\_m2_defect_doc.txt"
OUT = r"E:\0_work\1shijian\Software_testing\test_results\_m2_defect_lines.txt"

text = open(SRC, encoding="utf-8", errors="replace").read()
# Word Content.Text: 段落分隔为 \r；表格单元格之间常见 \x07
parts = re.split(r"[\r\n]+", text)
lines = []
for i, seg in enumerate(parts):
    seg = seg.replace("\x07", " | ").strip()
    if seg:
        lines.append("L%03d | %s" % (i, seg))
        lines.append("")

open(OUT, "w", encoding="utf-8").write("\n".join(lines))
print("WROTE", OUT, len(lines), "lines")
