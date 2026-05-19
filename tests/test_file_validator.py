from pathlib import Path

import pytest

from src.io.file_validator import FileValidationError, resolve_image_path, validate_image_path


def test_validate_image_path_accepts_supported_file(tmp_path: Path) -> None:
    image = tmp_path / "photo.jpg"
    image.write_bytes(b"stub")

    assert validate_image_path(str(image)) == image


def test_validate_image_path_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileValidationError, match="does not exist"):
        validate_image_path(str(tmp_path / "missing.jpg"))


def test_validate_image_path_rejects_unsupported_extension(tmp_path: Path) -> None:
    text_file = tmp_path / "photo.txt"
    text_file.write_text("not an image", encoding="utf-8")

    with pytest.raises(FileValidationError, match="Unsupported file extension"):
        validate_image_path(str(text_file))


def test_resolve_image_path_uses_single_image_in_default_folder(tmp_path: Path) -> None:
    image = tmp_path / "photo.png"
    image.write_bytes(b"stub")

    assert resolve_image_path(None, tmp_path) == image


def test_resolve_image_path_requires_choice_when_default_folder_has_many_images(
    tmp_path: Path,
) -> None:
    (tmp_path / "first.jpg").write_bytes(b"stub")
    (tmp_path / "second.png").write_bytes(b"stub")

    with pytest.raises(FileValidationError, match="Multiple images found"):
        resolve_image_path(None, tmp_path)
