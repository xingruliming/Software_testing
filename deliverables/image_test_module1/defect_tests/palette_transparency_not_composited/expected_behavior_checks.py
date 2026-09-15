"""Expected-behavior checks that reproduce DEF-IMG-003."""

import unittest
from pathlib import Path

import torch

from vggt.utils.load_fn import load_and_preprocess_images, load_and_preprocess_images_square


INPUT_DIR = Path(__file__).resolve().parent / "input"


class TestPaletteTransparencyExpectedBehavior(unittest.TestCase):
    def assert_white(self, tensor):
        self.assertTrue(torch.allclose(tensor, torch.ones_like(tensor), atol=1e-6))

    def test_rgba_transparency_control_is_composited_on_white(self):
        image_path = INPUT_DIR / "fully_transparent_rgba_14x14.png"
        result = load_and_preprocess_images([str(image_path)], mode="crop")
        self.assert_white(result)

    def test_standard_loader_should_composite_palette_transparency_on_white(self):
        image_path = INPUT_DIR / "fully_transparent_palette_14x14.png"
        result = load_and_preprocess_images([str(image_path)], mode="crop")
        self.assert_white(result)

    def test_square_loader_should_composite_palette_transparency_on_white(self):
        image_path = INPUT_DIR / "fully_transparent_palette_14x14.png"
        result, _ = load_and_preprocess_images_square([str(image_path)], target_size=14)
        self.assert_white(result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
