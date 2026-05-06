from __future__ import annotations

from pathlib import Path

from rich.console import Console

from src.cli.parser import build_parser
from src.io.file_validator import FileValidationError, validate_image_path
from src.metadata.exif_reader import ExifReadError, read_metadata
from src.output.json_writer import to_json, write_json
from src.output.rich_table import print_report


def main() -> int:
    console = Console(stderr=True)
    parser = build_parser()
    args = parser.parse_args()

    try:
        image_path = validate_image_path(args.path)
        report = read_metadata(image_path)
        data = report.to_dict()

        if args.output and not args.json:
            console.print("[yellow]--output is only used with --json; printing table instead.[/yellow]")

        if args.json:
            if args.output:
                write_json(data, Path(args.output))
                console.print(f"[green]JSON written to {args.output}[/green]")
            else:
                print(to_json(data))
        else:
            print_report(data)

        return 0
    except FileValidationError as exc:
        console.print(f"[red]Input error:[/red] {exc}")
    except ExifReadError as exc:
        console.print(f"[red]Metadata error:[/red] {exc}")
    except OSError as exc:
        console.print(f"[red]Output error:[/red] {exc}")

    return 1
