"""Original ASGI app and optional built UI in the exported app's single host."""
import importlib
import json
import os
from pathlib import Path
import sys
import site

root = Path(__file__).resolve().parent
metadata = json.loads((root / 'app-package.json').read_text(encoding='utf8'))
spec = metadata['adapter']; source = root / 'source'
work = (source / spec.get('directory', '.')).resolve()
if not work.is_relative_to(source.resolve()): raise ValueError('Invalid application folder')
os.chdir(work); sys.path.insert(0, str(work))
packages=source/'.platform-runtime/python'
if packages.is_dir():site.addsitedir(str(packages));sys.path.insert(0,str(packages))
module, name = spec['app'].split(':')
app = getattr(importlib.import_module(module), name)
if ui := spec.get('ui'):
    from fastapi.staticfiles import StaticFiles
    output = (source / ui.get('directory', '.') / ui.get('output', '.')).resolve()
    if not output.is_relative_to(source.resolve()): raise ValueError('Invalid UI folder')
    app.mount('/', StaticFiles(directory=str(output), html=True), name='original-ui')
