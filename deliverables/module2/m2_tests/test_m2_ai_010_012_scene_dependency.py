# -*- coding: utf-8 -*-
"""M2-AI-010 ~ M2-AI-012：场景依赖性与裁切假说检验。

覆盖用例清单中的：
    010 竖构图近景场景在默认置信阈值下的可用性      （清单判定：NG）
    011 竖构图场景放宽置信阈值后的指标测量
    012 排除裁切影响：竖构图补白成正方形后重测

数据来源：``vggt_output/001_watercup/predictions.npz``（8 帧竖构图）与
``vggt_output/exp/sq4096``（补白正方形变体，缺失时按需现场生成）。

M2-AI-010 是清单中两条失败用例之一：默认阈值下该场景的深度置信最大值
（实测 2.187）低于阈值 3.0，全部像素被判为低置信，G1/G2/G4 因「有效像素为 0」
被静默跳过——对应缺陷 DEF-M2-003「低置信场景下置信度过滤静默失效」。
本测试断言的是用例**期望行为**（四项指标应可统计），因此当前必然失败，
这正是该缺陷的自动化复现。
"""

import unittest

from m2_tests import common as C


class TestSceneDependency(unittest.TestCase):
    """场景依赖性：置信度绝对值随场景漂移，固定阈值不通用。"""

    @classmethod
    def setUpClass(cls):
        cls.water_npz = C.scene_npz(C.WATER_SCENE)
        if not cls.water_npz.is_file():
            raise unittest.SkipTest("缺少竖构图场景产物 %s" % cls.water_npz)

    # ---------------- M2-AI-010 ----------------
    def test_m2_ai_010_default_threshold_metrics_available(self):
        """M2-AI-010 竖构图近景场景在默认置信阈值下的可用性。

        预期：四项指标与基线同量级，可正常统计。
        实际：深度置信最大值低于默认阈值 3.0 → G1/G2/G4 全部因「有效像素为 0」
        被跳过且无任何降级提示（缺陷 DEF-M2-003）。
        """
        res = C.metrics_of(self.water_npz, C.CONF_DEFAULT)
        self.assertEqual(res.get("num_frames"), 8, "竖构图场景应为 8 帧")

        conf = C.pick(res, "confidence").get("depth_conf") or {}
        conf_max = conf.get("max")
        conf_mean = conf.get("mean")

        metrics_all = ("pointmap_vs_depth", "pointmap_vs_camera", "confidence", "photometric")
        unavailable = [name for name in metrics_all if not C.is_available(res, name)]

        self.assertEqual(
            unavailable, [],
            "默认阈值 %.1f 下应能统计全部四项指标，实际不可统计：%s。"
            "该场景深度置信最大值仅 %s（均值 %s），低于阈值导致有效像素为 0 —— "
            "对应缺陷 DEF-M2-003：置信度阈值跨场景静默失效。"
            % (C.CONF_DEFAULT, unavailable, conf_max, conf_mean),
        )

    # ---------------- M2-AI-011 ----------------
    def test_m2_ai_011_loose_threshold_shows_degradation(self):
        """M2-AI-011 竖构图场景放宽置信阈值后的指标测量（conf_thres=1.0）。

        预期：指标可统计，且显著劣于横构图基线（近景、低纹理、小基线场景）。
        """
        res = C.metrics_of(self.water_npz, C.CONF_LOOSE)

        for name in ("pointmap_vs_depth", "pointmap_vs_camera", "photometric"):
            self.assertTrue(
                C.is_available(res, name),
                "阈值放宽到 %.1f 后 %s 应可统计" % (C.CONF_LOOSE, name),
            )

        g1 = C.g1_rel(res)
        self.assertGreater(
            g1, 5 * C.BASELINE_G1_REL,
            "放宽阈值后 G1 相对误差应显著大于横构图基线（应大于 5 倍基线 %.4g），实测 %.4g"
            % (C.BASELINE_G1_REL, g1),
        )

        g2 = C.g2_px(res)
        self.assertGreater(
            g2, 10.0,
            "放宽阈值后 G2 平均重投影像素误差应显著劣化（应大于 10 px），实测 %.4g px" % g2,
        )

        ncc = C.g4_ncc(res)
        self.assertLess(
            ncc, 0.70,
            "放宽阈值后 G4 光度一致性应明显低于横构图基线 %.4g，实测 %.4g" % (C.BASELINE_G4_NCC, ncc),
        )

    # ---------------- M2-AI-012 ----------------
    def test_m2_ai_012_square_padding_does_not_improve(self):
        """M2-AI-012 排除裁切影响：竖构图补白成正方形后重测。

        预期：若预处理裁切是质量退化的主因，补白后指标应显著改善；
        实测假说被否证（指标未改善，退化由场景本身导致）。
        同时该场景暴露缺陷 DEF-M2-002（crop 模式对非 1:1 输入静默裁切 24.5% 视野）。
        """
        square_npz = C.need_square_case()
        square = C.metrics_of(square_npz, C.CONF_LOOSE)
        original = C.metrics_of(self.water_npz, C.CONF_LOOSE)

        self.assertTrue(C.is_available(square, "pointmap_vs_depth"), "补白变体的 G1 应可统计")

        orig_g1, new_g1 = C.g1_rel(original), C.g1_rel(square)
        improvement = (orig_g1 - new_g1) / orig_g1
        self.assertLess(
            improvement, 0.20,
            "补白成正方形后 G1 相对误差未显著改善（改善幅度应小于 20%%，即裁切不是退化主因）："
            "原竖构图 %.4g -> 补白后 %.4g（改善 %.1f%%）" % (orig_g1, new_g1, improvement * 100),
        )

        orig_ncc, new_ncc = C.g4_ncc(original), C.g4_ncc(square)
        self.assertLess(
            new_ncc - orig_ncc, 0.20,
            "补白后 G4 光度一致性的提升不应达到「显著改善」量级：原 %.4g -> 补白后 %.4g"
            % (orig_ncc, new_ncc),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
