# -*- coding: utf-8 -*-
"""校验 pptx 包完整性：zip 可读、XML 可解析、关系目标存在、Content_Types 自洽。"""
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

path = sys.argv[1]
z = zipfile.ZipFile(path)
bad = z.testzip()
print("zip 完整性:", "OK" if bad is None else ("损坏: %s" % bad))

names = set(z.namelist())
# 1) 所有 XML 可解析
errs = []
for n in names:
    if n.endswith((".xml", ".rels")):
        try:
            ET.fromstring(z.read(n))
        except Exception as e:
            errs.append("%s :: %s" % (n, e))
print("XML 解析:", "OK (%d 个文件)" % sum(1 for n in names if n.endswith(('.xml', '.rels')))
      if not errs else "失败")
for e in errs:
    print("   ", e)

# 2) 所有 rels 的目标存在
miss = []
for n in names:
    if not n.endswith(".rels"):
        continue
    # 计算 rels 所属部件的目录：ppt/_rels/x.xml.rels -> ppt/
    #                      _rels/.rels           -> （包根）
    if n == "_rels/.rels":
        base = ""
    else:
        base = n.rsplit("/_rels/", 1)[0] + "/"
    root = ET.fromstring(z.read(n))
    for r in root:
        if r.tag.endswith("Relationship") and r.get("TargetMode") != "External":
            t = r.get("Target")
            tgt = t.lstrip("/") if t.startswith("/") else base + t
            # 归一化 ../
            parts = []
            for seg in tgt.split("/"):
                if seg == "..":
                    if parts:
                        parts.pop()
                elif seg and seg != ".":
                    parts.append(seg)
            tgt = "/".join(parts)
            if tgt not in names:
                miss.append("%s -> %s" % (n, tgt))
print("关系目标:", "全部存在" if not miss else "缺失 %d 个" % len(miss))
for m in miss:
    print("   ", m)

# 3) Content_Types 覆盖所有 slide / tags
ct = z.read("[Content_Types].xml").decode("utf-8")
slides = [n for n in names if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)]
tags = [n for n in names if re.fullmatch(r"ppt/tags/tag\d+\.xml", n)]
for n in slides + tags:
    if ('PartName="/%s"' % n) not in ct:
        print("   !! Content_Types 未声明:", n)
print("Content_Types: slides=%d tags=%d" % (len(slides), len(tags)))

# 4) sldIdLst <-> slide 文件一一对应
pres = z.read("ppt/presentation.xml").decode("utf-8")
prels = ET.fromstring(z.read("ppt/_rels/presentation.xml.rels"))
rmap = {r.get("Id"): r.get("Target") for r in prels}
order = re.findall(r'<p:sldId id="(\d+)" r:id="([^"]+)"', pres)
print("sldIdLst 页数:", len(order), "| slide 文件数:", len(slides))
seen = []
for sid, rid in order:
    t = rmap.get(rid)
    seen.append("ppt/" + t if not t.startswith("/") else t.lstrip("/"))
ok = seen == sorted(slides, key=lambda x: int(re.search(r"\d+", x.split("/")[-1]).group()))
print("页序映射:", "OK" if ok else "不一致")
if not ok:
    print("   sldIdLst:", seen)
    print("   实际文件:", sorted(slides))

# 5) 每个 slide 的 tag 部件是否唯一
used_tags = {}
dup = []
for n in slides:
    rel = n.rsplit("/", 1)[0] + "/_rels/" + n.split("/")[-1] + ".rels"
    if rel not in names:
        dup.append("%s 无 rels" % n)
        continue
    root = ET.fromstring(z.read(rel))
    for r in root:
        t = r.get("Target", "")
        if "/tags/" in t:
            fn = t.split("/")[-1]
            if fn in used_tags:
                dup.append("%s 与 %s 共用 tag %s" % (n, used_tags[fn], fn))
            used_tags[fn] = n
print("tag 独占性:", "OK（每页独立）" if not dup else "冲突")
for d in dup:
    print("   ", d)

# 6) 占位文残留检查
placeholder = ["请输入标题", "点击输入文字", "点击此处输入内容", "您的正文已经",
               "PLEASE ENTER", "DAILY REPORT", "点击此处输入你想要表达的内容", "您的标题",
               "这里输入您的内容", "华中大", "研小招", "学术报告", "论文答辩", "XX.0",
               "202X", "模板"]
print("\n占位文残留扫描:")
found = False
for n in slides:
    txt = "".join(re.findall(r"<a:t>(.*?)</a:t>", z.read(n).decode("utf-8")))
    hits = [p for p in placeholder if p in txt]
    if hits:
        found = True
        print("   %s :: %s" % (n, hits))
if not found:
    print("   无残留")

# 7) 字体检查
fonts = set()
for n in slides:
    fonts.update(re.findall(r'typeface="([^"]+)"', z.read(n).decode("utf-8")))
print("\n使用字体:", sorted(fonts))
