"""Install validated main/broker environments without sharing system packages."""
from pathlib import Path
import os,subprocess,venv
ROOT=Path(__file__).resolve().parents[1]

def main():
    os.environ['PYTHONUTF8']='1'
    subprocess.run(['git','submodule','update','--init','vendor/FinRL-X'],cwd=ROOT,check=True)
    env=os.environ.copy();env.update(MSGPACK_PUREPYTHON='1',PYYAML_FORCE_LIBYAML='0')
    for directory,requirements in (('.venv','operations.txt'),('.venv-kiwoom','kiwoom.txt')):
        target=ROOT/directory;python=target/'Scripts/python.exe'
        if not python.exists():venv.EnvBuilder(with_pip=True,system_site_packages=False).create(target)
        config=target/'pyvenv.cfg'
        if 'include-system-site-packages = true' in config.read_text(encoding='utf8'):
            raise RuntimeError(f'{directory}가 시스템 패키지를 공유합니다. 실행 중 작업을 종료하고 검증된 독립 환경으로 교체하세요.')
        command=[str(python),'-m','pip','install','--no-compile']
        if directory=='.venv':command+=['--extra-index-url','https://download.pytorch.org/whl/cu132']
        lock=ROOT/'scripts/requirements'/requirements.replace('.txt','.lock.txt')
        if lock.is_file():command+=['-c',str(lock)]
        subprocess.run([*command,'-r',str(ROOT/'scripts/requirements'/requirements)],cwd=ROOT,env=env,check=True)
        if directory=='.venv':
            subprocess.run([*command,'-r',str(ROOT/'scripts/requirements/verification.txt')],cwd=ROOT,env=env,check=True)
            subprocess.run([str(python),'-m','pip','install','--no-deps','-e',str(ROOT)],cwd=ROOT,check=True)
        subprocess.run([str(python),'-m','pip','check'],cwd=ROOT,check=True)
    rea_env=env.copy();rea_env['PYTHONPATH']=str(ROOT/'backend')
    subprocess.run([str(ROOT/'.venv/Scripts/python.exe'),'-c','from rea.program_analysis.operations import install;install()'],cwd=ROOT,env=rea_env,check=True)
    print('주 실행 환경·키움 SDK·REA 설치 완료. 서버켜기.cmd를 실행하세요.')

if __name__=='__main__':main()
