import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="visual-pose-angle-detector",
        description=(
            "Estimate visual pose angles from a single image. "
            "The default pipeline runs Stage 4-7; use --stage-0-3 for roll-only compatibility."
        ),
    )
    parser.add_argument("--path", required=True, help="Path to a JPEG/PNG/HEIC/HEIF/TIFF image.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of Rich tables.")
    parser.add_argument("--output", help="Write JSON output to a file. Use with --json.")
    parser.add_argument(
        "--debug-dir",
        default="debug",
        help="Directory for debug images.",
    )
    parser.add_argument(
        "--metadata",
        action="store_true",
        help="Run the legacy EXIF metadata report instead of the visual pose pipeline.",
    )
    parser.add_argument(
        "--stage-0-3",
        action="store_true",
        help="Run the Stage 0-3 roll-only pipeline for compatibility.",
    )
    return parser
