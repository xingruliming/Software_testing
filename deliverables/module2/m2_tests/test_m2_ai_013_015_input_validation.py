# -*- coding: utf-8 -*-
"""M2-AI-013 ~ M2-AI-015：推理入口的输入校验（异常输入）。

覆盖用例清单中的：
    013 空输入目录的异常处理
    014 输入目录不存在的异常处理
    015 损坏图像文件的异常处理            （清单判定：NG）

本组用例与其他用例不同：不针对已有产物做断言，而是**真实调用**
``run_vggt_inference.py``（子进程），检查报错信息、退出码与残留产物。

013/014 在校验阶段即结束（秒级，不需要加载权重）；
015 会走到图像解码阶段（需要权重与 CUDA，约 30 s）。

M2-AI-015 是清单中第二条失败用例：损坏图像会让流程抛出未捕获的
PIL.UnidentifiedImageError 原始堆栈，并残留半成品输出目录，
对应缺陷 DEF-M2-001（异常处理不一致）。
"""

import time
import unittest

from m2_tests import common as C


def _run_dir(name: str):
    return C.make_temp_case_dir(name)


class TestInputValidation(unittest.TestCase):
    """推理入口对异常输入的校验一致性。"""

    # ---------------- M2-AI-013 ----------------
    def test_m2_ai_013_empty_input_directory(self):
        """M2-AI-013 空输入目录的异常处理。

        预期：给出明确的中文错误提示，以非零退出码结束，且不创建输出目录。
        """
        ts = time.strftime("%Y%m%d_%H%M%S")
        in_dir = _run_dir("empty_input_%s" % ts)
        out_dir = _run_dir("empty_out_%s_should_not_exist" % ts)
        in_dir.mkdir(parents=True, exist_ok=True)

        proc = C.run_inference(in_dir, out_dir, timeout=600)
        combined = (proc.stdout or "") + (proc.stderr or "")

        self.assertNotEqual(proc.returncode, 0, "空目录应以非零退出码结束")
        self.assertIn(
            "[错误] 输入目录中没有图像", combined,
            "应给出明确的中文提示「输入目录中没有图像」，实际输出：%s" % combined[-500:],
        )
        self.assertFalse(
            out_dir.exists(),
            "校验失败时不应创建输出目录，实际已创建：%s" % out_dir,
        )

    # ---------------- M2-AI-014 ----------------
    def test_m2_ai_014_missing_input_directory(self):
        """M2-AI-014 输入目录不存在的异常处理。

        预期：给出明确的中文错误提示，以非零退出码结束。
        """
        ts = time.strftime("%Y%m%d_%H%M%S")
        in_dir = _run_dir("no_such_dir_%s" % ts)          # 故意不创建
        out_dir = _run_dir("missing_out_%s" % ts)

        proc = C.run_inference(in_dir, out_dir, timeout=600)
        combined = (proc.stdout or "") + (proc.stderr or "")

        self.assertNotEqual(proc.returncode, 0, "目录不存在应以非零退出码结束")
        self.assertIn(
            "[错误] 输入目录不存在", combined,
            "应给出明确的中文提示「输入目录不存在」，实际输出：%s" % combined[-500:],
        )

    # ---------------- M2-AI-015 ----------------
    def test_m2_ai_015_damaged_image_friendly_error(self):
        """M2-AI-015 损坏图像文件的异常处理。

        预期：给出明确的中文错误提示，以非零退出码结束，且不残留半成品产物。

        实际（当前版本）：抛出未捕获的 PIL.UnidentifiedImageError 原始堆栈，
        并在输出目录残留 images/（已写入图像副本、无 predictions.npz）——
        对应缺陷 DEF-M2-001。
        """
        if not C.MODEL_PATH.is_file():
            self.skipTest("缺少模型权重 %s，无法执行该用例" % C.MODEL_PATH)
        if not C.cuda_available():
            self.skipTest("当前解释器无可用 CUDA，无法执行推理链路用例")

        ts = time.strftime("%Y%m%d_%H%M%S")
        in_dir = _run_dir("damaged_input_%s" % ts)
        out_dir = _run_dir("damaged_out_%s" % ts)
        in_dir.mkdir(parents=True, exist_ok=True)
        (in_dir / "broken.jpg").write_bytes(b"not an image")

        proc = C.run_inference(in_dir, out_dir, timeout=900)
        combined = (proc.stdout or "") + (proc.stderr or "")

        friendly = any(token in combined for token in ("[错误]", "无法解码", "无法打开", "无法识别"))
        leftovers = []
        if out_dir.exists():
            leftovers = sorted(
                str(p.relative_to(out_dir)).replace("\\", "/") for p in out_dir.rglob("*")
            )

        # 退出码：非零（当前已满足）
        self.assertNotEqual(proc.returncode, 0, "损坏图像应以非零退出码结束")

        with self.subTest("报错信息应为面向用户的中文提示"):
            self.assertTrue(
                friendly,
                "损坏图像应给出明确的中文错误提示，而不是暴露内部异常堆栈。"
                "实际输出末尾：%s" % combined[-800:],
            )
            self.assertNotIn(
                "UnidentifiedImageError", combined,
                "不应把 PIL 内部异常类型直接暴露给使用者（缺陷 DEF-M2-001）",
            )

        with self.subTest("失败后不应残留半成品产物"):
            self.assertEqual(
                leftovers, [],
                "推理失败后不应残留半成品输出目录内容（缺陷 DEF-M2-001），实际残留：%s" % leftovers,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
