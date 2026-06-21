from __future__ import annotations

import argparse
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import cv2


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}
TOOLS_DIR = Path(__file__).resolve().parents[1]
DEFAULT_IMAGE_DIR = TOOLS_DIR / "input" / "images"
DEFAULT_POSE_DIR = TOOLS_DIR / "input" / "oxts"
DEFAULT_OUTPUT_PATH = TOOLS_DIR / "output" / "kitti_pose_overlay.mp4"


@dataclass(frozen=True)
class PoseAngles:
    yaw_deg: float
    pitch_deg: float
    roll_deg: float


def natural_key(path: Path) -> list[object]:
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", path.name)]


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


def parse_pose_text(text: str) -> PoseAngles | None:
    labelled = {
        key: re.search(rf"{key}\s*:\s*([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)", text)
        for key in ("yaw_deg", "pitch_deg", "roll_deg")
    }
    if all(match is not None for match in labelled.values()):
        return PoseAngles(
            yaw_deg=float(labelled["yaw_deg"].group(1)),
            pitch_deg=float(labelled["pitch_deg"].group(1)),
            roll_deg=float(labelled["roll_deg"].group(1)),
        )

    numeric_line = next(
        (line for line in text.splitlines() if re.match(r"^\s*[-+]?\d", line)),
        "",
    )
    values = [float(value) for value in numeric_line.split()]
    if len(values) >= 6:
        # KITTI raw OXTS stores: lat lon alt roll pitch yaw ... with angles in radians.
        roll_rad, pitch_rad, yaw_rad = values[3], values[4], values[5]
        return PoseAngles(
            yaw_deg=math.degrees(yaw_rad),
            pitch_deg=math.degrees(pitch_rad),
            roll_deg=math.degrees(roll_rad),
        )
    return None


def load_poses(pose_path: Path) -> list[PoseAngles]:
    if pose_path.is_dir():
        txt_files = sorted(pose_path.glob("*.txt"), key=natural_key)
        poses = [parse_pose_text(path.read_text(encoding="utf-8", errors="replace")) for path in txt_files]
    elif pose_path.is_file():
        text = pose_path.read_text(encoding="utf-8", errors="replace")
        if "yaw_deg" in text and "pitch_deg" in text and "roll_deg" in text:
            poses = [parse_pose_text(text)]
        else:
            poses = [parse_pose_text(line) for line in text.splitlines() if line.strip()]
    else:
        raise ValueError(f"Pose path does not exist: {pose_path}")

    valid_poses = [pose for pose in poses if pose is not None]
    if not valid_poses:
        raise ValueError(f"No KITTI pose records found in: {pose_path}")
    return valid_poses


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
