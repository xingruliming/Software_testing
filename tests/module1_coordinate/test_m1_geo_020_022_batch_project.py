"""M1-GEO-020 .. M1-GEO-022 — ``project_world_points_to_camera_points_batch``.

Cases:
    020 单位外参批量投影到相机坐标（等价类：单位外参）
    021 平移外参批量投影（等价类：纯平移）
    022 不同帧外参的广播计算（组合覆盖：帧维度广播）
"""

from __future__ import annotations

import unittest

import torch

from vggt.utils.geometry import project_world_points_to_camera_points_batch

from .common import ATOL, CoordinateTestCase


def _grad_to_cam(rotation, translation):
    """Build a torch 3x4 extrinsic from numpy-like rotation and translation."""
    return torch.cat([rotation, translation], dim=1)


class TestProjectWorldPointsToCameraPointsBatch(CoordinateTestCase):
    def test_m1_geo_020_identity_extrinsic(self):
        """M1-GEO-020: 单位外参下相机坐标等于世界坐标。"""
        world_points = torch.tensor([[[[[0.0, 0.0, 1.0], [1.0, 2.0, 3.0]]]]])  # (1,1,1,2,3)
        extrinsics = _grad_to_cam(torch.eye(3), torch.zeros(3, 1))[None, None]  # (1,1,3,4)

        result = project_world_points_to_camera_points_batch(world_points, extrinsics)

        self.assertEqual(tuple(result.shape), (1, 1, 1, 2, 3))
        self.assertTorchAlmostEqual(result, world_points)

    def test_m1_geo_021_translation_extrinsic(self):
        """M1-GEO-021: 平移外参 (1,0,0) 应把世界点平移到相机系。"""
        world_points = torch.tensor([[[[[0.0, 0.0, 1.0]]]]])  # (1,1,1,1,3)
        translation = torch.tensor([[1.0], [0.0], [0.0]])
        extrinsics = _grad_to_cam(torch.eye(3), translation)[None, None]

        result = project_world_points_to_camera_points_batch(world_points, extrinsics)

        self.assertEqual(tuple(result.shape), (1, 1, 1, 1, 3))
        self.assertArrayAlmostEqual(result.reshape(-1, 3).numpy(), [[1.0, 0.0, 1.0]])

    def test_m1_geo_022_per_frame_extrinsic_broadcast(self):
        """M1-GEO-022: 帧维广播 —— 同一世界点经两帧不同外参得到不同相机坐标。"""
        world_points = torch.tensor([[[[[1.0, 1.0, 1.0]]], [[[1.0, 1.0, 1.0]]]]])  # (1,2,1,1,3)
        frame0 = _grad_to_cam(torch.eye(3), torch.zeros(3, 1))
        frame1 = _grad_to_cam(torch.eye(3), torch.tensor([[1.0], [2.0], [3.0]]))
        extrinsics = torch.stack([frame0, frame1])[None]  # (1,2,3,4)

        result = project_world_points_to_camera_points_batch(world_points, extrinsics)

        self.assertEqual(tuple(result.shape), (1, 2, 1, 1, 3))
        self.assertArrayAlmostEqual(result[0, 0].reshape(-1, 3).numpy(), [[1.0, 1.0, 1.0]])
        self.assertArrayAlmostEqual(result[0, 1].reshape(-1, 3).numpy(), [[2.0, 3.0, 4.0]])


if __name__ == "__main__":
    unittest.main()
