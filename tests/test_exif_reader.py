from pathlib import Path

from PIL import Image

from src.metadata.exif_reader import read_metadata


def test_read_metadata_handles_image_without_exif(tmp_path: Path) -> None:
    image_path = tmp_path / "plain.jpg"
    Image.new("RGB", (32, 24), color="white").save(image_path)

    report = read_metadata(image_path)
    data = report.to_dict()

    assert data["file_info"]["filename"] == "plain.jpg"
    assert data["image_parameters"]["ImageWidth"] == "32"
    assert data["image_parameters"]["ImageLength"] == "24"
    assert "No EXIF metadata found in this image." in data["warnings"]
