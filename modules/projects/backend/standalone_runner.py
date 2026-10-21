"""Self-contained source distribution entry point; no original checkout lookups."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from urllib.request import urlopen
import zipfile

ROOT = Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'backend'))
from platform_native import npm_command


def environment():
    result = dict(os.environ)
    for key in ('PYTHONPATH', 'PLATFORM_MODULES_DIR', 'HERMES_HOME', 'HERMES_RUNTIME_DIR'):
        result.pop(key, None)
    result.update(PLATFORM_ROOT=str(ROOT), PYTHONUTF8='1', PYTHONIOENCODING='utf-8')
    return result


def execute(command):
    subprocess.run([str(value) for value in command], cwd=ROOT, env=environment(), check=True)


def python():
    return ROOT / '.venv/platform' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def install_runner(metadata):
    spec=metadata.get('llama_cpp')
    if sys.platform=='darwin':
        runner=shutil.which('llama-server')
        if not runner:raise ValueError('Metal 실행기가 필요합니다: brew install llama.cpp')
        target=ROOT/'runtime/shared/engines/llama.cpp/llama-server'
        target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists():
            pending=target.with_name(target.name+'.tmp')
            pending.symlink_to(runner);pending.replace(target)
        return
    if not spec:return
    if not spec['source'].startswith('https://github.com/ggml-org/llama.cpp/releases/download/'):
        raise ValueError('llama.cpp 공식 배포 주소가 아닙니다.')
    target=ROOT/'runtime/shared/engines/llama.cpp'
    binary=target/'llama-server.exe';receipt=target/'engine.json'
    if binary.is_file() and receipt.is_file():
        saved=json.loads(receipt.read_text(encoding='utf8'))
        if saved.get('sha256')==spec['sha256'] and saved.get('binary_sha256')==hashlib.sha256(binary.read_bytes()).hexdigest():return
    with urlopen(spec['source'],timeout=120) as response:data=response.read(256*1024*1024+1)
    if len(data)>256*1024*1024 or hashlib.sha256(data).hexdigest()!=spec['sha256']:
        raise ValueError('llama.cpp 배포 파일 크기/SHA-256 검사 실패')
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        if sum(item.file_size for item in archive.infolist())>512*1024*1024:raise ValueError('llama.cpp 압축 해제 한도 초과')
        for item in archive.infolist():
            path=(target/item.filename).resolve()
            if not path.is_relative_to(target.resolve()):raise ValueError('llama.cpp 압축 경로 오류')
        target.mkdir(parents=True,exist_ok=True)
        archive.extractall(target)
    if not binary.is_file():raise ValueError('llama.cpp 서버 실행파일이 없습니다.')
    receipt.write_text(json.dumps({**spec,'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest()}),encoding='utf8')


def verify(check_hash=False):
    metadata = json.loads((ROOT / 'standalone-module.json').read_text(encoding='utf8'))
    changed=[]
    for name, digest in metadata['files'].items():
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file():
            raise ValueError('배포 소스 무결성 확인 실패: ' + name)
        if check_hash and hashlib.sha256(path.read_bytes()).hexdigest() != digest:changed.append(name)
    actual = sorted(path.parent.name for path in (ROOT / 'modules').glob('*/module.json'))
    if actual != [metadata['module']]: raise ValueError('선택한 모듈 이외의 프로그램이 포함됐습니다.')
    return {**metadata,'changed_files':changed}


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'): stream.reconfigure(encoding='utf8')
    parser = argparse.ArgumentParser(description='원래 플랫폼 없이 단독 모듈을 설치·실행합니다.')
    parser.add_argument('command', choices=['setup', 'check', 'run'], nargs='?', default='run')
    parser.add_argument('--port', type=int, default=8080)
    args = parser.parse_args()
    metadata = verify(check_hash=args.command=='check')
    if metadata['changed_files']:print('내보낸 뒤 수정된 소스: '+', '.join(metadata['changed_files']),flush=True)
    if args.command == 'setup':
        if os.name!='nt' and sys.platform!='darwin':raise ValueError('현재 독립 설치는 Windows와 macOS를 지원합니다.')
        if sys.platform=='darwin' and metadata['module']=='finance':raise ValueError('금융 CUDA·키움 전용 환경은 macOS 설치 대상이 아닙니다. 원본 데이터·모델은 보존하세요.')
        execute([sys.executable, 'development/scripts/install_windows.py'])
        execute([*npm_command(), 'run', 'build', '--workspace', 'frontend'])
        if metadata['module']=='hermes':install_runner(metadata)
        return
    if not python().is_file(): raise ValueError('먼저 python run.py setup으로 전용 환경을 설치하세요.')
    if not (ROOT / 'frontend/dist/index.html').is_file(): raise ValueError('화면 빌드가 없습니다. setup을 실행하세요.')
    if args.command == 'check':
        code = """import sys,json
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'backend'))
from platform_modules import registrations,lifecycle
import os
try:
 entries=registrations()
 errors={item['id']:entry.load_error for item,entry in entries if getattr(entry,'load_error',None)}
 if errors:raise RuntimeError(json.dumps(errors,ensure_ascii=False))
 forbidden=os.environ.get('STANDALONE_FORBIDDEN_ROOT')
 if forbidden:
  forbidden=Path(forbidden).resolve();root=Path.cwd().resolve()
  outside=[str(Path(module.__file__).resolve()) for module in list(sys.modules.values())
   if getattr(module,'__file__',None) and Path(module.__file__).resolve().is_relative_to(forbidden)
   and not Path(module.__file__).resolve().is_relative_to(root)]
  if outside:raise RuntimeError('Original checkout imports: '+repr(outside))
 print(json.dumps({'modules':[item['id'] for item,entry in entries],'root':str(Path.cwd())},ensure_ascii=False))
finally:lifecycle('close')
"""
        execute([python(), '-I', '-X', 'utf8', '-B', '-c', code])
    else:
        execute([python(), '-I', '-X', 'utf8', '-B', '-m', 'uvicorn', 'web_api:app',
                 '--app-dir', ROOT / 'backend', '--host', '127.0.0.1', '--port', args.port])


if __name__ == '__main__':
    try: main()
    except (ValueError, OSError, subprocess.CalledProcessError) as exc: sys.exit(str(exc))
