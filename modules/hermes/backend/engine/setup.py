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

ENGINE = Path(__file__).resolve().parent
ROOT = ENGINE.parents[3]


def install_driver():
    lock = json.loads((ENGINE / 'upstream/pm/lock.json').read_text(encoding='utf-8'))
    artifact = lock['packages']['cua-driver']['artifacts']['win32-x64']
    target = ROOT / 'runtime/ai_agent/Hermes/tools/cua-driver'
    binary = target / 'cua-driver.exe'
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
    with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
        for member in bundle.infolist():
            if member.is_dir(): continue
            path = (target / member.filename).resolve()
            if not path.is_relative_to(target.resolve()):
                raise RuntimeError('드라이버 압축 경로가 설치 폴더 밖을 가리킵니다.')
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(bundle.read(member))
    matches = list(target.rglob('cua-driver*.exe'))
    if not matches: raise RuntimeError('cua-driver 실행파일을 찾을 수 없습니다.')
    if not binary.exists(): shutil.copyfile(matches[0], binary)
    receipt.write_text(json.dumps({**artifact, 'binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest()}, indent=2), encoding='utf-8')
    return binary


def main():
    if os.name != 'nt': raise RuntimeError('이 설치 진입점은 Windows용입니다.')
    interpreter = ROOT / '.venv/hermes/Scripts/python.exe'
    uv = shutil.which('uv')
    if not uv: raise RuntimeError('설치된 uv 실행기를 찾을 수 없습니다.')
    if not interpreter.exists():
        python = subprocess.check_output(['py', '-3.14', '-c', 'import sys;print(sys.executable)'], text=True).strip()
        subprocess.run([uv, 'venv', '--python', python, str(ROOT / '.venv/hermes')], check=True)
    command = [uv, 'pip', 'install', '--python', str(interpreter), '-r', str(ENGINE / 'requirements.txt')]
    if (ENGINE / 'requirements.lock.txt').is_file():
        command += ['-c', str(ENGINE / 'requirements.lock.txt')]
    subprocess.run(command, check=True)
    print('Desktop driver:', install_driver())


if __name__ == '__main__': main()
