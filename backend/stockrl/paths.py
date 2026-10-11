"""Paths used inside frozen Expert definitions."""
from pathlib import Path
PROJECT_ROOT=Path(__file__).resolve().parents[2]
DEFAULT_MODEL_DIR=Path.home()/'Desktop'/'모델'

def expert_weight_path(path):return Path(path).expanduser()

def ensure_project_path(path: str | Path, label: str = "runtime") -> Path:
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate
    root = PROJECT_ROOT.resolve()
    resolved = candidate.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"StockRL {label} must stay inside the project folder: {root}")
    return resolved
