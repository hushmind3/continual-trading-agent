"""Compatibility name for the module-owned source package."""
from pathlib import Path
import os
_module=Path(__file__).resolve().parents[2]/'modules/finance/backend'
if not (_module/'__init__.py').is_file():raise ModuleNotFoundError("Module is detached: finance")
__path__=[str(_module)]
__file__=str(_module/'__init__.py')
exec(compile((_module/'__init__.py').read_text(encoding='utf8'),__file__,'exec'),globals())
