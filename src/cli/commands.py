from __future__ import annotations

from pathlib import Path

from rich.console import Console

from src.app.video_pipeline import run_video_pose_pipeline
from src.cli.parser import build_parser
from src.app.pipeline import run_stage_4_7_pose_pipeline, run_visual_pose_pipeline
from src.contexts.input.adapters.video_source import FrameSamplingConfig
from src.contexts.camera_model.domain.intrinsics import load_camera_intrinsics
from src.contexts.camera_model.services.kitti_calibration_loader import load_kitti_calibration
from src.contexts.output.services.rich_table_writer import print_pose_report
from src.io.file_validator import FileValidationError, resolve_image_path
from src.metadata.exif_reader import ExifReadError, read_metadata
from src.output.json_writer import to_json, write_json
from src.output.rich_table import print_report
from src.shared.errors import VisualPoseError
from src.shared.repository_paths import RepositoryPaths
from src.shared.run_directory import RunDirectoryService


def main() -> int:
    console = Console(stderr=True)
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.camera_intrinsics and args.kitti_calibration_dir:
            parser.error(
                "Use either --camera-intrinsics or --kitti-calibration-dir, not both."
            )
        if args.kitti_calibration_dir:
            camera_intrinsics = load_kitti_calibration(
                Path(args.kitti_calibration_dir), args.kitti_camera_index
            ).intrinsics
        elif args.camera_intrinsics:
            camera_intrinsics = load_camera_intrinsics(Path(args.camera_intrinsics))
        else:
            camera_intrinsics = None

        if args.video:
            if args.path:
                parser.error("Use either --path for a single image or --video for offline video, not both.")
            output_dir = Path(args.output_dir) if args.output_dir else (
                RunDirectoryService(RepositoryPaths.discover().outputs_root).next_run_path() / "geometry"
            )
            result = run_video_pose_pipeline(
                Path(args.video),
                output_dir,
                sampling_config=FrameSamplingConfig(
                    sample_every=args.sample_every,
                    target_fps=args.target_fps,
                ),
                write_overlay=args.write_overlay,
                debug_sampled_frames=args.debug_sampled_frames,
                camera_intrinsics=camera_intrinsics,
            )
            data = result.to_dict()
            if args.json:
                if args.output:
                    write_json(data, Path(args.output))
                    console.print(f"[green]JSON written to {args.output}[/green]")
                else:
                    print(to_json(data))
            else:
                console.print(f"[green]Video pose CSV written to {result.csv_path}[/green]")
                console.print(f"[green]Video pose JSON written to {result.json_path}[/green]")
                if result.overlay_path is not None:
                    console.print(f"[green]Predicted overlay written to {result.overlay_path}[/green]")
                console.print(f"Sampled frames: {len(result.frame_results)}")
            return 0

        if not args.path:
            parser.error("Provide --path for an image or --video for offline video.")

        image_path = resolve_image_path(args.path)
        if args.metadata:
            report = read_metadata(image_path)
            data = report.to_dict()
        elif args.stage_0_3:
            result = run_visual_pose_pipeline(
                image_path, Path(args.debug_dir) if args.debug_dir else None
            )
            data = result.to_dict()
        else:
            result = run_stage_4_7_pose_pipeline(
                image_path,
                Path(args.debug_dir) if args.debug_dir else None,
                camera_intrinsics=camera_intrinsics,
            )
            data = result.to_dict()

        if args.output and not args.json:
            console.print("[yellow]--output is only used with --json; printing table instead.[/yellow]")

        if args.json:
            if args.output:
                write_json(data, Path(args.output))
                console.print(f"[green]JSON written to {args.output}[/green]")
            else:
                print(to_json(data))
        else:
            if args.metadata:
                print_report(data)
            else:
                print_pose_report(data)

        return 0
    except FileValidationError as exc:
        console.print(f"[red]Input error:[/red] {exc}")
    except ExifReadError as exc:
        console.print(f"[red]Metadata error:[/red] {exc}")
    except VisualPoseError as exc:
        console.print(f"[red]Visual pose error:[/red] {exc}")
    except OSError as exc:
        console.print(f"[red]Output error:[/red] {exc}")

    return 1
