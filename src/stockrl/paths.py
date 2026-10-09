"""Paths used inside frozen Expert definitions."""
from pathlib import Path

def expert_weight_path(path):return Path(path).expanduser()
