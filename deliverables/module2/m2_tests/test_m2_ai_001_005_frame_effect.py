# -*- coding: utf-8 -*-
"""M2-AI-001 ~ M2-AI-005：帧数效应与自洽性基线。

覆盖用例清单中的：
    001 基准场景自洽性基线测量（9 帧）
    002 帧数减少至 5 帧的自洽性退化
    003 帧数减少至 2 帧的自洽性退化
    004 单帧输入时光度一致性指标应不可用
    005 帧数—指标单调性检验（1→2→5→9）

数据来源：``vggt_output/002_computer/predictions.npz``（基线，9 帧）与
``vggt_output/exp/N1|N2|N5``（由 tools/robustness_experiments.py 生成，
缺失时按需现场生成）。
"""

import json
import unittest

from m2_tests import common as C


class TestFrameEffect(unittest.TestCase):
    """帧数效应：多视角冗余是自洽性的主要来源。"""

    @classmethod
    def setUpClass(cls):
        cls.base_npz = C.scene_npz(C.BASE_SCENE)
        if not cls.base_npz.is_file():
            raise unittest.SkipTest("缺少基线产物 %s，请先跑一次 run_vggt_inference.py" % cls.base_npz)
        cls.base = C.metrics_of(cls.base_npz, C.CONF_DEFAULT)

    # ---------------- M2-AI-001 ----------------
    def test_m2_ai_001_baseline_self_consistency(self):
        """M2-AI-001 基准场景自洽性基线测量（002_computer，9 帧，conf_thres=3.0）。

        预期：四项自洽性指标均可统计，且落在可用区间；产物完整。
        """
        res = self.base
        self.assertEqual(res.get("num_frames"), 9, "基线应为 9 帧输入")
        for name in ("pointmap_vs_depth", "pointmap_vs_camera", "confidence", "photometric"):
            self.assertTrue(C.is_available(res, name), "指标 %s 应可统计" % name)

        g1 = C.g1_rel(res)
        self.assertLess(g1, 5e-3, "G1 点图 vs 深度反投影的相对误差应小于 5e-3，实测 %.4g" % g1)

        g2 = C.g2_px(res)
        self.assertLess(g2, 5.0, "G2 平均重投影像素误差应小于 5 px，实测 %.4g" % g2)
        lt5 = C.pick(res, "pointmap_vs_camera").get("pix_err_lt5px_ratio")
        self.assertGreater(lt5, 0.95, "G2 落在 5 px 内的像素占比应超过 95%%，实测 %.4g" % lt5)

        conf_mean = C.g3_conf_mean(res)
        self.assertGreater(conf_mean, 5.0, "G3 深度置信均值应大于 5，实测 %.4g" % conf_mean)

        ncc = C.g4_ncc(res)
        self.assertGreater(ncc, 0.8, "G4 光度一致性 NCC 应大于 0.8，实测 %.4g" % ncc)

        # —— 产物完整性：深度图张数、GLB、峰值显存 ——
        info_path = C.scene_dir(C.BASE_SCENE) / "run_info.json"
        self.assertTrue(info_path.is_file(), "应存在 run_info.json")
        info = json.loads(info_path.read_text(encoding="utf-8"))

        depth_images = info.get("depth_images") or []
        self.assertEqual(len(depth_images), 9, "深度图应为 9 张（与帧数一致）")
        for rel in depth_images:
            p = C.scene_dir(C.BASE_SCENE) / rel
            self.assertTrue(p.is_file(), "深度图缺失：%s" % p)
            self.assertGreater(p.stat().st_size, 0, "深度图为空文件：%s" % p)

        glb_files = info.get("glb_files") or []
        self.assertEqual(len(glb_files), 2, "应导出两个预测分支的 GLB")
        for rel in glb_files:
            p = C.scene_dir(C.BASE_SCENE) / rel
            self.assertTrue(p.is_file(), "GLB 缺失：%s" % p)
            self.assertGreater(C.size_mb(p), 1.0, "GLB 体积异常偏小：%s" % p)

        peak = (info.get("inference") or {}).get("peak_gpu_memory_gb")
        self.assertIsNotNone(peak, "run_info.json 应记录峰值显存")
        self.assertLessEqual(peak, 8.6, "峰值显存应不超过 8.6 GB，实测 %s GB" % peak)

    # ---------------- M2-AI-002 ----------------
    def test_m2_ai_002_five_frames_degrade(self):
        """M2-AI-002 帧数减少至 5 帧的自洽性退化。

        预期：各项指标相对 9 帧基线退化（G1 相对误差变大），但仍可统计。
        """
        res = C.metrics_of(C.need_variant("N5"), C.CONF_DEFAULT)
        self.assertTrue(C.is_available(res, "pointmap_vs_depth"), "G1 应仍可统计")
        self.assertEqual(res.get("num_frames"), 5, "N5 变体应为 5 帧")

        base_g1 = C.g1_rel(self.base)
        g1 = C.g1_rel(res)
        self.assertGreater(g1, base_g1, "5 帧的 G1 相对误差应大于 9 帧基线：%.4g 应 > %.4g" % (g1, base_g1))

    # ---------------- M2-AI-003 ----------------
    def test_m2_ai_003_two_frames_degrade_further(self):
        """M2-AI-003 帧数减少至 2 帧的自洽性退化。

        预期：指标相对 5 帧进一步退化。
        """
        n5 = C.metrics_of(C.need_variant("N5"), C.CONF_DEFAULT)
        res = C.metrics_of(C.need_variant("N2"), C.CONF_DEFAULT)
        self.assertTrue(C.is_available(res, "pointmap_vs_depth"), "G1 应仍可统计")
        self.assertEqual(res.get("num_frames"), 2, "N2 变体应为 2 帧")

        g1 = C.g1_rel(res)
        g1_n5 = C.g1_rel(n5)
        self.assertGreater(g1, g1_n5, "2 帧的 G1 相对误差应大于 5 帧：%.4g 应 > %.4g" % (g1, g1_n5))

    # ---------------- M2-AI-004 ----------------
    def test_m2_ai_004_single_frame_g4_unavailable(self):
        """M2-AI-004 单帧输入时光度一致性指标应不可用。

        预期：G4 因缺少帧对而报告不可用，而不是给出错误数值；G1–G3 仍可统计。
        """
        res = C.metrics_of(C.need_variant("N1"), C.CONF_DEFAULT)
        self.assertEqual(res.get("num_frames"), 1, "N1 变体应为单帧")

        self.assertFalse(
            C.is_available(res, "photometric"),
            "单帧时 G4 光度一致性应报告不可用（无帧对），实际却给出了数值：%s"
            % C.pick(res, "photometric"),
        )
        for name in ("pointmap_vs_depth", "pointmap_vs_camera", "confidence"):
            self.assertTrue(C.is_available(res, name), "%s 在单帧下应仍可统计" % name)

    # ---------------- M2-AI-005 ----------------
    def test_m2_ai_005_monotonic_improvement_with_frames(self):
        """M2-AI-005 帧数—指标单调性检验（1→2→5→9）。

        预期：帧数增加时 G1 相对误差单调下降、G3 深度置信均值单调上升。
        """
        chain = []
        for label, npz in (
            ("N1", C.need_variant("N1")),
            ("N2", C.need_variant("N2")),
            ("N5", C.need_variant("N5")),
        ):
            chain.append((label, C.metrics_of(npz, C.CONF_DEFAULT)))
        chain.append(("BASE(9帧)", self.base))

        g1_series = [(label, C.g1_rel(res)) for label, res in chain]
        conf_series = [(label, C.g3_conf_mean(res)) for label, res in chain]

        for (lab_a, a), (lab_b, b) in zip(g1_series, g1_series[1:]):
            self.assertGreater(
                a, b, "G1 相对误差应随帧数单调下降，但 %s=%.4g 未大于 %s=%.4g" % (lab_a, a, lab_b, b)
            )
        for (lab_a, a), (lab_b, b) in zip(conf_series, conf_series[1:]):
            self.assertLess(
                a, b, "G3 深度置信均值应随帧数单调上升，但 %s=%.4g 未小于 %s=%.4g" % (lab_a, a, lab_b, b)
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
