"""Expected-behavior checks that reproduce DEF-IMG-002."""

import unittest
from pathlib import Path

import torch

from vggt.utils.load_fn import load_and_preprocess_images, load_and_preprocess_images_square


INPUT_DIR = Path(__file__).resolve().parent / "input"


class TestExifOrientationExpectedBehavior(unittest.TestCase):
    def test_control_without_orientation_keeps_landscape_shape(self):
        image_path = INPUT_DIR / "control_no_orientation_40x20.jpg"
        result = load_and_preprocess_images([str(image_path)], mode="crop")
        self.assertEqual(tuple(result.shape), (1, 3, 252, 518))

    def test_standard_loader_should_apply_orientation_before_resize(self):
        image_path = INPUT_DIR / "exif_orientation_6_stored_40x20.jpg"
        result = load_and_preprocess_images([str(image_path)], mode="crop")
        self.assertEqual(tuple(result.shape), (1, 3, 518, 518))

    def test_square_loader_should_report_displayed_orientation_coordinates(self):
        image_path = INPUT_DIR / "exif_orientation_6_stored_40x20.jpg"
        _, coords = load_and_preprocess_images_square([str(image_path)], target_size=140)
        expected = torch.tensor([[35.0, 0.0, 105.0, 140.0, 20.0, 40.0]])
        self.assertTrue(torch.equal(coords, expected), f"actual coords={coords.tolist()}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
