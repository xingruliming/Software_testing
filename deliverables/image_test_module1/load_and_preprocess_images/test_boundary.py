from tests.common import ImageFixtureTestCase
from vggt.utils.load_fn import load_and_preprocess_images


class TestLoadAndPreprocessImagesBoundary(ImageFixtureTestCase):
    """Boundary values for image count and image dimensions."""

    def test_tc006_zero_images(self):
        with self.assertRaisesRegex(ValueError, "At least 1 image is required"):
            load_and_preprocess_images([], mode="crop")

    def test_tc007_one_by_one_image(self):
        image_path = self.make_image("one_pixel.png", "RGB", (1, 1), (255, 0, 0))

        result = load_and_preprocess_images([image_path], mode="crop")

        self.assertEqual(tuple(result.shape), (1, 3, 518, 518))

    def test_tc008_minimum_patch_aligned_height(self):
        image_path = self.make_image("height_14.png", "RGB", (518, 14), (0, 255, 0))

        result = load_and_preprocess_images([image_path], mode="crop")

        self.assertEqual(tuple(result.shape), (1, 3, 14, 518))
