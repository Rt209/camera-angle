class VisualPoseError(RuntimeError):
    """Base error for the visual pose pipeline."""


class ImageLoadError(VisualPoseError):
    """Raised when an image cannot be loaded as a frame."""

