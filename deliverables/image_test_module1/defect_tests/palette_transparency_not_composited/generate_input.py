"""Generate deterministic transparency fixtures for DEF-IMG-003."""

from pathlib import Path

from PIL import Image


INPUT_DIR = Path(__file__).resolve().parent / "input"


def main():
    INPUT_DIR.mkdir(parents=True, exist_ok=True)

    palette_image = Image.new("P", (14, 14), 0)
    palette = [255, 0, 0] + [0, 0, 0] * 255
    palette_image.putpalette(palette)
    palette_image.info["transparency"] = 0
    palette_image.save(INPUT_DIR / "fully_transparent_palette_14x14.png")

    rgba_image = Image.new("RGBA", (14, 14), (255, 0, 0, 0))
    rgba_image.save(INPUT_DIR / "fully_transparent_rgba_14x14.png")
    print("Generated palette and RGBA transparency fixtures")


if __name__ == "__main__":
    main()
