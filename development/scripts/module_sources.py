"""Install a relocatable source hook inside a module's own Python environment."""
from pathlib import Path
import sys

BOOTSTRAP='''import importlib.abc,importlib.util,json,sys
from pathlib import Path
def install():
 root=next((p for p in Path(sys.prefix).resolve().parents if (p/'module.json').is_file()),None)
 if root is None:return
 prefix=Path(sys.prefix).resolve();marker=prefix/'module-executable-root.txt'
 if not marker.is_file() or marker.read_text(encoding='utf8')!=str(prefix):
  import os
  with (prefix/'module-executable.lock').open('a+b') as guard:
   guard.seek(0,os.SEEK_END)
   if guard.tell()==0:guard.write(b'0');guard.flush()
   guard.seek(0)
   if sys.platform=='win32':
    import msvcrt
    msvcrt.locking(guard.fileno(),msvcrt.LK_LOCK,1)
   else:
    import fcntl
    fcntl.flock(guard.fileno(),fcntl.LOCK_EX)
   try:
    if not marker.is_file() or marker.read_text(encoding='utf8')!=str(prefix):
     from importlib.metadata import distributions
     from pip._vendor.distlib.scripts import ScriptMaker
     maker=ScriptMaker(None,str(prefix/('Scripts' if sys.platform=='win32' else 'bin')))
     maker.executable=sys.executable;maker.variants={''};maker.clobber=True
     for distribution in distributions():
      for entry in distribution.entry_points:
       if entry.group=='console_scripts':maker.make(entry.name+' = '+entry.value)
     marker.write_text(str(prefix),encoding='utf8')
   finally:
    guard.seek(0)
    if sys.platform=='win32':msvcrt.locking(guard.fileno(),msvcrt.LK_UNLCK,1)
    else:fcntl.flock(guard.fileno(),fcntl.LOCK_UN)
 name=json.loads((root/'module.json').read_text(encoding='utf8')).get('runtime',{}).get('package')
 if not name:return
 class Finder(importlib.abc.MetaPathFinder):
  def find_spec(self,fullname,path=None,target=None):
   if fullname==name:return importlib.util.spec_from_file_location(name,root/'backend/__init__.py',submodule_search_locations=[str(root/'backend')])
 sys.meta_path.insert(0,Finder())
'''

def install(target):
    target=Path(target)
    site=target/'Lib/site-packages' if sys.platform=='win32' else target/f'lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages'
    site.mkdir(parents=True,exist_ok=True)
    (site/'_module_source.py').write_text(BOOTSTRAP,encoding='utf8')
    (site/'module-source.pth').write_text('import _module_source; _module_source.install()\n',encoding='utf8')
