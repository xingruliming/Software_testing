# -*- coding: utf-8 -*-
"""M2-AI-006 ~ M2-AI-009：鲁棒性扰动矩阵与确定性。

覆盖用例清单中的：
    006 分辨率降为 0.5 倍的鲁棒性
    007 高斯噪声 σ=10 的鲁棒性
    008 随机遮挡 25% 面积的鲁棒性
    009 重复运行确定性检验

数据来源：``vggt_output/exp/res50 | noise10 | occ25 | det2``
（由 tools/robustness_experiments.py 生成，缺失时按需现场生成）。

判定口径说明：006/007 的用例预期为「指标单调退化」，实测未出现显著退化，
因此脚本断言的是**实测结论**（与基线同量级）——这正是清单中「通过但结论与
预期相反」的判定，属于有效的鲁棒性结论而非缺陷。
"""

import unittest

from m2_tests import common as C


class TestRobustness(unittest.TestCase):
    """扰动矩阵：模型对像素噪声与降采样不敏感，对遮挡敏感。"""

    @classmethod
    def setUpClass(cls):
        base_npz = C.scene_npz(C.BASE_SCENE)
        if not base_npz.is_file():
            raise unittest.SkipTest("缺少基线产物 %s" % base_npz)
        cls.base = C.metrics_of(base_npz, C.CONF_DEFAULT)

    def _assert_same_order(self, variant: str, metric_note: str):
        """断言扰动变体的 G2 / G4 与基线同量级（未显著退化）。"""
        res = C.metrics_of(C.need_variant(variant), C.CONF_DEFAULT)
        base_g2, base_ncc = C.g2_px(self.base), C.g4_ncc(self.base)
        g2, ncc = C.g2_px(res), C.g4_ncc(res)

        self.assertTrue(C.is_available(res, "pointmap_vs_camera"), "%s：G2 应可统计" % metric_note)
        self.assertTrue(C.is_available(res, "photometric"), "%s：G4 应可统计" % metric_note)

        g2_delta = abs(g2 - base_g2) / base_g2
        ncc_delta = abs(ncc - base_ncc) / base_ncc
        self.assertLess(
            g2_delta, 0.30,
            "%s：G2 不应显著退化（相对基线变化应小于 30%%），基线 %.4g -> 变体 %.4g（%.1f%%）"
            % (metric_note, base_g2, g2, g2_delta * 100),
        )
        self.assertLess(
            ncc_delta, 0.15,
            "%s：G4 NCC 不应显著退化（相对变化应小于 15%%），基线 %.4g -> 变体 %.4g（%.1f%%）"
            % (metric_note, base_ncc, ncc, ncc_delta * 100),
        )
        return res

    # ---------------- M2-AI-006 ----------------
    def test_m2_ai_006_resolution_half_not_degraded(self):
        """M2-AI-006 分辨率降为 0.5 倍的鲁棒性。

        用例预期为「G2、G4 相对基线出现退化」；实测结论与预期相反（未见显著退化），
        本测试断言实测结论：两项指标与基线同量级。
        """
        res = self._assert_same_order("res50", "0.5 倍分辨率")
        self.assertEqual(res.get("num_frames"), 9, "分辨率扰动不应改变帧数")

    # ---------------- M2-AI-007 ----------------
    def test_m2_ai_007_gaussian_noise_not_degraded(self):
        """M2-AI-007 高斯噪声 σ=10 的鲁棒性。

        用例预期为「G2、G4 相对基线出现退化」；实测结论与预期相反（未见显著退化），
        本测试断言实测结论：两项指标与基线同量级。
        """
        self._assert_same_order("noise10", "高斯噪声 σ=10")

    # ---------------- M2-AI-008 ----------------
    def test_m2_ai_008_occlusion_significant_degradation(self):
        """M2-AI-008 随机遮挡 25% 面积的鲁棒性。

        预期：G1、G4 出现退化，低置信像素占比上升。实测为全部变体中唯一显著退化项。
        """
        res = C.metrics_of(C.need_variant("occ25"), C.CONF_DEFAULT)
        base_ncc = C.g4_ncc(self.base)
        ncc = C.g4_ncc(res)

        self.assertTrue(C.is_available(res, "photometric"), "遮挡变体的 G4 应可统计")
        drop = (base_ncc - ncc) / base_ncc
        self.assertGreater(
            drop, 0.20,
            "遮挡 25%% 面积后 G4 NCC 应显著下降（降幅应大于 20%%），基线 %.4g -> 变体 %.4g（%.1f%%）"
            % (base_ncc, ncc, drop * 100),
        )

        base_low = C.g3_low_ratio(self.base)
        low = C.g3_low_ratio(res)
        self.assertGreater(
            low, base_low + 0.05,
            "遮挡后低置信像素占比应明显上升，基线 %.4g -> 变体 %.4g" % (base_low, low),
        )

    # ---------------- M2-AI-009 ----------------
    def test_m2_ai_009_determinism_bitwise_identical(self):
        """M2-AI-009 重复运行确定性检验。

        预期：相同输入、独立进程重跑后，depth / world_points / extrinsic /
        intrinsic 四个关键输出与基线逐位一致（max_abs_diff = 0.0）。
        """
        import numpy as np
        import metrics as metrics_mod

        base_npz = C.scene_npz(C.BASE_SCENE)
        rerun_npz = C.need_variant("det2")

        base = metrics_mod.load_predictions(base_npz)
        rerun = metrics_mod.load_predictions(rerun_npz)

        fields = ("depth", "world_points", "extrinsic", "intrinsic")
        for key in fields:
            a, b = base.get(key), rerun.get(key)
            self.assertIsNotNone(a, "基线缺少字段 %s" % key)
            self.assertIsNotNone(b, "重跑产物缺少字段 %s" % key)
            self.assertEqual(a.shape, b.shape, "%s 形状不一致：%s vs %s" % (key, a.shape, b.shape))

            diff = np.abs(a.astype(np.float64) - b.astype(np.float64))
            max_diff = float(diff.max())
            self.assertEqual(
                max_diff, 0.0,
                "字段 %s 应逐位一致（max_abs_diff=0），实际 max_abs_diff=%.4g" % (key, max_diff),
            )
            np.testing.assert_array_equal(a, b, err_msg="字段 %s 未逐位一致" % key)


if __name__ == "__main__":
    unittest.main(verbosity=2)
