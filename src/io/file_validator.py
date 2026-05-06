from pathlib import Path


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".heic", ".heif", ".tif", ".tiff"}


class FileValidationError(ValueError):
    """Raised when the input image path is invalid."""


def validate_image_path(path_value: str) -> Path:
    path = Path(path_value).expanduser()

    if not path.exists():
        raise FileValidationError(f"File does not exist: {path}")
    if not path.is_file():
        raise FileValidationError(f"Path is not a file: {path}")
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise FileValidationError(
            f"Unsupported file extension '{path.suffix}'. Supported: {supported}"
        )

    return path
