# -*- coding: utf-8 -*-
"""导出缺陷报告各表格的行摘要（block.table.cells 结构）。"""
import json
import subprocess

EDSDK_DIR = r"D:\Users\LENOVO\AppData\Local\Programs\WorkBuddy\resources\app.asar.unpacked\resources\plugins\workbuddy-builtin\skills\tencent-local-office-edit"
PY = r"C:\Users\LENOVO\.workbuddy\binaries\python\envs\default\Scripts\python.exe"
FILE_ID = "8426d2d7-9376-4df1-930d-b9bf54ab4eb6"
OUT = r"E:\0_work\1shijian\Software_testing\test_results\_m2_tables.txt"

TABLES = [
    ("rb38fy7d", "1.4 参考资料"),
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
    lines.append("=" * 74)
    lines.append("%s  (table_id=%s)" % (label, table_id))
    lines.append("=" * 74)
    raw = (proc.stdout or "").strip()
    try:
        data = json.loads(raw)
    except Exception as exc:
        lines.append("解析失败: %s | 原始: %s" % (exc, raw[:300]))
        lines.append("")
        continue

    table = ((data.get("block") or {}).get("table") or {})
    cells = table.get("cells") or []
    rows = {}
    for c in cells:
        rows.setdefault(c.get("row"), []).append(c)
    lines.append("row_count=%s col_count=%s" % (table.get("row_count"), table.get("col_count")))
    for r in sorted(k for k in rows if isinstance(k, int)):
        items = sorted(rows[r], key=lambda x: x.get("col") or 0)
        texts = [(c.get("text") or "").replace("\n", " ").strip() for c in items]
        merged = " || ".join(t[:26] for t in texts[:2])
        lines.append("R%02d | %s" % (r, merged))
    lines.append("")

open(OUT, "w", encoding="utf-8").write("\n".join(lines))
print("WROTE", OUT, len(lines), "lines")
