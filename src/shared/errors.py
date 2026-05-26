class VisualPoseError(RuntimeError):
    """Base error for the visual pose pipeline."""


class ImageLoadError(VisualPoseError):
    """Raised when an image cannot be loaded as a frame."""


class VideoSourceError(VisualPoseError):
    """Raised when a video cannot be opened or sampled."""


class VideoOutputError(VisualPoseError):
    """Raised when video pose outputs cannot be written."""
