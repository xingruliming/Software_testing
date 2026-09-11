# 固定测试图片说明

本目录保存自动化测试使用的固定输入图片。图片来自 Pillow 官方 GitHub 仓库的测试资源：

| 本地文件 | 原始文件 | 格式 / 模式 / 尺寸 | SHA-256 |
|---|---|---|---|
| `pillow_hopper_rgb.jpg` | `Tests/images/hopper.jpg` | JPEG / RGB / 128×128 | `ffe89a0ab0e94114e10777e7313d7fa83d634e34ebc2ea7479085cffa504c920` |
| `pillow_hopper_rgb.png` | `Tests/images/hopper.png` | PNG / RGB / 128×128 | `dbdcb9a9f8ec2c54ff99e99636059bbd57194ed84e2cca5e53853aef293faf42` |
| `pillow_hopper_gray_4bpp.tif` | `Tests/images/hopper_gray_4bpp.tif` | TIFF / L / 128×128 | `229acfa765dc52d9cb76e16ea769dbed896324c5d172a70a149eaf1b28fc8995` |

来源地址：`https://github.com/python-pillow/Pillow/tree/main/Tests/images`

许可证：Pillow 开源许可证，详见 `https://github.com/python-pillow/Pillow/blob/main/LICENSE`。

固定图片主要用于测试真实文件解码、颜色模式转换和批量输入。需要精确尺寸或精确颜色的边界用例仍在运行时生成临时图片。
