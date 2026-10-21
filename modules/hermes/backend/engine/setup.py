"""Install selected dependencies and the upstream-pinned desktop driver, without Hermes PM bootstrap."""
from pathlib import Path
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile
import tarfile
import platform
import tempfile

ENGINE = Path(__file__).resolve().parent
sys.path.insert(0,str(ENGINE))
from locations import ROOT, MODULE_ROOT, PYTHON


def install_driver():
    lock = json.loads((ENGINE / 'upstream/pm/lock.json').read_text(encoding='utf-8'))
    system={'win32':'win32','darwin':'darwin','linux':'linux'}.get(sys.platform)
    machine='arm64' if platform.machine().lower() in ('arm64','aarch64') else 'x64'
    artifact = lock['packages']['cua-driver']['artifacts'][f'{system}-{machine}']
    target = ROOT / 'runtime/ai_agent/Hermes/tools/cua-driver'
    binary = target / ('cua-driver.exe' if os.name=='nt' else 'cua-driver')
    receipt = target / 'receipt.json'
    if binary.is_file() and receipt.is_file():
        saved = json.loads(receipt.read_text(encoding='utf-8'))
        if saved.get('sha256') == artifact['sha256'] and saved.get('binary_sha256') == hashlib.sha256(binary.read_bytes()).hexdigest():
            return binary
    with urllib.request.urlopen(artifact['url'], timeout=90) as response:
        archive = response.read()
    if hashlib.sha256(archive).hexdigest() != artifact['sha256']:
        raise RuntimeError('cua-driver 다운로드의 SHA-256이 공식 잠금 정보와 다릅니다.')
    target.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.install-',dir=target) as directory:
        staging=Path(directory)
        if artifact['url'].endswith('.zip'):
            with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
                for member in bundle.infolist():
                    if member.is_dir(): continue
                    path = (staging / member.filename).resolve()
                    if not path.is_relative_to(staging.resolve()):
                        raise RuntimeError('드라이버 압축 경로가 설치 폴더 밖을 가리킵니다.')
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(bundle.read(member))
        else:
            with tarfile.open(fileobj=io.BytesIO(archive),mode='r:gz') as bundle:
                bundle.extractall(staging,filter='data')
        matches = [path for path in staging.rglob('cua-driver*') if path.is_file() and path.suffix not in ('.json','.exe')]
        if os.name=='nt': matches=list(staging.rglob('cua-driver*.exe'))
        if not matches: raise RuntimeError('cua-driver 실행파일을 찾을 수 없습니다.')
        shutil.copyfile(matches[0], binary)
    if os.name!='nt': binary.chmod(0o755)
    receipt.write_text(json.dumps({**artifact, 'binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest()}, indent=2), encoding='utf-8')
    return binary


def main():
    interpreter = PYTHON
    uv = shutil.which('uv')
    if not uv: raise RuntimeError('설치된 uv 실행기를 찾을 수 없습니다.')
    if not interpreter.exists():
        python = subprocess.check_output(['py', '-3.14', '-c', 'import sys;print(sys.executable)'], text=True).strip() if os.name=='nt' else sys.executable
        if sys.version_info < (3,14) and os.name!='nt': raise RuntimeError('Python 3.14로 설치하세요.')
        subprocess.run([uv, 'venv', '--seed', '--python', python, str(MODULE_ROOT / '.venv')], check=True)
    command = [uv, 'pip', 'install', '--python', str(interpreter), '-r', str(ENGINE / 'requirements.txt')]
    if (ENGINE / 'requirements.lock.txt').is_file():
        command += ['-c', str(ENGINE / 'requirements.lock.txt')]
    subprocess.run(command, check=True)
    print('Desktop driver:', install_driver())


if __name__ == '__main__': main()
