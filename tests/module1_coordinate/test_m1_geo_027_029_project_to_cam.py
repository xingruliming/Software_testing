"""M1-GEO-027 .. M1-GEO-029 — ``project_world_points_to_cam``.

Cases:
    027 单位内外参的世界点投影（等价类：端到端投影正常路径）
    028 平移外参与自定义内参组合投影（组合覆盖：外参平移×非单位内参）
    029 only_points_cam 跳过像素投影（判定表：only_points_cam=True 分支）
"""

from __future__ import annotations

import unittest

import torch

from vggt.utils.geometry import project_world_points_to_cam

from .common import ATOL, CoordinateTestCase


class TestProjectWorldPointsToCam(CoordinateTestCase):
    def test_m1_geo_027_identity_extrinsic_and_intrinsic(self):
        """M1-GEO-027: 端到端投影正常路径，同时校验像素与相机坐标。"""
        world_points = torch.tensor([[0.0, 0.0, 1.0], [2.0, 4.0, 2.0]])
        extrinsics = torch.cat([torch.eye(3), torch.zeros(3, 1)], dim=1)[None]
        intrinsics = torch.eye(3)[None]

        image_points, cam_points = project_world_points_to_cam(world_points, extrinsics, intrinsics)

        self.assertArrayAlmostEqual(image_points[0].numpy(), [[0.0, 0.0], [1.0, 2.0]])
        # cam_points 为 Bx3xN，即每个点是一列
        self.assertEqual(tuple(cam_points.shape), (1, 3, 2))
        self.assertArrayAlmostEqual(cam_points[0, :, 0].numpy(), [0.0, 0.0, 1.0])
        self.assertArrayAlmostEqual(cam_points[0, :, 1].numpy(), [2.0, 4.0, 2.0])

    def test_m1_geo_028_translation_with_custom_intrinsic(self):
        """M1-GEO-028: 外参平移 (1,2,0) 且使用非单位内参。"""
        world_point = torch.tensor([[0.0, 0.0, 1.0]])
        extrinsics = torch.cat(
            [torch.eye(3), torch.tensor([[1.0], [2.0], [0.0]])], dim=1
        )[None]
        intrinsics = torch.tensor([[[2.0, 0.0, 10.0], [0.0, 3.0, 20.0], [0.0, 0.0, 1.0]]])

        image_points, cam_points = project_world_points_to_cam(world_point, extrinsics, intrinsics)

        self.assertArrayAlmostEqual(cam_points[0, :, 0].numpy(), [1.0, 2.0, 1.0])
        self.assertArrayAlmostEqual(image_points[0, 0].numpy(), [12.0, 26.0])

    def test_m1_geo_029_only_points_cam_skips_pixel_projection(self):
        """M1-GEO-029: only_points_cam=True 时 image_points 为 None。"""
        world_point = torch.tensor([[1.0, 2.0, 3.0]])
        extrinsics = torch.cat(
            [torch.eye(3), torch.tensor([[1.0], [0.0], [-1.0]])], dim=1
        )[None]

        image_points, cam_points = project_world_points_to_cam(
            world_point, extrinsics, None, only_points_cam=True
        )

        self.assertIsNone(image_points)
        self.assertEqual(tuple(cam_points.shape), (1, 3, 1))
        self.assertArrayAlmostEqual(cam_points[0, :, 0].numpy(), [2.0, 2.0, 2.0])


if __name__ == "__main__":
    unittest.main()
