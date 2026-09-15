import torch

from tests.common import ImageFixtureTestCase
from vggt.utils.load_fn import load_and_preprocess_images_square


class TestLoadAndPreprocessImagesSquareEquivalence(ImageFixtureTestCase):
    """Equivalence partitions for orientation, color mode, and path validity."""

    def test_tc009_valid_rgb_landscape_image(self):
        image_path = self.make_image("landscape.png", "RGB", (640, 480), (255, 0, 0))

        result, coords = load_and_preprocess_images_square([image_path], target_size=518)

        self.assertEqual(tuple(result.shape), (1, 3, 518, 518))
        torch.testing.assert_close(
            coords[0],
            torch.tensor([0.0, 64.75, 518.0, 453.25, 640.0, 480.0]),
        )
        torch.testing.assert_close(result[0, :, 0, 259], torch.zeros(3))

    def test_tc010_valid_rgb_portrait_image(self):
        image_path = self.make_image("portrait.png", "RGB", (480, 640), (0, 0, 255))

        result, coords = load_and_preprocess_images_square([image_path], target_size=518)

        self.assertEqual(tuple(result.shape), (1, 3, 518, 518))
        torch.testing.assert_close(
            coords[0],
            torch.tensor([64.75, 0.0, 453.25, 518.0, 480.0, 640.0]),
        )
        torch.testing.assert_close(result[0, :, 259, 0], torch.zeros(3))

    def test_tc011_valid_rgba_transparent_image(self):
        image_path = self.make_image("transparent.png", "RGBA", (32, 32), (255, 0, 0, 0))

        result, _ = load_and_preprocess_images_square([image_path], target_size=64)

        self.assertEqual(tuple(result.shape), (1, 3, 64, 64))
        torch.testing.assert_close(result[0, :, 32, 32], torch.ones(3))

    def test_tc012_nonexistent_image_path(self):
        missing_path = str(self.temp_path / "missing.png")

        with self.assertRaises(FileNotFoundError):
            load_and_preprocess_images_square([missing_path], target_size=518)
