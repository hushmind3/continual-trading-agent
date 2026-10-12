"""Install missing distributions; preserve installed packages and official sources."""
from pathlib import Path
import json,os,re,subprocess,tempfile,venv
ROOT=Path(__file__).resolve().parents[1]

def main():
    os.environ['PYTHONUTF8']='1'
    python=ROOT/'.venv/Scripts/python.exe'
    if not python.exists():venv.EnvBuilder(with_pip=True,system_site_packages=True).create(ROOT/'.venv')
    subprocess.run(['git','submodule','update','--init','FinRL-X'],cwd=ROOT,check=True)
    probe=subprocess.check_output([str(python),'-c','import importlib.metadata,json; print(json.dumps([d.metadata["Name"].lower().replace("_","-") for d in importlib.metadata.distributions()]))'],text=True)
    installed=set(json.loads(probe))
    pins=subprocess.check_output([str(python),'-c','import importlib.metadata; names={d.metadata["Name"] for d in importlib.metadata.distributions()}; print("\\n".join(n+"=="+importlib.metadata.version(n) for n in sorted(names)))'],text=True)
    temporary=tempfile.TemporaryDirectory(prefix='finrl-install-');constraints=Path(temporary.name)/'constraints.txt';constraints.write_text(pins,encoding='utf8')
    for requirement in (ROOT/'requirements/operations.txt').read_text().splitlines():
        requirement=requirement.strip()
        if not requirement or requirement.startswith('#'):continue
        name=re.split(r'[<>=@\[ ]',requirement,1)[0].lower().replace('_','-')
        if name in installed:continue
        subprocess.run([str(python),'-m','pip','install','--extra-index-url','https://download.pytorch.org/whl/cu132','-c',str(constraints),requirement],cwd=ROOT,check=True)
        installed.add(name)
    subprocess.run([str(python),'-m','pip','install','--no-deps','-e',str(ROOT)],cwd=ROOT,check=True)
    temporary.cleanup()
    print('설치 완료. 서버켜기.cmd를 실행하세요. 기존 패키지는 재설치하거나 업그레이드하지 않았습니다.')

if __name__=='__main__':main()
