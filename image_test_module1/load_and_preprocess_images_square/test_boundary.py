from tests.common import ImageFixtureTestCase
from vggt.utils.load_fn import load_and_preprocess_images_square


class TestLoadAndPreprocessImagesSquareBoundary(ImageFixtureTestCase):
    """Boundary values for image count and target size."""

    def test_tc013_zero_images(self):
        with self.assertRaisesRegex(ValueError, "At least 1 image is required"):
            load_and_preprocess_images_square([], target_size=518)

    def test_tc014_minimum_target_size_one(self):
        image_path = self.make_image("one_pixel.png", "RGB", (1, 1), (255, 0, 0))

        result, coords = load_and_preprocess_images_square([image_path], target_size=1)

        self.assertEqual(tuple(result.shape), (1, 3, 1, 1))
        self.assertEqual(tuple(coords.shape), (1, 6))

    def test_tc015_patch_size_target_fourteen(self):
        image_path = self.make_image("fourteen.png", "RGB", (14, 14), (0, 255, 0))

        result, coords = load_and_preprocess_images_square([image_path], target_size=14)

        self.assertEqual(tuple(result.shape), (1, 3, 14, 14))
        self.assertEqual(tuple(coords.shape), (1, 6))
