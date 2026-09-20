# -*- coding: utf-8 -*-
"""输出各缺陷表 R21（关闭人员 / 复测结果）的完整文本，供追加自动化回归入口。"""
import json
import subprocess

EDSDK_DIR = r"D:\Users\LENOVO\AppData\Local\Programs\WorkBuddy\resources\app.asar.unpacked\resources\plugins\workbuddy-builtin\skills\tencent-local-office-edit"
PY = r"C:\Users\LENOVO\.workbuddy\binaries\python\envs\default\Scripts\python.exe"
FILE_ID = "8426d2d7-9376-4df1-930d-b9bf54ab4eb6"
OUT = r"E:\0_work\1shijian\Software_testing\test_results\_m2_r21.txt"

TABLES = [
    ("gpyjpbrv", "DEF-M2-001"),
    ("yq0kyr17", "DEF-M2-002"),
    ("8lhnohlc", "DEF-M2-003"),
    ("grlpc2gv", "DEF-M2-004"),
    ("rcdd1mow", "DEF-M2-005"),
]

lines = []
for table_id, label in TABLES:
    proc = subprocess.run(
        [PY, "edsdk.py", "call", "doc_get_table_info", "file_id=%s" % FILE_ID,
         "table_id=%s" % table_id],
        cwd=EDSDK_DIR, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    data = json.loads((proc.stdout or "").strip())
    cells = ((data.get("block") or {}).get("table") or {}).get("cells") or []
    target = [c for c in cells if c.get("row") == 21 and c.get("col") == 2]
    lines.append("%s  table_id=%s" % (label, table_id))
    lines.append("R21C1(标签): %r" % ([c for c in cells if c.get("row") == 21 and c.get("col") == 1][0].get("text")))
    lines.append("R21C2(原文): %s" % (target[0].get("text") if target else "(缺失)"))
    lines.append("")

open(OUT, "w", encoding="utf-8").write("\n".join(lines))
print("WROTE", OUT)
print("\n".join(lines))
