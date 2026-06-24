from pathlib import Path


def test_evaluation_tools_are_thin_and_src_does_not_import_tools() -> None:
    root = Path(__file__).resolve().parents[2]
    wrappers = [
        root / "tools/evaluation/evaluate_video_pose_against_oxts.py",
        root / "tools/evaluation/evaluate_uncalibrated_pose_overlay_against_oxts.py",
    ]
    for wrapper in wrappers:
        text = wrapper.read_text(encoding="utf-8")
        assert "import numpy" not in text
        assert "import matplotlib" not in text
        assert "def compute_" not in text
        assert "def render_report" not in text
        assert len(text.splitlines()) <= 120

    for source in (root / "src").rglob("*.py"):
        text = source.read_text(encoding="utf-8")
        assert "from tools" not in text
        assert "import tools" not in text


def test_dataset_tool_uses_src_oxts_loader() -> None:
    root = Path(__file__).resolve().parents[2]
    text = (root / "tools/dataset/kitti_pose_video.py").read_text(encoding="utf-8")
    assert "src.contexts.evaluation.services.oxts_loader" in text
    assert "def load_poses" not in text
