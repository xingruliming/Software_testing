"""M1-GEO-006 .. M1-GEO-010 — ``closed_form_inverse_se3``.

Cases:
    006 NumPy 单位 SE(3) 矩阵求逆（等价类：单位变换）
    007 NumPy 批量平移矩阵求逆（等价类：批量输入；组合覆盖）
    008 绕 Z 轴 90° 旋转矩阵求逆（等价类：纯旋转；逆变换性质）
    009 Torch float64 类型与设备保持（等价类：Torch 输入；类型保持）
    010 SE(3) 尾部尺寸非法（边界值：尾部矩阵尺寸）
"""

from __future__ import annotations

import unittest

import numpy as np
import torch

from vggt.utils.geometry import closed_form_inverse_se3

from .common import ATOL, CoordinateTestCase


class TestClosedFormInverseSe3(CoordinateTestCase):
    def test_m1_geo_006_numpy_identity(self):
        """M1-GEO-006: 单位 SE(3) 求逆仍为单位矩阵。"""
        se3 = np.eye(4)[None, :, :]

        result = closed_form_inverse_se3(se3)

        self.assertIsInstance(result, np.ndarray)
        self.assertEqual(result.shape, (1, 4, 4))
        self.assertArrayAlmostEqual(result[0], np.eye(4))

    def test_m1_geo_007_numpy_batch_translation(self):
        """M1-GEO-007: 批量输入，含单位帧与平移帧。"""
        se3 = np.zeros((2, 4, 4))
        se3[0] = np.eye(4)
        se3[1] = np.eye(4)
        se3[1, :3, 3] = [1.0, 2.0, 3.0]

        result = closed_form_inverse_se3(se3)

        # 第一帧仍是单位矩阵
        self.assertArrayAlmostEqual(result[0], np.eye(4))
        # 第二帧旋转不变，平移取反，底行齐次
        self.assertArrayAlmostEqual(result[1, :3, :3], np.eye(3))
        self.assertArrayAlmostEqual(result[1, :3, 3], [-1.0, -2.0, -3.0])
        self.assertArrayAlmostEqual(result[1, 3], [0.0, 0.0, 0.0, 1.0])

    def test_m1_geo_008_numpy_pure_rotation_z90(self):
        """M1-GEO-008: 绕 Z 轴 +90° 的 3x4 矩阵求逆。

        输入 Rz(+90°) = [[0,-1,0],[1,0,0],[0,0,1]]，其逆为 Rz(-90°)。
        """
        se3 = np.array([[[0, -1, 0, 0], [1, 0, 0, 0], [0, 0, 1, 0]]], dtype=float)

        result = closed_form_inverse_se3(se3)

        self.assertEqual(result.shape, (1, 4, 4))
        expected_rotation = np.array([[0, 1, 0], [-1, 0, 0], [0, 0, 1]], dtype=float)
        self.assertArrayAlmostEqual(result[0, :3, :3], expected_rotation)
        self.assertArrayAlmostEqual(result[0, :3, 3], [0.0, 0.0, 0.0])
        self.assertArrayAlmostEqual(result[0, 3], [0.0, 0.0, 0.0, 1.0])

    def test_m1_geo_009_torch_float64_dtype_and_device(self):
        """M1-GEO-009: Torch 输入应保持 dtype 与 device。"""
        se3 = torch.eye(4, dtype=torch.float64).unsqueeze(0)

        result = closed_form_inverse_se3(se3)

        self.assertIsInstance(result, torch.Tensor)
        self.assertEqual(result.dtype, torch.float64)
        self.assertEqual(result.device, se3.device)
        self.assertEqual(tuple(result.shape), (1, 4, 4))
        self.assertTorchAlmostEqual(result, torch.eye(4, dtype=torch.float64).unsqueeze(0))

    def test_m1_geo_010_invalid_trailing_shape(self):
        """M1-GEO-010: se3 尾部尺寸非法（应为 4x4 或 3x4）。"""
        se3 = np.zeros((1, 4, 3))

        with self.assertRaises(ValueError) as context:
            closed_form_inverse_se3(se3)

        message = str(context.exception)
        self.assertIn("se3 must be of shape", message)
        self.assertIn("(1, 4, 3)", message)


if __name__ == "__main__":
    unittest.main()
