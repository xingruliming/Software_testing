"""M1-GEO-016 .. M1-GEO-019 — ``unproject_depth_map_to_point_map``.

Cases:
    016 两帧深度图批量反投影（等价类：多帧批处理）
    017 带末尾单通道维度的深度图（等价类：文档允许的四维输入）
    018 Torch 输入自动转为 NumPy（等价类：Torch/NumPy 类型转换）
    019 深度帧数与外参数量不一致（错误推测：批量长度不一致）

.. warning::
   M1-GEO-016 与 M1-GEO-018 当前为**失败用例**，对应已登记的缺陷
   ``DEF-M1-001``：函数文档声明支持 ``(S, H, W)`` 三维深度图，但实现中
   ``depth_map[frame_idx].squeeze(-1)`` 在 ``W == 1`` 时会删除宽度维，
   导致后续 ``H, W = depth_map.shape`` 解包失败。

   这两条用例按**预期结果**断言（即断言文档承诺的行为），因此在缺陷修复前
   必然失败——这正是它们要暴露的问题。修复后应自动转为通过，无需改动用例。
   现状记录见 ``test_results/module1/DEF-M1-001_reproduction.txt``。
"""

from __future__ import annotations

import unittest

import numpy as np
import torch

from vggt.utils.geometry import unproject_depth_map_to_point_map

from .common import ATOL, CoordinateTestCase


class TestUnprojectDepthMapToPointMap(CoordinateTestCase):
    def test_m1_geo_016_two_frame_batch(self):
        """M1-GEO-016: 两帧 (S,H,W) 深度图批量反投影 —— 暴露 DEF-M1-001。

        文档承诺返回 (2, 1, 1, 3)；当前实现因 squeeze(-1) 破坏宽度维而抛出
        ValueError，故本用例失败即为预期中的缺陷证据。
        """
        depth_map = np.array([[[1.0]], [[2.0]]])
        intrinsics = np.array([np.eye(3)] * 2)
        extrinsics = np.array([np.hstack([np.eye(3), np.zeros((3, 1))])] * 2)

        result = unproject_depth_map_to_point_map(depth_map, extrinsics, intrinsics)

        self.assertEqual(result.shape, (2, 1, 1, 3))
        self.assertArrayAlmostEqual(result[0, 0, 0], [0.0, 0.0, 1.0])
        self.assertArrayAlmostEqual(result[1, 0, 0], [0.0, 0.0, 2.0])

    def test_m1_geo_017_trailing_single_channel(self):
        """M1-GEO-017: 四维 (S,H,W,1) 输入应能正确 squeeze 后反投影。"""
        depth_map = np.array([[[[1.0], [2.0]]]])  # (1, 1, 2, 1)
        intrinsics = np.array([np.eye(3)])
        extrinsics = np.array([np.hstack([np.eye(3), np.zeros((3, 1))])])

        result = unproject_depth_map_to_point_map(depth_map, extrinsics, intrinsics)

        self.assertEqual(result.shape, (1, 1, 2, 3))
        self.assertArrayAlmostEqual(result[0, 0, 0], [0.0, 0.0, 1.0])
        self.assertArrayAlmostEqual(result[0, 0, 1], [2.0, 0.0, 2.0])

    def test_m1_geo_018_torch_input_converted_to_numpy(self):
        """M1-GEO-018: Torch 输入应自动转 NumPy 并返回 np.ndarray —— 暴露 DEF-M1-001。

        与 M1-GEO-016 同源：三维 ``(S,H,W)`` torch 输入同样触发 squeeze 缺陷。
        期望返回 np.ndarray、shape=(1,1,1,3)、坐标 [0,0,3]。
        """
        depth = torch.tensor([[[3.0]]])
        intrinsic = torch.eye(3)[None]
        extrinsic = torch.cat([torch.eye(3), torch.zeros(3, 1)], dim=1)[None]

        result = unproject_depth_map_to_point_map(depth, extrinsic, intrinsic)

        self.assertIsInstance(result, np.ndarray)
        self.assertEqual(result.shape, (1, 1, 1, 3))
        self.assertArrayAlmostEqual(result[0, 0, 0], [0.0, 0.0, 3.0])

    def test_m1_geo_019_frame_count_mismatch_raises(self):
        """M1-GEO-019: 深度帧数多于外参数量时应抛出异常，而非返回部分结果。

        使用四维输入以绕开 DEF-M1-001，从而独立验证「批量长度不一致」这一意图：
        第 2 帧访问 extrinsics[1] 时越界。
        """
        depth_map = np.zeros((2, 1, 1, 1))
        intrinsics = np.array([np.eye(3)] * 2)
        extrinsics = np.array([np.hstack([np.eye(3), np.zeros((3, 1))])])  # 仅 1 帧

        with self.assertRaises(IndexError):
            unproject_depth_map_to_point_map(depth_map, extrinsics, intrinsics)

    def test_m1_geo_019_control_matched_lengths_succeed(self):
        """M1-GEO-019 对照：帧数与外参一致时（四维输入）应正常返回。"""
        depth_map = np.zeros((2, 1, 1, 1))
        intrinsics = np.array([np.eye(3)] * 2)
        extrinsics = np.array([np.hstack([np.eye(3), np.zeros((3, 1))])] * 2)

        result = unproject_depth_map_to_point_map(depth_map, extrinsics, intrinsics)

        self.assertEqual(result.shape, (2, 1, 1, 3))


if __name__ == "__main__":
    unittest.main()
