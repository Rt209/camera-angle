import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="photo-metadata-geometry-analyzer",
        description="Read EXIF metadata and prepare supported geometry analysis.",
    )
    parser.add_argument("--path", required=True, help="Path to a JPEG/HEIC/HEIF/TIFF image.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of Rich tables.")
    parser.add_argument("--output", help="Write JSON output to a file. Use with --json.")
    return parser
