"""Module-owned locations; the host supplies a platform root only when connected."""
import os
from pathlib import Path
MODULE_ROOT=Path(__file__).resolve().parent.parent
_host=MODULE_ROOT.parent.parent
ROOT=Path(os.environ.get('PLATFORM_ROOT') or (_host if (_host/'backend/platform_modules.py').is_file() else MODULE_ROOT)).resolve()
CONFIG_DIR=MODULE_ROOT/'configs'
