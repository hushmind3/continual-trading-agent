"""One production entrypoint: verify ownership, build React, serve API + UI on 8766."""
from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from urllib.request import urlopen

import psutil

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
RUNTIME = ROOT / "runtime/official"
PORT = 8766


def same_path(left, right):
    return os.path.normcase(str(Path(left).resolve())) == os.path.normcase(str(Path(right).resolve()))


def classify(process):
    """Only recognize listeners whose actual cwd and command point to this checkout."""
    command = process.cmdline()
    cwd = process.cwd()
    if same_path(cwd, ROOT) and "stockrl.web_api:app" in command and "uvicorn" in command:
        return "api"
    return None


def listeners(port):
    records = []
    for connection in psutil.net_connections(kind="tcp"):
        if connection.status != psutil.CONN_LISTEN or connection.laddr.port != port:
            continue
        if connection.pid is None:
            raise RuntimeError(f"{port} 포트의 프로세스 소유권을 확인할 수 없습니다.")
        process = psutil.Process(connection.pid)
        kind = classify(process)
        if kind is None:
            raise RuntimeError(f"{port} 포트는 이 프로젝트에서 확인된 서버가 아닙니다. PID {process.pid}; 종료하지 않았습니다.")
        records.append((process.pid, process.create_time(), kind))
    return list(dict.fromkeys(records))


def stop_verified(record):
    pid, created, kind = record
    try:
        process = psutil.Process(pid)
        if abs(process.create_time() - created) > 0.01 or classify(process) != kind:
            raise RuntimeError(f"PID {pid} 소유권이 변경되었습니다. 종료하지 않았습니다.")
        print(f"이 프로젝트의 이전 {kind} 서버만 종료: PID {pid}", flush=True)
        process.terminate()  # Do not terminate learner / Expert child processes.
        try:
            process.wait(timeout=5)
        except psutil.TimeoutExpired:
            if abs(process.create_time() - created) > 0.01 or classify(process) != kind:
                raise RuntimeError(f"PID {pid} 재확인 실패")
            process.kill()
            process.wait(timeout=3)
    except psutil.NoSuchProcess:
        pass


def ready():
    try:
        with urlopen(f"http://127.0.0.1:{PORT}/api/health", timeout=2) as response:
            result = json.load(response)
        return result.get("service") == "finrlx-react-sac" and same_path(result.get("project", ""), ROOT)
    except (OSError, ValueError):
        return False


@contextmanager
def startup_lock():
    import msvcrt
    RUNTIME.mkdir(parents=True, exist_ok=True)
    with (RUNTIME / "server-start.lock").open("a+b") as handle:
        if handle.tell() == 0:
            handle.write(b".")
            handle.flush()
        deadline = time.monotonic() + 60
        while True:
            try:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise RuntimeError("다른 통합 서버 실행 절차가 진행 중입니다.")
                time.sleep(0.1)
        try:
            yield
        finally:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


def main():
    with startup_lock():
        current = listeners(PORT)
        previous = listeners(8767)
        if current and current[0][2] == "api" and ready():
            for record in previous:
                stop_verified(record)
            print(f"기존 통합 서버 사용: http://127.0.0.1:{PORT}/ (PID {current[0][0]})", flush=True)
            return

        node = shutil.which("node")
        vite = FRONTEND / "node_modules/vite/bin/vite.js"
        typescript = FRONTEND / "node_modules/typescript/bin/tsc"
        if not node or not vite.is_file() or not typescript.is_file():
            raise RuntimeError("설치된 Node/Vite/TypeScript가 필요합니다. 이 실행 스크립트는 패키지를 설치하거나 업그레이드하지 않습니다.")
        for script, args in ((typescript, ["--noEmit"]), (vite, ["build"])):
            subprocess.run([node, str(script), *args], cwd=FRONTEND, check=True)
        if not (FRONTEND / "dist/index.html").is_file():
            raise RuntimeError("React 빌드 산출물이 없습니다.")

        for record in current:
            stop_verified(record)
        env = os.environ.copy()
        env.update(PYTHONPATH=str(ROOT / "src"), PYTHONUTF8="1")
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        with (RUNTIME / "server.stdout.log").open("ab") as output, (RUNTIME / "server.stderr.log").open("ab") as errors:
            child = subprocess.Popen([sys.executable, "-m", "uvicorn", "stockrl.web_api:app",
                                     "--host", "127.0.0.1", "--port", str(PORT)],
                                     cwd=ROOT, env=env, stdout=output, stderr=errors, creationflags=flags)
        for _ in range(100):
            if child.poll() is not None:
                raise RuntimeError("통합 서버 시작 실패. runtime/official/server.stderr.log를 확인하세요.")
            if ready():
                break
            time.sleep(0.1)
        else:
            raise RuntimeError("통합 서버 응답 대기 실패. 생성한 서버 로그를 확인하세요.")
        for record in previous:
            stop_verified(record)
        # Advisory record only. Process ownership is always checked independently.
        actual = listeners(PORT)
        (RUNTIME / "server.json").write_text(json.dumps({"project": str(ROOT), "port": PORT,
            "pid": actual[0][0], "process_created": actual[0][1], "service": "finrlx-react-sac"}, ensure_ascii=False, indent=2), encoding="utf8")
        print(f"통합 서버 실행: http://127.0.0.1:{PORT}/ (PID {actual[0][0]})", flush=True)
        print("5173은 npm run dev로 실행하는 개발 서버 전용입니다.", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, subprocess.SubprocessError, psutil.Error) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
