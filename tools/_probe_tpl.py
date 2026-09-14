# -*- coding: utf-8 -*-
"""探针：列出模板各页每个形状的 id / name / <a:t> 个数 / 文本。"""
import os
import re
import sys

base = r"C:\Users\LENOVO\AppData\Local\Temp\ppt_work\tpl\ppt\slides"
targets = [int(a) for a in sys.argv[1:]] or [1, 2, 3, 4, 5, 6, 7, 8, 13, 15]

for n in targets:
    p = os.path.join(base, "slide%d.xml" % n)
    xml = open(p, encoding="utf-8").read()
    print("=" * 95)
    print("slide%d.xml" % n)
    for m in re.finditer(r"<p:sp>.*?</p:sp>", xml, re.S):
        blk = m.group(0)
        idm = re.search(r'<p:cNvPr id="(\d+)" name="([^"]*)"', blk)
        if not idm:
            continue
        txts = re.findall(r"<a:t>(.*?)</a:t>", blk, re.S)
        j = "|".join(txts)
        if not j.strip():
            continue
        print("  id=%-4s %-16s n_a_t=%-3d :: %s" %
              (idm.group(1), idm.group(2), len(txts), j[:110]))
