# 输入图片说明

- `extreme_wide_518x1.png`：尺寸为 `518×1` 的纯红色 RGB PNG，用于触发缩放高度被计算为 0 的缺陷。
- `valid_boundary_518x14.png`：尺寸为 `518×14` 的纯绿色 RGB PNG，作为最小补丁高度的有效边界对照。

两张图片由 `generate_input.py` 使用 Pillow 确定性生成，不依赖网络下载。重新运行生成脚本会覆盖为相同尺寸和颜色的输入文件。
