from pathlib import Path
from typing import Any

from PIL import Image


def register_heif_support() -> None:
    try:
        from pillow_heif import register_heif_opener
    except ImportError:
        return

    register_heif_opener()


def open_image(path: Path) -> Image.Image:
    register_heif_support()
    return Image.open(path)


def get_basic_image_info(image: Image.Image) -> dict[str, Any]:
    width, height = image.size
    return {
        "image_width": width,
        "image_height": height,
        "format": image.format,
        "mode": image.mode,
    }
