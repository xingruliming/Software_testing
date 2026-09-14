"""M1-GEO-001 .. M1-GEO-005 — ``depth_to_cam_coords_points``.

Cases:
    001 单像素中心点反投影（等价类：有效单像素输入）
    002 主点位于右下角的 2x2 深度图（边界值：图像四个边角）
    003 全零深度图（边界值：深度下界 0）
    004 内参矩阵尺寸非法（等价类：无效矩阵尺寸）
    005 内参矩阵含非零偏斜项（错误推测：不支持的非零 skew）
"""

from __future__ import annotations

import unittest

import numpy as np

from vggt.utils.geometry import depth_to_cam_coords_points

from .common import ATOL, CoordinateTestCase


class TestDepthToCamCoordsPoints(CoordinateTestCase):
    def test_m1_geo_001_single_center_pixel(self):
        """M1-GEO-001: 单像素中心点反投影。

        内参 fu=2, fv=4，主点 (0,0)；像素 (0,0) 位于主点上，
        因此反投影结果只有 z=depth 分量。
        """
        depth_map = np.array([[2.0]])
        intrinsic = np.array([[2, 0, 0], [0, 4, 0], [0, 0, 1]])

        result = depth_to_cam_coords_points(depth_map, intrinsic)

        self.assertEqual(result.shape, (1, 1, 3))
        self.assertEqual(result.dtype, np.float32)
        self.assertArrayAlmostEqual(result[0, 0], [0.0, 0.0, 2.0])

    def test_m1_geo_002_principal_point_bottom_right_2x2(self):
        """M1-GEO-002: 主点位于右下角，覆盖 2x2 图像的四个边角。"""
        depth_map = np.ones((2, 2))
        intrinsic = np.array([[1, 0, 1], [0, 1, 1], [0, 0, 1]])

        result = depth_to_cam_coords_points(depth_map, intrinsic)

        self.assertEqual(result.shape, (2, 2, 3))
        expected = [
            [[-1.0, -1.0, 1.0], [0.0, -1.0, 1.0]],
            [[-1.0, 0.0, 1.0], [0.0, 0.0, 1.0]],
        ]
        self.assertArrayAlmostEqual(result, expected)

    def test_m1_geo_003_all_zero_depth(self):
        """M1-GEO-003: 全零深度图（深度下界 0）。"""
        depth_map = np.zeros((2, 3))
        intrinsic = np.eye(3)

        result = depth_to_cam_coords_points(depth_map, intrinsic)

        self.assertEqual(result.shape, (2, 3, 3))
        self.assertEqual(result.dtype, np.float32)
        self.assertTrue(np.all(result == 0), "全零深度应产生全零相机坐标")

    def test_m1_geo_004_invalid_intrinsic_size(self):
        """M1-GEO-004: 内参矩阵尺寸非法，应抛出 AssertionError。"""
        depth_map = np.ones((1, 1))
        intrinsic = np.eye(2)

        with self.assertRaises(AssertionError) as context:
            depth_to_cam_coords_points(depth_map, intrinsic)

        self.assertIn("Intrinsic matrix must be 3x3", str(context.exception))

    def test_m1_geo_005_nonzero_skew(self):
        """M1-GEO-005: 内参矩阵含非零偏斜项，应抛出 AssertionError。"""
        depth_map = np.ones((1, 1))
        intrinsic = np.array([[1, 0.1, 0], [0, 1, 0], [0, 0, 1]])

        with self.assertRaises(AssertionError) as context:
            depth_to_cam_coords_points(depth_map, intrinsic)

        self.assertIn("Intrinsic matrix must have zero skew", str(context.exception))


if __name__ == "__main__":
    unittest.main()
