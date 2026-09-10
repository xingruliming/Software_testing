# -*- coding: utf-8 -*-
"""用真实函数体验证端口探测：7860 应判定为占用，7861 应判定为空闲。"""
import ast
import socket

SRC = r"E:\办公\研一\1软件实践\Software_testing\vggt-main\demo_gradio_cn.py"
with open(SRC, "r", encoding="utf-8") as f:
    source = f.read()

tree = ast.parse(source)
func_src = None
for node in tree.body:
    if isinstance(node, ast.FunctionDef) and node.name == "is_port_free":
        func_src = ast.get_source_segment(source, node)
assert func_src, "未找到 is_port_free"

ns = {"socket": socket}
exec(func_src, ns)
is_port_free = ns["is_port_free"]
print("已提取 is_port_free 真实函数体\n")

# 先确认 7860 确实被占用
occupied = None
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    try:
        s.bind(("127.0.0.1", 7860))
        s.close()
        occupied = False
    except OSError:
        occupied = True
print(f"netstat 侧确认 7860 是否被占用: {occupied}")

r7860 = is_port_free(7860)
r7861 = is_port_free(7861)
print(f"is_port_free(7860) = {r7860}   (期望 False)")
print(f"is_port_free(7861) = {r7861}   (期望 True)")

ok = True
if occupied and r7860 is not False:
    ok = False
if r7861 is not True:
    ok = False

print()
print(">>> 端口探测行为正确" if ok else ">>> 端口探测行为异常")
raise SystemExit(0 if ok else 1)
