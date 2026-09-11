#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OpenCV 中文路径兼容层
=====================

问题
----
Windows 上 OpenCV 会把文件路径按当前 ANSI 码页（简体中文系统为 GBK）处理后
交给 `fopen`，因此**含中文或其它非 ASCII 字符的路径会失败**，而且失败方式
非常隐蔽 —— 不抛异常：

    cv2.imwrite("E:/办公/.../a.png", img)   -> 返回 False，什么都不写
    cv2.imread ("E:/办公/.../a.png")        -> 返回 None，只打一条 WARN

调用方如果不检查返回值，就会表现为「日志说成功、磁盘上没文件」。

解决
----
绕开 OpenCV 自己的路径处理，改由 Python 的文件对象读写字节流：

    读：np.fromfile(path, np.uint8)  ->  cv2.imdecode(buf, flags)
    写：cv2.imencode(ext, img)       ->  open(path, "wb").write(...)   # 顺带支持任意 Unicode 路径

用法
----
    import cv2_unicode
    cv2_unicode.patch()          # 全局替换，之后原代码里的 cv2.imread / cv2.imwrite 自动生效
    image = cv2_unicode.imread(path)      # 也可以显式调用
    cv2_unicode.imwrite(path, image)

    cv2_unicode.is_patched()     # 查询当前是否已启用
    cv2_unicode.unpatch()        # 还原成 OpenCV 原生实现（复现缺陷时用）
"""

import os

import cv2
import numpy as np

# 在 cv2 模块上打的标记，用于保证 patch() 幂等
_PATCH_FLAG = "__unicode_path_patched__"
# 原生实现的备份，供 unpatch() 还原
_originals = {}


def imread(path, flags=cv2.IMREAD_COLOR):
    """
    读取图像，支持任意 Unicode 路径。

    行为对齐 cv2.imread：读不到时返回 None（但会打印可定位的原因）。
    """
    if isinstance(path, os.PathLike):
        path = os.fspath(path)
    if not isinstance(path, str):
        return None
    if not os.path.isfile(path):
        print(f"[cv2_unicode] 文件不存在或不可读: {path}")
        return None

    try:
        buf = np.fromfile(path, dtype=np.uint8)
    except OSError as exc:
        print(f"[cv2_unicode] 读取失败: {path} ({exc})")
        return None

    if buf.size == 0:
        print(f"[cv2_unicode] 文件内容为空: {path}")
        return None

    return cv2.imdecode(buf, flags)


def imwrite(path, img, params=None):
    """
    写出图像，支持任意 Unicode 路径。

    行为对齐 cv2.imwrite：成功返回 True，失败返回 False（不会抛异常）。
    与原生实现的一处差异：会自动创建缺失的父目录。
    """
    if isinstance(path, os.PathLike):
        path = os.fspath(path)
    if not isinstance(path, str):
        return False

    ext = os.path.splitext(path)[1]
    if not ext:
        ext = ".png"

    try:
        ok, buf = cv2.imencode(ext, img, params if params is not None else [])
        if not ok:
            print(f"[cv2_unicode] 编码失败（格式 {ext}）: {path}")
            return False
        parent = os.path.dirname(os.path.abspath(path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "wb") as f:
            f.write(buf.tobytes())
        return True
    except Exception as exc:  # 与 cv2.imwrite 一致：失败不抛异常
        print(f"[cv2_unicode] 写入失败: {path} ({exc})")
        return False


def patch():
    """把 cv2.imread / cv2.imwrite 全局替换为 Unicode 安全版本。幂等。"""
    if getattr(cv2, _PATCH_FLAG, False):
        return False
    _originals.setdefault("imread", cv2.imread)
    _originals.setdefault("imwrite", cv2.imwrite)
    cv2.imread = imread
    cv2.imwrite = imwrite
    setattr(cv2, _PATCH_FLAG, True)
    print("[cv2_unicode] 已启用中文路径兼容层（cv2.imread / cv2.imwrite）")
    return True


def unpatch():
    """还原成 OpenCV 原生实现（复现原始缺陷时使用）。"""
    if not getattr(cv2, _PATCH_FLAG, False):
        return False
    if "imread" in _originals:
        cv2.imread = _originals["imread"]
    if "imwrite" in _originals:
        cv2.imwrite = _originals["imwrite"]
    setattr(cv2, _PATCH_FLAG, False)
    print("[cv2_unicode] 已还原为 OpenCV 原生实现")
    return True


def is_patched():
    """当前是否已启用兼容层。"""
    return bool(getattr(cv2, _PATCH_FLAG, False))
