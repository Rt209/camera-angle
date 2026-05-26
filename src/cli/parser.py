import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="visual-pose-angle-detector",
        description=(
            "Estimate visual pose angles from a single image or offline video. "
            "The default pipeline runs Stage 4-7; use --stage-0-3 for roll-only compatibility."
        ),
    )
    parser.add_argument("--path", help="Path to a JPEG/PNG/HEIC/HEIF/TIFF image.")
    parser.add_argument("--video", help="Path to an offline video file.")
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
    parser.add_argument("--sample-every", type=int, default=1, help="Sample every N video frames. Default: 1.")
    parser.add_argument("--target-fps", type=float, help="Sample video near this FPS instead of --sample-every.")
    parser.add_argument(
        "--output-dir",
        default="outputs/video_pose",
        help="Directory for video pose CSV/JSON/overlay outputs.",
    )
    parser.add_argument("--write-overlay", action="store_true", help="Write predicted_pose_overlay.mp4 for video input.")
    parser.add_argument(
        "--debug-sampled-frames",
        action="store_true",
        help="Keep per-sampled-frame debug images under the video output directory.",
    )
    return parser
