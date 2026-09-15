# -*- coding: utf-8 -*-
"""检查 WPS/PowerPoint 是否打开着目标 PPT（结果写 UTF-8 日志）。"""
import io

import psutil  # type: ignore

names = {"wps", "wpp", "POWERPNT", "wpspdf", "et"}
hits = []
for p in psutil.process_iter(["name"]):
    try:
        n = (p.info["name"] or "").lower().split(".")[0]
        if n in {x.lower() for x in names}:
            hits.append(n)
    except Exception:
        pass
with io.open(r"E:/0_work/1shijian/Software_testing/tools/_lock4.txt", "w", encoding="utf-8") as f:
    f.write("hits: %s\n" % hits)
