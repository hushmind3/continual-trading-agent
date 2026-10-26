"""Apply the versioned UI/host compatibility overlay to the complete official tree."""
from pathlib import Path
import subprocess
from locations import GIT_ARGS


def prepare(engine:Path):
    source=engine/'upstream'
    patch=engine/'patches/platform.patch'
    if not (source/'hermes').is_file():
        raise RuntimeError('공식 전체 소스가 없습니다. git submodule update --init으로 준비하세요.')
    if not patch.is_file():return
    command=['git',*GIT_ARGS,'-C',str(source),'apply','--ignore-space-change']
    if subprocess.run([*command,'--reverse','--check',str(patch)],capture_output=True).returncode==0:return
    check=subprocess.run([*command,'--check',str(patch)],capture_output=True,text=True,encoding='utf-8',errors='replace')
    if check.returncode:
        raise RuntimeError('공식 버전과 플랫폼 패치가 충돌합니다. 원본을 덮어쓰지 않았습니다.\n'+check.stderr[:1500])
    subprocess.run([*command,str(patch)],check=True)


if __name__=='__main__':prepare(Path(__file__).resolve().parent)
