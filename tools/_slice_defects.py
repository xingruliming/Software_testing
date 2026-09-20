# -*- coding: utf-8 -*-
"""从缺陷报告纯文本中切出 DEF-M2-00x 的上下文片段，便于核对缺陷定义。"""
import re

SRC = r"E:\0_work\1shijian\Software_testing\test_results\_m2_defect_doc.txt"
OUT = r"E:\0_work\1shijian\Software_testing\test_results\_m2_defect_slices.txt"

text = open(SRC, encoding="utf-8", errors="replace").read()
# 去掉 Word 粘出来的多余空白
text = re.sub(r"[ \t]+", " ", text)

lines = []
for tag in ["DEF-M2-001", "DEF-M2-002", "DEF-M2-003", "DEF-M2-004", "DEF-M2-005",
            "T-M2-001", "T-M2-002", "T-M2-003"]:
    idxs = [m.start() for m in re.finditer(re.escape(tag), text)]
    lines.append("=" * 78)
    lines.append("%s  出现 %d 次" % (tag, len(idxs)))
    lines.append("=" * 78)
    for i, pos in enumerate(idxs[:4]):
        seg = text[max(0, pos - 120): pos + 700]
        lines.append("--- #%d ---" % (i + 1))
        lines.append(seg)
        lines.append("")
    lines.append("")

open(OUT, "w", encoding="utf-8").write("\n".join(lines))
print("WROTE", OUT, len(lines), "lines")
