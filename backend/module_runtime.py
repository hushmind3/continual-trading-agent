"""Language-neutral module IPC. The host never imports a module's business dependencies."""
from __future__ import annotations
import atexit
import base64
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import threading
import uuid
from fastapi import APIRouter, HTTPException, Request, Response
from platform_native import native_runtime_path
from fastapi.responses import FileResponse


class ModuleRuntime:
    def __init__(self, folder):
        self.folder = Path(folder).resolve()
        self.metadata = json.loads((self.folder / 'module.json').read_text(encoding='utf8'))
        self.spec = self.metadata['runtime']
        self.process = None
        self.pending = {}
        self.mutable_pending = set()
        self.lock = threading.RLock()
        self.admission = threading.RLock()
        self.writes = threading.Lock()
        self.log = None
        self.restarting = False
        atexit.register(self.close)

    def command(self):
        command = self.spec['command']
        if not isinstance(command, list) or not command or not all(isinstance(value, str) for value in command):
            raise ValueError('모듈 실행 명령은 문자열 목록이어야 합니다.')
        executable = self.folder / native_runtime_path(command[0])
        if not executable.is_file():
            if any(separator in command[0] for separator in ('/', '\\')):
                raise RuntimeError(f'{self.metadata["id"]} 전용 실행 환경이 없습니다: {executable}')
            executable = shutil.which(command[0])
            if not executable: raise RuntimeError('모듈 실행기를 찾을 수 없습니다: ' + command[0])
        return [str(executable), *[value.replace('{module}', str(self.folder)) for value in command[1:]]]

    def _read(self, process):
        try:
            for line in process.stdout:
                try: message = json.loads(line)
                except ValueError: continue
                with self.lock: waiter = self.pending.get(message.get('id'))
                if waiter: waiter.put(message)
        except (UnicodeError,OSError) as exc:
            with self.lock:
                for waiter in self.pending.values():waiter.put({'error':'UTF-8 모듈 통신 오류: '+str(exc)})
        finally:
            with self.lock:
                if self.process is process:
                    for waiter in self.pending.values(): waiter.put({'error': '모듈 실행기가 종료됐습니다.'})

    def _start(self):
        if self.process and self.process.poll() is None: return self.process
        from platform_modules import ROOT
        state = (ROOT / self.spec['state']).resolve()
        if not state.is_relative_to((ROOT / 'runtime').resolve()): raise ValueError('모듈 기록 경로가 runtime 밖입니다.')
        state.mkdir(parents=True, exist_ok=True)
        if self.log: self.log.close()
        self.log = (state / 'module-worker.log').open('a', encoding='utf8')
        environment = {**os.environ, 'PLATFORM_ROOT': str(ROOT), 'MODULE_WORKER': self.metadata['id'],
                       'PYTHONUTF8': '1', 'PYTHONIOENCODING': 'utf-8'}
        environment.pop('PYTHONPATH', None)
        self.process = subprocess.Popen(self.command(), cwd=self.folder, env=environment,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.log, text=True, encoding='utf8',
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        threading.Thread(target=self._read, args=(self.process,), daemon=True).start()
        return self.process

    def call(self, operation, payload=None, timeout=90):
        key = uuid.uuid4().hex; waiter = queue.Queue()
        with self.admission:
            if self.restarting and operation != 'shutdown':raise RuntimeError('모듈 적용 준비 중입니다.')
            with self.lock:
                if operation=='shutdown' and (not self.process or self.process.poll() is not None):return True
                process = self._start(); self.pending[key] = waiter
                if operation=='request' and (payload or {}).get('method','GET')!='GET':self.mutable_pending.add(key)
        try:
            with self.writes:
                process.stdin.write(json.dumps({'id': key, 'operation': operation, 'payload': payload or {}}, ensure_ascii=False) + '\n')
                process.stdin.flush()
            try: response = waiter.get(timeout=timeout)
            except queue.Empty: raise RuntimeError('모듈 응답 시간이 초과됐습니다: ' + operation) from None
            if response.get('error'): raise RuntimeError(response['error'])
            return response.get('result')
        finally:
            with self.lock:
                self.pending.pop(key, None);self.mutable_pending.discard(key)

    def close(self):
        with self.lock: process = self.process
        if process and process.poll() is None:
            try: self.call('shutdown', timeout=10)
            except (OSError, RuntimeError): pass
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired: process.terminate(); process.wait(timeout=5)
        if self.log: self.log.close(); self.log = None

    def busy_reason(self):
        if self.restarting:return ''
        with self.lock:
            if self.mutable_pending:return self.metadata['id']+' 작업 요청 처리 중'
        if not self.process or self.process.poll() is not None: return ''
        try: return ' · '.join(self.call('hook', {'name': 'busy'}, timeout=5) or [])
        except (OSError, RuntimeError): return self.metadata['id'] + ' 실행 상태 확인 실패; 재시작 보류'

    def reserve_restart(self):
        # Reader responses use self.lock, so admission can span the IPC check
        # without blocking replies. New requests wait until reservation finishes.
        with self.admission:
            if self.restarting:return
            if reason:=self.busy_reason():raise RuntimeError(reason)
            self.call('hook',{'name':'reserve_restart'})
            self.restarting=True

    def cancel_restart(self):
        with self.admission:
            self.restarting=False
            if self.process and self.process.poll() is None:self.call('hook',{'name':'cancel_restart'})


def proxy_router(runtime, description):
    router = APIRouter()
    for route in description['routes']:
        def endpoint_for(spec):
            async def endpoint(request: Request):
                try:
                    result = await __import__('asyncio').to_thread(runtime.call, 'request', {
                        'path': request.url.path, 'query': request.url.query, 'method': request.method,
                        'body': base64.b64encode(await request.body()).decode(),
                        'headers': dict(request.headers)},timeout=None)
                except (OSError, RuntimeError) as exc: raise HTTPException(503, str(exc)) from exc
                if result.get('file'):
                    if not Path(result['file']).is_file():raise HTTPException(404,'결과 파일이 없습니다.')
                    return FileResponse(result['file'],status_code=result['status'],headers=result['headers'])
                return Response(base64.b64decode(result['body']), status_code=result['status'], headers=result['headers'])
            endpoint.__name__ = spec['name']; endpoint.__module__ = spec['module']
            return endpoint
        router.add_api_route(route['path'], endpoint_for(route), methods=route['methods'],
            description=route.get('description', ''), openapi_extra={'module_schemas': route['schemas']})
    return router
