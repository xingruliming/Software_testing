"""Expected-behavior checks that reproduce DEF-IMG-001.

These tests intentionally fail on the affected implementation. They use a
non-standard filename so the ordinary ``unittest discover -s tests`` command
does not include them in the existing 15-case regression suite.
"""

import unittest
from pathlib import Path

from vggt.utils.load_fn import load_and_preprocess_images


INPUT_DIR = Path(__file__).resolve().parent / "input"


class TestExtremeAspectRatioExpectedBehavior(unittest.TestCase):
    def test_control_crop_height_fourteen_succeeds(self):
        """The existing minimum patch-aligned boundary remains valid."""
        image_path = INPUT_DIR / "valid_boundary_518x14.png"

        result = load_and_preprocess_images([str(image_path)], mode="crop")

        self.assertEqual(tuple(result.shape), (1, 3, 14, 518))

    def test_crop_height_one_should_not_produce_zero_dimension(self):
        """A readable image should not crash during resize."""
        image_path = INPUT_DIR / "extreme_wide_518x1.png"

        result = load_and_preprocess_images([str(image_path)], mode="crop")

        self.assertEqual(result.shape[0], 1)
        self.assertEqual(result.shape[1], 3)
        self.assertEqual(result.shape[3], 518)
        self.assertGreaterEqual(result.shape[2], 14)

    def test_pad_height_one_should_return_square_tensor(self):
        """Pad mode should preserve the image and return a 518 square."""
        image_path = INPUT_DIR / "extreme_wide_518x1.png"

        result = load_and_preprocess_images([str(image_path)], mode="pad")

        self.assertEqual(tuple(result.shape), (1, 3, 518, 518))


if __name__ == "__main__":
    unittest.main(verbosity=2)
