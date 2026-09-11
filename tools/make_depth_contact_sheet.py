#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把输出目录里的「输入图像」与「伪彩色深度图」按帧配成对照拼图。

用法：
    python tools/make_depth_contact_sheet.py <output_dir> [每行帧数]

产物：<output_dir>/depth_vs_input_contact_sheet.png
（纯 PIL 读写，天然支持中文路径）
"""

import os
import sys

from PIL import Image, ImageDraw

CELL_W = 320          # 每格宽度（含内边距）
PAD = 6
LABEL_H = 18


def load_row(path, height):
    img = Image.open(path).convert("RGB")
    ratio = height / img.height
    return img.resize((max(1, int(img.width * ratio)), height), Image.LANCZOS)


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    out_dir = os.path.abspath(sys.argv[1])
    per_row = int(sys.argv[2]) if len(sys.argv) > 2 else 3

    images_dir = os.path.join(out_dir, "images")
    depth_dir = os.path.join(out_dir, "depth")

    inputs = sorted(os.listdir(images_dir))
    depths = sorted(f for f in os.listdir(depth_dir) if f.lower().endswith(".png"))
    count = min(len(inputs), len(depths))
    if count == 0:
        raise SystemExit("[错误] 输入图像或深度图为空")

    cell_h = int(CELL_W * 0.75)
    rows = (count + per_row - 1) // per_row
    sheet_w = per_row * (CELL_W + PAD) + PAD
    sheet_h = rows * (2 * (cell_h + LABEL_H) + PAD * 3) + PAD

    sheet = Image.new("RGB", (sheet_w, sheet_h), (245, 245, 247))
    draw = ImageDraw.Draw(sheet)

    for i in range(count):
        r, c = divmod(i, per_row)
        base_x = PAD + c * (CELL_W + PAD)
        block_h = 2 * (cell_h + LABEL_H) + PAD * 3
        base_y = PAD + r * block_h

        for k, (src, tag) in enumerate((
            (os.path.join(images_dir, inputs[i]), f"[{i:02d}] input"),
            (os.path.join(depth_dir, depths[i]), f"[{i:02d}] depth"),
        )):
            thumb = load_row(src, cell_h)
            y = base_y + k * (cell_h + LABEL_H + PAD)
            draw.text((base_x + 2, y + 3), tag, fill=(30, 30, 30))
            sheet.paste(thumb, (base_x + (CELL_W - thumb.width) // 2, y + LABEL_H))

    out_path = os.path.join(out_dir, "depth_vs_input_contact_sheet.png")
    sheet.save(out_path)
    print(f"[完成] {out_path}  ({count} 帧)")


if __name__ == "__main__":
    main()
