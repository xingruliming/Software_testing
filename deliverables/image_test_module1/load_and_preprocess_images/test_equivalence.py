import torch

from tests.common import ImageFixtureTestCase, fixed_input
from vggt.utils.load_fn import load_and_preprocess_images


class TestLoadAndPreprocessImagesEquivalence(ImageFixtureTestCase):
    """Equivalence partitions for valid and invalid input classes."""

    def test_tc001_valid_rgb_png_crop(self):
        image_path = fixed_input("pillow_hopper_rgb.png")

        result = load_and_preprocess_images([image_path], mode="crop")

        self.assertEqual(tuple(result.shape), (1, 3, 518, 518))
        self.assertEqual(result.dtype, torch.float32)
        self.assertGreaterEqual(float(result.min()), 0.0)
        self.assertLessEqual(float(result.max()), 1.0)
        self.assertGreater(float(result.std()), 0.0)

    def test_tc002_valid_rgba_png_pad(self):
        image_path = self.make_image("transparent.png", "RGBA", (640, 480), (255, 0, 0, 0))

        result = load_and_preprocess_images([image_path], mode="pad")

        self.assertEqual(tuple(result.shape), (1, 3, 518, 518))
        torch.testing.assert_close(result[0, :, 259, 259], torch.ones(3))
        torch.testing.assert_close(result[0, :, 0, 259], torch.ones(3))

    def test_tc003_valid_grayscale_tiff_crop(self):
        image_path = fixed_input("pillow_hopper_gray_4bpp.tif")

        result = load_and_preprocess_images([image_path], mode="crop")

        self.assertEqual(tuple(result.shape), (1, 3, 518, 518))
        torch.testing.assert_close(result[0, 0], result[0, 1])
        torch.testing.assert_close(result[0, 1], result[0, 2])

    def test_tc004_valid_same_size_image_batch(self):
        rgb_path = fixed_input("pillow_hopper_rgb.jpg")
        gray_path = fixed_input("pillow_hopper_gray_4bpp.tif")

        result = load_and_preprocess_images([rgb_path, gray_path], mode="crop")

        self.assertEqual(tuple(result.shape), (2, 3, 518, 518))
        self.assertFalse(torch.equal(result[0, 0], result[0, 1]))
        torch.testing.assert_close(result[1, 0], result[1, 1])
        torch.testing.assert_close(result[1, 1], result[1, 2])

    def test_tc005_invalid_processing_mode(self):
        image_path = self.make_image("red.png", "RGB", (64, 64), (255, 0, 0))

        with self.assertRaisesRegex(ValueError, "Mode must be either 'crop' or 'pad'"):
            load_and_preprocess_images([image_path], mode="resize")
