"""Generate deterministic JPEG fixtures for DEF-IMG-002."""

from pathlib import Path

from PIL import Image


INPUT_DIR = Path(__file__).resolve().parent / "input"


def create_jpeg(path: Path, orientation: int | None):
    image = Image.new("RGB", (40, 20), (255, 0, 0))
    for x in range(20, 40):
        for y in range(20):
            image.putpixel((x, y), (0, 0, 255))
    if orientation is None:
        image.save(path, quality=100, subsampling=0)
    else:
        exif = Image.Exif()
        exif[274] = orientation
        image.save(path, quality=100, subsampling=0, exif=exif)


def main():
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    create_jpeg(INPUT_DIR / "control_no_orientation_40x20.jpg", None)
    create_jpeg(INPUT_DIR / "exif_orientation_6_stored_40x20.jpg", 6)
    print("Generated JPEG orientation fixtures")


if __name__ == "__main__":
    main()
