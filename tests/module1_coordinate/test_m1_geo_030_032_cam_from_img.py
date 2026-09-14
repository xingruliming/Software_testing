"""M1-GEO-030 .. M1-GEO-032 — ``cam_from_img``.

Cases:
    030 根据焦距和主点归一化像素轨迹（等价类：无畸变归一化）
    031 不同内参的批量轨迹归一化（组合覆盖：批量内参差异）
    032 零畸变参数的反畸变分支（判定表：extra_params 有/无；等价类）
"""

from __future__ import annotations

import unittest

import torch

from vggt.utils.geometry import cam_from_img

from .common import ATOL, CoordinateTestCase


class TestCamFromImg(CoordinateTestCase):
    def test_m1_geo_030_normalize_with_focal_and_principal_point(self):
        """M1-GEO-030: 归一化 (track - principal_point) / focal_length。"""
        pred_tracks = torch.tensor([[[10.0, 20.0], [12.0, 26.0]]])
        intrinsics = torch.tensor([[[2.0, 0.0, 10.0], [0.0, 3.0, 20.0], [0.0, 0.0, 1.0]]])

        result = cam_from_img(pred_tracks, intrinsics, None)

        self.assertEqual(tuple(result.shape), (1, 2, 2))
        self.assertArrayAlmostEqual(result[0].numpy(), [[0.0, 0.0], [1.0, 2.0]])

    def test_m1_geo_031_batch_with_different_intrinsics(self):
        """M1-GEO-031: 批内每帧独立使用其内参归一化。"""
        pred_tracks = torch.tensor([[[2.0, 4.0]], [[5.0, 7.0]]])
        intrinsics = torch.tensor(
            [
                [[2.0, 0.0, 0.0], [0.0, 2.0, 0.0], [0.0, 0.0, 1.0]],
                [[4.0, 0.0, 1.0], [0.0, 5.0, 2.0], [0.0, 0.0, 1.0]],
            ]
        )

        result = cam_from_img(pred_tracks, intrinsics, None)

        self.assertEqual(tuple(result.shape), (2, 1, 2))
        self.assertArrayAlmostEqual(result[0, 0].numpy(), [1.0, 2.0])
        self.assertArrayAlmostEqual(result[1, 0].numpy(), [1.0, 1.0])

    def test_m1_geo_032_zero_distortion_branch_matches_none(self):
        """M1-GEO-032: extra_params 为 None 与全零时结果一致。"""
        pred_tracks = torch.tensor([[[0.5, -0.25]]])
        intrinsics = torch.eye(3)[None]

        without = cam_from_img(pred_tracks, intrinsics, None)
        with_zero = cam_from_img(pred_tracks, intrinsics, torch.tensor([[0.0]]))

        self.assertArrayAlmostEqual(without[0, 0].numpy(), [0.5, -0.25])
        self.assertTorchAlmostEqual(with_zero, without)


if __name__ == "__main__":
    unittest.main()
