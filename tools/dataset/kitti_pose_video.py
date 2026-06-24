from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable

import cv2

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.contexts.evaluation.domain.pose_record import PoseAngles
from src.contexts.evaluation.services.oxts_loader import load_poses, natural_key, parse_pose_text


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_ROOT = REPOSITORY_ROOT / "data" / "samples" / "kitti"
DEFAULT_IMAGE_DIR = SAMPLE_ROOT / "images"
DEFAULT_POSE_DIR = SAMPLE_ROOT / "references" / "oxts"
DEFAULT_OUTPUT_PATH = SAMPLE_ROOT / "videos" / "kitti_pose_overlay.mp4"


def list_images(image_dir: Path) -> list[Path]:
    if not image_dir.is_dir():
        raise ValueError(f"Image directory does not exist: {image_dir}")
    images = sorted(
        (path for path in image_dir.iterdir() if path.suffix.lower() in IMAGE_EXTENSIONS),
        key=natural_key,
    )
    if not images:
        raise ValueError(f"No images found in: {image_dir}")
    return images


def draw_pose_overlay(frame, pose: PoseAngles, frame_index: int, total_frames: int):
    height, width = frame.shape[:2]
    scale = max(0.55, min(width, height) / 900.0)
    thickness = max(1, round(scale * 2))
    line_height = int(28 * scale)
    padding = int(14 * scale)
    origin_x = padding
    origin_y = padding + line_height
    lines = [
        f"Frame {frame_index + 1}/{total_frames}",
        f"Yaw   {pose.yaw_deg:8.3f} deg",
        f"Pitch {pose.pitch_deg:8.3f} deg",
        f"Roll  {pose.roll_deg:8.3f} deg",
    ]

    box_width = int(max(cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, scale, thickness)[0][0] for line in lines) + padding * 2)
    box_height = line_height * len(lines) + padding
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (box_width, box_height), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)

    for row, line in enumerate(lines):
        y = origin_y + row * line_height
        cv2.putText(
            frame,
            line,
            (origin_x, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            scale,
            (255, 255, 255),
            thickness,
            cv2.LINE_AA,
        )
    return frame


def parse_size(value: str) -> tuple[int, int]:
    match = re.fullmatch(r"(\d+)x(\d+)", value.lower())
    if not match:
        raise argparse.ArgumentTypeError("Size must use WIDTHxHEIGHT, for example 1242x375")
    return int(match.group(1)), int(match.group(2))


def build_video(
    image_paths: Iterable[Path],
    poses: list[PoseAngles],
    output_path: Path,
    fps: float,
    size: tuple[int, int] | None,
    overlay_pose: bool,
) -> int:
    image_paths = list(image_paths)
    frame_count = min(len(image_paths), len(poses))
    if frame_count == 0:
        raise ValueError("No frame/pose pairs to write.")

    first = cv2.imread(str(image_paths[0]))
    if first is None:
        raise ValueError(f"Could not read image: {image_paths[0]}")
    width, height = size if size else (first.shape[1], first.shape[0])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(
        str(output_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height),
    )
    if not writer.isOpened():
        raise ValueError(f"Could not open video writer for: {output_path}")

    try:
        for index in range(frame_count):
            frame = cv2.imread(str(image_paths[index]))
            if frame is None:
                raise ValueError(f"Could not read image: {image_paths[index]}")
            if frame.shape[1] != width or frame.shape[0] != height:
                frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
            if overlay_pose:
                frame = draw_pose_overlay(frame, poses[index], index, frame_count)
            writer.write(frame)
    finally:
        writer.release()
    return frame_count


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a KITTI frame video with yaw/pitch/roll overlay.")
    parser.add_argument(
        "--images",
        type=Path,
        default=DEFAULT_IMAGE_DIR,
        help=f"Directory containing KITTI frame images. Default: {DEFAULT_IMAGE_DIR}",
    )
    parser.add_argument(
        "--poses",
        type=Path,
        default=DEFAULT_POSE_DIR,
        help="KITTI OXTS txt file, multi-line txt, or directory containing per-frame txt files.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f"Output mp4 path. Default: {DEFAULT_OUTPUT_PATH}",
    )
    parser.add_argument("--fps", type=float, default=10.0, help="Output video frame rate. Default: 10.")
    parser.add_argument("--size", type=parse_size, help="Optional output size, for example 1242x375.")
    parser.add_argument(
        "--no-overlay",
        action="store_true",
        help="Write the video without yaw/pitch/roll text overlay.",
    )
    args = parser.parse_args()

    image_paths = list_images(args.images)
    poses = load_poses(args.poses)
    written = build_video(image_paths, poses, args.output, args.fps, args.size, not args.no_overlay)

    if len(image_paths) != len(poses):
        print(f"Warning: images={len(image_paths)} poses={len(poses)}; wrote {written} paired frames.")
    print(f"Wrote {written} frames to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
