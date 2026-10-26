"""Hermes-owned executable locations, independent of other installed modules."""
import json
import os
from pathlib import Path
MODULE_ROOT=Path(__file__).resolve().parents[1]
ROOT=Path(os.environ['PLATFORM_ROOT']).resolve() if os.environ.get('PLATFORM_ROOT') else next(
    (parent for parent in MODULE_ROOT.parents if (parent/'backend/platform_modules.py').is_file()),MODULE_ROOT)
GIT_DIR=ROOT/'.git/modules/hermes-engine'
GIT_ARGS=('--git-dir',str(GIT_DIR),'--work-tree',str(ROOT/'backend/ai_agent/choki/engine/upstream')) if GIT_DIR.is_dir() else ()
PM_RUNTIME=ROOT/'runtime/shared/engines/hermes-pm'
def _python():
    installs=ROOT/'runtime/ai_agent/choki/installs'
    executable=Path('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    selections=sorted(installs.glob('*/pm-runtime/selected.json'),key=lambda path:path.stat().st_mtime,reverse=True)
    for selection in selections:
        try:
            generation=(selection.parent/json.loads(selection.read_text(encoding='utf-8'))['generation']).resolve()
            if generation.is_relative_to(selection.parent.resolve()) and (generation/executable).is_file():return generation/executable
        except (OSError,KeyError,TypeError,ValueError):continue
    return installs/'unprepared'/executable
PYTHON=_python()
