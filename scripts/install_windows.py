"""Install one operation environment and build the production React application."""
from pathlib import Path
import argparse
import os
import shutil
import subprocess
import sys
import venv

ROOT=Path(__file__).resolve().parents[1]
FRAMEWORKS=[
    'finrl-trading @ git+https://github.com/AI4Finance-Foundation/FinRL-Trading.git@4409abe925c904e570be78ebfb5e77ac3491dff8',
    'kwcli @ git+https://github.com/Kiwoom-Securities/Kiwoom-REST-API.git@953e5dbff123f437ab4d11a78a95191a685eb51f',
]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--prepare-only',action='store_true');args=parser.parse_args()
    os.environ['PYTHONUTF8']='1'
    if sys.version_info<(3,13):raise RuntimeError('Python 3.13 이상이 필요합니다.')
    (ROOT/'runtime'/'finrlx').mkdir(parents=True,exist_ok=True)
    if args.prepare_only:return 0
    env=ROOT/'.venv';python=env/'Scripts'/'python.exe'
    if not python.exists():venv.EnvBuilder(with_pip=True,system_site_packages=True).create(env)
    subprocess.run([str(python),'-m','pip','install','--disable-pip-version-check',
        '--extra-index-url','https://download.pytorch.org/whl/cu132','-r',str(ROOT/'requirements'/'operations.txt')],cwd=ROOT,check=True)
    # Only selected, verified library APIs are needed; optional Alpaca/LLM/UI stacks are not installed.
    subprocess.run([str(python),'-m','pip','install','--no-deps',*FRAMEWORKS,'-e',str(ROOT)],cwd=ROOT,check=True)
    npm=shutil.which('npm.cmd')
    if not npm:raise RuntimeError('Node.js LTS를 설치한 뒤 다시 실행하세요.')
    subprocess.run([npm,'ci'],cwd=ROOT/'frontend',check=True)
    subprocess.run([npm,'run','build'],cwd=ROOT/'frontend',check=True)
    print('설치 완료. 서버켜기.cmd를 실행하세요. 모델 파일은 바탕화면 모델 폴더를 사용합니다.')
    return 0


if __name__=='__main__':raise SystemExit(main())
