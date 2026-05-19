from pathlib import Path


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".tif", ".tiff"}
DEFAULT_IMAGE_DIR = Path("examples")


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


def resolve_image_path(path_value: str | None, default_dir: Path = DEFAULT_IMAGE_DIR) -> Path:
    if path_value:
        return validate_image_path(path_value)

    if not default_dir.exists():
        raise FileValidationError(
            f"No input image provided and default folder does not exist: {default_dir}. "
            "Create it or run with --path <image-file>."
        )
    if not default_dir.is_dir():
        raise FileValidationError(f"Default image path is not a folder: {default_dir}")

    image_paths = sorted(
        path
        for path in default_dir.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )

    if not image_paths:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise FileValidationError(
            f"No input image provided. Put one image in {default_dir}/ or run "
            f"with --path <image-file>. Supported: {supported}"
        )
    if len(image_paths) > 1:
        names = ", ".join(path.name for path in image_paths)
        raise FileValidationError(
            f"Multiple images found in {default_dir}/: {names}. "
            "Run with --path <image-file> to choose one."
        )

    return image_paths[0]
