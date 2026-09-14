"""M1-GEO-023 .. M1-GEO-026 — ``img_from_cam``.

Cases:
    023 单位内参的透视除法（等价类：无畸变正常投影）
    024 自定义焦距和主点的像素投影（等价类：非单位内参）
    025 Z 为零导致 NaN 时使用默认值（边界值：Z=0；错误推测）
    026 零畸变参数等价于无畸变（等价类：可选参数 None/零值）
"""

from __future__ import annotations

import unittest
import warnings

import torch

from vggt.utils.geometry import img_from_cam

from .common import ATOL, CoordinateTestCase


class TestImgFromCam(CoordinateTestCase):
    def test_m1_geo_023_identity_intrinsic_perspective_divide(self):
        """M1-GEO-023: 单位内参下即为透视除法 (x/z, y/z)。

        输入 3x2 布局：(B=1, 3, N=2)，输出应为 (B, N, 2)。
        """
        cam_intrinsics = torch.eye(3)[None]
        cam_points = torch.tensor([[[2.0, -1.0], [4.0, 1.0], [2.0, 1.0]]])

        result = img_from_cam(cam_intrinsics, cam_points, None)

        self.assertEqual(tuple(result.shape), (1, 2, 2))
        self.assertArrayAlmostEqual(result[0].numpy(), [[1.0, 2.0], [-1.0, 1.0]])

    def test_m1_geo_024_custom_focal_and_principal_point(self):
        """M1-GEO-024: 按 u=fx*x/z+cx、v=fy*y/z+cy 复核。"""
        cam_intrinsics = torch.tensor([[[2.0, 0.0, 10.0], [0.0, 3.0, 20.0], [0.0, 0.0, 1.0]]])
        cam_points = torch.tensor([[[1.0], [2.0], [1.0]]])

        result = img_from_cam(cam_intrinsics, cam_points, None)

        self.assertEqual(tuple(result.shape), (1, 1, 2))
        self.assertArrayAlmostEqual(result[0, 0].numpy(), [12.0, 26.0])

    def test_m1_geo_025_zero_z_uses_default(self):
        """M1-GEO-025: z=0 导致 NaN，应被 nan_to_num 替换为 default。"""
        cam_intrinsics = torch.eye(3)[None]
        cam_points = torch.tensor([[[0.0], [0.0], [0.0]]])

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # 允许底层产生除零警告
            result = img_from_cam(cam_intrinsics, cam_points, None, default=-9.0)

        self.assertArrayAlmostEqual(result[0, 0].numpy(), [-9.0, -9.0])

    def test_m1_geo_026_zero_distortion_equals_none(self):
        """M1-GEO-026: 零畸变参数与不传畸变参数结果一致。"""
        cam_intrinsics = torch.eye(3)[None]
        cam_points = torch.tensor([[[1.0], [2.0], [2.0]]])

        without = img_from_cam(cam_intrinsics, cam_points, None)
        with_zero = img_from_cam(cam_intrinsics, cam_points, torch.tensor([[0.0]]))

        self.assertArrayAlmostEqual(without[0, 0].numpy(), [0.5, 1.0])
        self.assertTorchAlmostEqual(with_zero, without)


if __name__ == "__main__":
    unittest.main()
