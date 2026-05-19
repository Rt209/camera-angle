import argparse


class TraditionalChineseHelpFormatter(argparse.RawTextHelpFormatter):
    def _format_usage(self, usage, actions, groups, prefix):
        return super()._format_usage(usage, actions, groups, "用法: ")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="visual-pose-angle-detector",
        usage="python main.py [選項]",
        description=(
            "從單張圖片估計視覺姿態角度。\n"
            "目前 Stage 0-3 只估計 roll；yaw 與 pitch 會輸出為 null。"
        ),
        add_help=False,
        formatter_class=TraditionalChineseHelpFormatter,
    )
    parser._optionals.title = "選項"
    parser.add_argument("-h", "--help", action="help", help="顯示這份說明後結束。")
    parser.add_argument(
        "--path",
        help=(
            "圖片路徑，支援 JPEG/PNG/HEIC/HEIF/TIFF。\n"
            "若省略，會從專案 examples/ 資料夾尋找一張支援格式的圖片。"
        ),
    )
    parser.add_argument("--json", action="store_true", help="改用 JSON 輸出，而不是 Rich Table。")
    parser.add_argument("--output", help="將 JSON 輸出寫入檔案；需搭配 --json 使用。")
    parser.add_argument(
        "--debug-dir",
        default="debug",
        help="Stage 0-3 debug 圖片輸出資料夾。預設為 debug。",
    )
    parser.add_argument(
        "--metadata",
        action="store_true",
        help="執行舊版 EXIF / metadata 報告，而不是 visual pose pipeline。",
    )
    return parser
