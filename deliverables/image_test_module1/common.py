import tempfile
import unittest
from pathlib import Path

from PIL import Image


INPUT_DIR = Path(__file__).resolve().parent / "input"


def fixed_input(name):
    """Return a version-controlled image fixture from tests/input."""
    return str(INPUT_DIR / name)


class ImageFixtureTestCase(unittest.TestCase):
    """Create disposable image fixtures for preprocessing tests."""

    def setUp(self):
        self._temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self._temp_dir.name)

    def tearDown(self):
        self._temp_dir.cleanup()

    def make_image(self, name, mode, size, color):
        image_path = self.temp_path / name
        Image.new(mode, size, color=color).save(image_path)
        return str(image_path)
