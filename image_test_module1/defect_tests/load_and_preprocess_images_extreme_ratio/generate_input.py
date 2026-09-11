"""Generate deterministic image fixtures for DEF-IMG-001."""

from pathlib import Path

from PIL import Image


INPUT_DIR = Path(__file__).resolve().parent / "input"


def main():
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (518, 1), (255, 0, 0)).save(INPUT_DIR / "extreme_wide_518x1.png")
    Image.new("RGB", (518, 14), (0, 255, 0)).save(INPUT_DIR / "valid_boundary_518x14.png")
    print("Generated extreme_wide_518x1.png and valid_boundary_518x14.png")


if __name__ == "__main__":
    main()
