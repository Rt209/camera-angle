from __future__ import annotations

from pathlib import Path

from rich.console import Console

from src.cli.parser import build_parser
from src.app.pipeline import run_stage_4_7_pose_pipeline, run_visual_pose_pipeline
from src.contexts.output.services.rich_table_writer import print_pose_report
from src.io.file_validator import FileValidationError, resolve_image_path
from src.metadata.exif_reader import ExifReadError, read_metadata
from src.output.json_writer import to_json, write_json
from src.output.rich_table import print_report
from src.shared.errors import VisualPoseError


def main() -> int:
    console = Console(stderr=True)
    parser = build_parser()
    args = parser.parse_args()

    try:
        image_path = resolve_image_path(args.path)
        if args.metadata:
            report = read_metadata(image_path)
            data = report.to_dict()
        elif args.stage_0_3:
            result = run_visual_pose_pipeline(image_path, Path(args.debug_dir))
            data = result.to_dict()
        else:
            result = run_stage_4_7_pose_pipeline(image_path, Path(args.debug_dir))
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
