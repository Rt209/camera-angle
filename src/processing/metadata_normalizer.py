from pathlib import Path

from src.metadata.exif_reader import read_metadata
from src.metadata.metadata_model import MetadataReport


def build_metadata_report(path: Path) -> MetadataReport:
    return read_metadata(path)
