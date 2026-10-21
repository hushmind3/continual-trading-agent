"""Hermes-owned executable locations, independent of other installed modules."""
import os
from pathlib import Path
MODULE_ROOT=Path(__file__).resolve().parents[2]
_host=MODULE_ROOT.parent.parent
ROOT=Path(os.environ.get('PLATFORM_ROOT') or (_host if (_host/'backend/platform_modules.py').is_file() else MODULE_ROOT)).resolve()
PYTHON=MODULE_ROOT/'.venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
NODE_BIN=MODULE_ROOT/'backend/engine/browser/node_modules/.bin'
