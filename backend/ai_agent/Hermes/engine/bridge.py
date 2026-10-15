"""Bounded JSON-line IPC; upstream module names never enter the finance process."""
from __future__ import annotations

import atexit
import json
import os
from pathlib import Path
import queue
import subprocess
import threading
import uuid

ROOT = Path(__file__).resolve().parents[4]
STATE = ROOT / 'runtime/ai_agent/Hermes'
PYTHON = ROOT / '.venv/hermes/Scripts/python.exe'
WORKER = Path(__file__).with_name('worker.py')


class WorkerBridge:
    def __init__(self, state_dir=None):
        self.state_dir = Path(state_dir).resolve() if state_dir else STATE
        self.process = None
        self.pending = {}
        self.lock = threading.RLock()
        self.write_lock = threading.Lock()
        self.log = None

    def _read(self, process):
        try:
            for line in process.stdout:
                try:
                    message = json.loads(line)
                except ValueError:
                    continue
                with self.lock:
                    waiter = self.pending.get(message.get('id'))
                if waiter:
                    waiter.put(message)
        finally:
            with self.lock:
                if self.process is process:
                    for waiter in self.pending.values():
                        waiter.put({'error': 'Hermes 작업 프로세스가 종료됐습니다. 로그: runtime/ai_agent/Hermes/worker.log'})

    def _start(self):
        if self.process and self.process.poll() is None:
            return self.process
        if not PYTHON.is_file():
            raise RuntimeError('Hermes Python 실행 환경이 없습니다. Hermes README의 설치 명령을 실행하세요.')
        self.state_dir.mkdir(parents=True, exist_ok=True)
        if self.log:
            self.log.close()
        self.log = (self.state_dir / 'worker.log').open('a', encoding='utf-8')
        env = {**os.environ, 'PYTHONUTF8': '1', 'PYTHONIOENCODING': 'utf-8',
               'HERMES_HOME': str(self.state_dir), 'HERMES_RUNTIME_DIR': str(self.state_dir / 'runtime')}
        env.pop('PYTHONPATH', None)
        self.process = subprocess.Popen(
            [str(PYTHON), '-I', '-X', 'utf8', '-B', str(WORKER)], cwd=ROOT, env=env,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.log,
            encoding='utf-8', errors='replace', bufsize=1,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
        )
        self.reader = threading.Thread(target=self._read, args=(self.process,), daemon=True)
        self.reader.start()
        return self.process

    def call(self, operation, payload=None, timeout=45):
        request_id = uuid.uuid4().hex
        waiter = queue.Queue()
        with self.lock:
            process = self._start()
            self.pending[request_id] = waiter
        try:
            with self.write_lock:
                process.stdin.write(json.dumps({'id': request_id, 'operation': operation, 'payload': payload or {}}, ensure_ascii=False) + '\n')
                process.stdin.flush()
            try:
                result = waiter.get(timeout=timeout)
            except queue.Empty as exc:
                raise RuntimeError('Hermes 응답 대기 시간이 초과됐습니다. 실행 상태와 로그를 확인하세요.') from exc
            if result.get('error'):
                raise RuntimeError(result['error'])
            return result.get('result')
        except (OSError, BrokenPipeError) as exc:
            raise RuntimeError('Hermes 실행 프로세스와 연결이 끊겼습니다.') from exc
        finally:
            with self.lock:
                self.pending.pop(request_id, None)

    def close(self):
        with self.lock:
            process = self.process
        if process and process.poll() is None:
            try:
                self.call('shutdown', timeout=5)
                process.wait(timeout=5)
            except Exception:
                # Descendants belong to this worker (local model/MCP/terminal), never another application.
                import psutil
                try:
                    children = psutil.Process(process.pid).children(recursive=True)
                except psutil.NoSuchProcess:
                    children = []
                for child in reversed(children):
                    try: child.terminate()
                    except psutil.NoSuchProcess: pass
                process.terminate()
        if process:
            if getattr(self, 'reader', None): self.reader.join(timeout=2)
            for stream in (process.stdin, process.stdout):
                if stream:
                    try: stream.close()
                    except OSError: pass
            self.process = None
        if self.log:
            self.log.close()
            self.log = None


bridge = WorkerBridge()
atexit.register(bridge.close)
