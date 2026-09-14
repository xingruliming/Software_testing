"""M1-GEO-011 .. M1-GEO-015 — ``depth_to_world_coords_points``.

Cases:
    011 深度图为 None（等价类：空输入）
    012 单位内外参下世界坐标等于相机坐标（等价类：单位坐标系）
    013 含平移外参的相机到世界变换（等价类：纯平移；逆变换）
    014 默认 eps 附近的深度有效性（边界值：eps-、eps、eps+）
    015 旋转外参下的世界坐标（组合覆盖：深度与旋转）
"""

from __future__ import annotations

import unittest

import numpy as np

from vggt.utils.geometry import depth_to_world_coords_points

from .common import ATOL, CoordinateTestCase, extrinsic_with_translation, identity_extrinsic


class TestDepthToWorldCoordsPoints(CoordinateTestCase):
    def test_m1_geo_011_none_depth_returns_triple_none(self):
        """M1-GEO-011: depth_map 为 None 时直接返回 (None, None, None)。"""
        result = depth_to_world_coords_points(None, None, None)

        self.assertEqual(result, (None, None, None))

    def test_m1_geo_012_identity_extrinsic_world_equals_camera(self):
        """M1-GEO-012: 单位内外参下世界坐标等于相机坐标。"""
        depth_map = np.array([[1, 2]])
        intrinsic = np.eye(3)
        extrinsic = identity_extrinsic()

        world, cam, mask = depth_to_world_coords_points(depth_map, extrinsic, intrinsic)

        expected = [[[0.0, 0.0, 1.0], [2.0, 0.0, 2.0]]]
        self.assertArrayAlmostEqual(cam, expected)
        self.assertArrayAlmostEqual(world, expected)
        self.assertEqual(mask.tolist(), [[True, True]])

    def test_m1_geo_013_pure_translation_extrinsic(self):
        """M1-GEO-013: 外参含平移 (1,2,3)，世界坐标应为 cam 经逆平移后的结果。"""
        depth_map = np.array([[2.0]])
        intrinsic = np.eye(3)
        extrinsic = extrinsic_with_translation([1.0, 2.0, 3.0])

        world, cam, mask = depth_to_world_coords_points(depth_map, extrinsic, intrinsic)

        self.assertArrayAlmostEqual(cam[0, 0], [0.0, 0.0, 2.0])
        self.assertArrayAlmostEqual(world[0, 0], [-1.0, -2.0, -1.0])
        self.assertEqual(mask.tolist(), [[True]])

    def test_m1_geo_014_eps_boundary_depth_validity(self):
        """M1-GEO-014: 有效深度判据为 depth > eps（严格大于）。"""
        depth_map = np.array([[0, 1e-8, 1.1e-8, -1.0]])
        intrinsic = np.eye(3)
        extrinsic = identity_extrinsic()

        _, _, mask = depth_to_world_coords_points(depth_map, extrinsic, intrinsic, eps=1e-8)

        # 0 与 eps 本身不算有效；仅 1.1e-8 超过 eps；负深度无效
        self.assertEqual(mask.tolist(), [[False, False, True, False]])

    def test_m1_geo_015_rotation_extrinsic_world_coords(self):
        """M1-GEO-015: 绕 Z 轴 +90° 旋转外参下的世界坐标。"""
        depth_map = np.array([[0, 1]])
        intrinsic = np.eye(3)
        rotation_z90 = np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1]], dtype=float)
        extrinsic = np.hstack([rotation_z90, np.zeros((3, 1))])

        world, cam, _ = depth_to_world_coords_points(depth_map, extrinsic, intrinsic)

        # 第 0 像素深度为 0 -> 原点
        self.assertArrayAlmostEqual(world[0, 0], [0.0, 0.0, 0.0])
        # 第 1 像素相机坐标 [1,0,1]，经 Rz(+90) 的逆变换到世界系
        self.assertArrayAlmostEqual(cam[0, 1], [1.0, 0.0, 1.0])
        self.assertArrayAlmostEqual(world[0, 1], [0.0, -1.0, 1.0])


if __name__ == "__main__":
    unittest.main()
