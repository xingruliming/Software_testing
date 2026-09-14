"""Shared helpers for the module 1 coordinate-transform test suite.

Scope: ``vggt-main/vggt/utils/geometry.py`` (cases M1-GEO-001 .. M1-GEO-032).

The suite is deliberately import-light: it must not import ``demo_gradio_cn.py``
or any module that loads model weights. ``tests/run_tests.ps1`` injects the
``vggt-main`` directory into ``PYTHONPATH`` from the outside, so the baseline
source is never modified for testability.
"""

from __future__ import annotations

import unittest

import numpy as np
import torch

# Tolerance used across the suite, matching the value recorded in the case list.
ATOL = 1e-6


def identity_extrinsic() -> np.ndarray:
    """Return the canonical 3x4 identity extrinsic ``[I3 | 0]``."""
    return np.hstack([np.eye(3), np.zeros((3, 1))])


def extrinsic_with_translation(t) -> np.ndarray:
    """Return ``[I3 | t]`` with ``t`` given as a length-3 sequence."""
    return np.hstack([np.eye(3), np.asarray(t, dtype=float).reshape(3, 1)])


def torch_identity_extrinsic() -> torch.Tensor:
    """Return a 1-frame torch ``[I3 | 0]`` extrinsic of shape (1, 3, 4)."""
    return torch.cat([torch.eye(3), torch.zeros(3, 1)], dim=1).unsqueeze(0)


def torch_extrinsic_with_translation(t) -> torch.Tensor:
    """Return a 1-frame torch ``[I3 | t]`` extrinsic of shape (1, 3, 4)."""
    column = torch.tensor(t, dtype=torch.float32).reshape(3, 1)
    return torch.cat([torch.eye(3), column], dim=1).unsqueeze(0)


class CoordinateTestCase(unittest.TestCase):
    """Base class providing shared numpy/torch assertions."""

    def assertArrayAlmostEqual(self, actual, expected, atol=ATOL, msg=None):
        np.testing.assert_allclose(
            np.asarray(actual, dtype=float),
            np.asarray(expected, dtype=float),
            atol=atol,
            err_msg=msg or "arrays differ beyond tolerance",
        )

    def assertTorchAlmostEqual(self, actual, expected, atol=ATOL, msg=None):
        torch.testing.assert_close(
            actual,
            expected,
            atol=atol,
            rtol=0.0,
            msg=msg or "tensors differ beyond tolerance",
        )


__all__ = [
    "ATOL",
    "CoordinateTestCase",
    "identity_extrinsic",
    "extrinsic_with_translation",
    "torch_identity_extrinsic",
    "torch_extrinsic_with_translation",
]
