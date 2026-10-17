"""Clone declared, already-installed distributions into private venvs, without downloads."""
from pathlib import Path
import argparse
import json
import os
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]

CLONE=r'''
from pathlib import Path
import importlib.metadata as metadata,json,os,shutil,subprocess,sys
try:
 from packaging.requirements import Requirement
 from packaging.utils import canonicalize_name
except ModuleNotFoundError:
 from pip._vendor.packaging.requirements import Requirement
 from pip._vendor.packaging.utils import canonicalize_name
source=Path(sys.prefix).resolve();target=Path(sys.argv[1]).resolve()
if target==source or target.is_relative_to(source/'Lib/site-packages'):raise ValueError('Invalid target environment')
requirements=json.loads(sys.argv[2]);found={canonicalize_name(d.metadata['Name']):d for d in metadata.distributions() if d.metadata.get('Name')}
selected={};extras={};pending=[Requirement(r) for r in requirements];missing=set()
while pending:
 requirement=pending.pop();name=canonicalize_name(requirement.name)
 if requirement.marker and not any(requirement.marker.evaluate({'extra':extra}) for extra in ('',*requirement.extras)):continue
 if name not in found:missing.add(name);continue
 wanted=extras.setdefault(name,set());new=not(name in selected) or not requirement.extras.issubset(wanted)
 if not new:continue
 wanted.update(requirement.extras);dist=found[name];selected[name]=dist
 for declared in dist.requires or []:
  dep=Requirement(declared)
  if not dep.marker or any(dep.marker.evaluate({'extra':extra}) for extra in ('',*wanted)):pending.append(dep)
if missing:raise RuntimeError('Installed environment lacks declared dependencies: '+', '.join(sorted(missing)))
python=target/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
if not python.is_file():subprocess.run([sys.executable,'-m','venv',str(target)],check=True)
count=0;total=0
for name,dist in sorted(selected.items()):
 for item in dist.files or []:
  src=Path(dist.locate_file(item)).resolve()
  if not src.is_file() or src.suffix in ('.pyc','.pyo'):continue
  if not src.is_relative_to(source):raise RuntimeError('External package source cannot be copied: '+str(src))
  relative=src.relative_to(source)
  if relative.parts[0].lower() in ('scripts','bin'):continue
  dest=target/relative
  if dest.exists() and dest.stat().st_size==src.stat().st_size and dest.stat().st_mtime_ns==src.stat().st_mtime_ns:continue
  dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest);count+=1;total+=src.stat().st_size
try:from pip._vendor.distlib.scripts import ScriptMaker
except ModuleNotFoundError:
 sys.path.insert(0,str(target/'Lib/site-packages'))
 from pip._vendor.distlib.scripts import ScriptMaker
maker=ScriptMaker(None,str(python.parent));maker.executable=str(python);maker.variants={''};maker.clobber=True
for dist in selected.values():
 for entry in dist.entry_points:
  if entry.group=='console_scripts':maker.make(entry.name+' = '+entry.value)
receipt={'source_python':sys.executable,'python':str(python),'packages':{name:dist.version for name,dist in sorted(selected.items())},'copied_files':count,'copied_bytes':total,'system_site_packages':False}
(target/'module-environment.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
print(json.dumps({'python':str(python),'packages':len(selected),'copied_files':count,'copied_bytes':total}))
'''

def install(source, target, requirements):
    target=Path(target).resolve()
    if not target.is_relative_to(ROOT):raise ValueError('Environment must stay in the workspace')
    result=subprocess.run([str(source),'-I','-X','utf8','-B','-c',CLONE,str(target),json.dumps(requirements)])
    if result.returncode:raise SystemExit(result.returncode)
    from module_sources import install as install_sources
    install_sources(target)
    return result

def declared(path):
    return [line.strip() for line in Path(path).read_text(encoding='utf8').splitlines()
            if line.strip() and not line.lstrip().startswith(('#','-'))]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('module',choices=('finance','rea','hermes','platform','kiwoom'));args=parser.parse_args()
    if args.module=='kiwoom':
        source=ROOT/'.venv/kiwoom/Scripts/python.exe';target=ROOT/'modules/finance/.venv/kiwoom'
        requirements=declared(ROOT/'modules/finance/dependencies/kiwoom.txt')
    elif args.module=='hermes':
        source=ROOT/'.venv/hermes/Scripts/python.exe';target=ROOT/'modules/hermes/.venv'
        requirements=declared(ROOT/'modules/hermes/backend/engine/requirements.txt')
    else:
        source=ROOT/'.venv/Scripts/python.exe'
        target=ROOT/'.venv/platform' if args.module=='platform' else ROOT/'modules'/args.module/'.venv'
        requirements=['fastapi','uvicorn[standard]','psutil','requests'] if args.module=='platform' else declared(ROOT/'modules'/args.module/('dependencies/operations.txt' if args.module=='finance' else 'requirements.txt'))
    install(source,target,requirements)
if __name__=='__main__':main()
