"""Install each language environment at its owning module; the host stays minimal."""
from pathlib import Path
import os,subprocess,sys,venv
from module_sources import install as install_sources
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from platform_native import npm_command

def environment(directory,requirements,constraints=None,gpu=False,python_version=None):
 if gpu and sys.platform=='darwin':raise RuntimeError('CUDA 전용 요구사항은 macOS에 설치하지 않습니다.')
 target=ROOT/directory;python=target/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
 if not python.is_file():
  if python_version:subprocess.run(['uv','venv','--python',python_version,'--seed',str(target)],check=True)
  else:venv.EnvBuilder(with_pip=True,system_site_packages=False).create(target)
 if 'include-system-site-packages = true' in (target/'pyvenv.cfg').read_text(encoding='utf8'):
  raise RuntimeError('전용 환경에서 시스템 패키지를 공유할 수 없습니다: '+str(target))
 args=[str(python),'-m','pip','install','--no-compile']
 if gpu:args+=['--extra-index-url','https://download.pytorch.org/whl/cu132']
 if constraints:args+=['-c',str(ROOT/constraints)]
 subprocess.run([*args,'-r',str(ROOT/requirements)],cwd=ROOT,check=True)
 subprocess.run([str(python),'-c',"import sys;sys.path.insert(0,'development/scripts');from module_sources import install;install(sys.prefix)"],cwd=ROOT,check=True)
 subprocess.run([str(python),'-m','pip','check'],check=True)
 return python

def main():
 os.environ['PYTHONUTF8']='1'
 host=environment('.venv/platform','development/scripts/requirements/platform.txt')
 for module in ('finance','rea'):
  if not (ROOT/'modules'/module/'module.json').is_file():continue
  if module=='finance' and sys.platform=='darwin':
   environment('modules/finance/.venv','modules/finance/dependencies/operations-macos.txt',python_version='3.11')
  elif module=='finance':
   environment('modules/finance/.venv','modules/finance/dependencies/operations.txt','modules/finance/dependencies/operations.lock.txt',gpu=True)
   environment('modules/finance/.venv/kiwoom','modules/finance/dependencies/kiwoom.txt','modules/finance/dependencies/kiwoom.lock.txt')
  else:
   rea=environment('modules/rea/.venv','modules/rea/requirements.txt','development/scripts/requirements/platform.txt')
   subprocess.run([str(rea),'-I','-c','from rea.program_analysis.operations import install;install()'],check=True)
 subprocess.run([*npm_command(),'ci','--no-audit','--no-fund'],cwd=ROOT,check=True)
 if (ROOT/'modules/hermes/module.json').is_file():
  subprocess.run([str(host),'-I',str(ROOT/'modules/hermes/backend/engine/setup.py')],check=True)
  install_sources(ROOT/'modules/hermes/.venv')
  subprocess.run([*npm_command(),'ci','--workspaces=false','--no-audit','--no-fund'],cwd=ROOT/'modules/hermes/backend/engine/browser',check=True)
 if sys.platform=='darwin':
  import shutil
  runner=shutil.which('llama-server')
  if not runner:raise RuntimeError('Homebrew의 llama.cpp 설치가 필요합니다: brew install llama.cpp')
  link=ROOT/'runtime/shared/engines/llama.cpp/llama-server';link.parent.mkdir(parents=True,exist_ok=True)
  if not link.exists():
   pending=link.with_name(link.name+'.tmp')
   pending.symlink_to(runner);pending.replace(link)
  print('플랫폼·금융·Hermes·REA 설치 완료. 서버켜기.command를 실행하세요. 금융은 macOS 전용 환경을 사용하며 Windows CUDA·키움 환경은 설치하지 않았습니다.')
 else:print('플랫폼과 각 모듈의 전용 환경 설치 완료. 서버켜기.cmd를 실행하세요.')
if __name__=='__main__':main()
