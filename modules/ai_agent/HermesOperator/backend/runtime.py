"""Lifecycle for the visible Browser Use operator process."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import threading
import time

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "runtime/ai_agent/HermesOperator"
VENV = BASE / ".venv"
PROFILE = BASE / "browser-profile"
STATE_FILE = BASE / "state.json"
INSTALL_MARKER = BASE / "install-complete.json"
LOG_FILE = BASE / "operator.log"
WORKER = Path(__file__).with_name("worker.py")
REQUIREMENTS = Path(__file__).parents[1] / "requirements.txt"

LOCK = threading.RLock()
WRITE_LOCK = threading.Lock()
_process: subprocess.Popen | None = None
_install_thread: threading.Thread | None = None
_reader_thread: threading.Thread | None = None
_installing = False
_install_error = ""
_busy = False
_progress = ""
_history: list[dict] = []


def _python() -> Path:
    return VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _load_state():
    global _history
    try:
        payload = json.loads(STATE_FILE.read_text(encoding="utf8"))
        history = payload.get("history", [])
        if isinstance(history, list):
            _history = history[-100:]
    except (OSError, ValueError):
        pass


def _save_state():
    BASE.mkdir(parents=True, exist_ok=True)
    payload = {"history": _history[-100:]}
    temporary = STATE_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf8")
    os.replace(temporary, STATE_FILE)


_load_state()


def _installed() -> bool:
    python = _python()
    if not python.is_file() or not INSTALL_MARKER.is_file():
        return False
    try:
        result = subprocess.run(
            [str(python), "-c", "import browser_use, playwright"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=8,
        )
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _alive() -> bool:
    return bool(_process and _process.poll() is None)


def status():
    with LOCK:
        return {
            "installed": _installed(),
            "installing": _installing,
            "install_error": _install_error,
            "running": _alive(),
            "busy": _busy,
            "progress": _progress,
            "history": list(_history[-100:]),
            "log": str(LOG_FILE),
            "target": "http://127.0.0.1:8766/#ai_agent/HermesOriginal",
            "model": "FreeLLMAPI · auto",
        }


def _install_job():
    global _installing, _install_error
    BASE.mkdir(parents=True, exist_ok=True)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    uv = shutil.which("uv")
    if not uv:
        with LOCK:
            _install_error = "uv를 찾지 못했습니다."
            _installing = False
        return
    try:
        INSTALL_MARKER.unlink(missing_ok=True)
        with LOG_FILE.open("a", encoding="utf8") as log:
            commands = [
                [uv, "venv", "--python", "3.12", str(VENV)],
                [uv, "pip", "install", "--python", str(_python()), "-r", str(REQUIREMENTS)],
                [str(_python()), "-m", "playwright", "install", "chromium"],
            ]
            for command in commands:
                log.write("\n$ " + " ".join(command) + "\n")
                log.flush()
                subprocess.run(command, cwd=ROOT, stdout=log, stderr=log, check=True)
        INSTALL_MARKER.write_text(json.dumps({"completed_at": int(time.time())}), encoding="utf8")
        if not _installed():
            raise RuntimeError("Browser Use 설치 확인에 실패했습니다.")
    except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
        with LOCK:
            _install_error = str(exc)
    finally:
        with LOCK:
            _installing = False


def install():
    global _install_thread, _installing, _install_error
    with LOCK:
        if _installed():
            return status()
        if _installing:
            return status()
        _installing = True
        _install_error = ""
        _install_thread = threading.Thread(target=_install_job, name="hermes-operator-install", daemon=True)
        _install_thread.start()
        return status()


def _append(role: str, text: str):
    _history.append({"role": role, "text": text, "time": int(time.time())})
    del _history[:-100]
    _save_state()


def _reader(process: subprocess.Popen):
    global _busy, _progress
    try:
        for raw in process.stdout:
            try:
                event = json.loads(raw)
            except (ValueError, TypeError):
                continue
            kind = event.get("event")
            with LOCK:
                if kind == "ready":
                    _progress = "Chromium 준비됨"
                elif kind == "progress":
                    _progress = str(event.get("text") or "조작 중")
                elif kind == "result":
                    _busy = False
                    _progress = ""
                    _append("assistant", str(event.get("text") or "완료"))
                elif kind == "error":
                    _busy = False
                    _progress = ""
                    _append("assistant", "오류: " + str(event.get("text") or "알 수 없는 오류"))
    finally:
        with LOCK:
            if _process is process:
                _busy = False
                _progress = ""


def _start_worker():
    global _process, _reader_thread
    if _alive():
        return
    if not _installed():
        raise RuntimeError("먼저 Browser Use를 설치하세요.")
    BASE.mkdir(parents=True, exist_ok=True)
    PROFILE.mkdir(parents=True, exist_ok=True)
    log = LOG_FILE.open("a", encoding="utf8")
    env = {
        **os.environ,
        "PLATFORM_ROOT": str(ROOT),
        "HERMES_OPERATOR_PROFILE": str(PROFILE),
        "HERMES_OPERATOR_TARGET": "http://127.0.0.1:8766/#ai_agent/HermesOriginal",
        "HERMES_OPERATOR_MODEL": "auto",
        "ANONYMIZED_TELEMETRY": "false",
        "BROWSER_USE_LOGGING_LEVEL": "warning",
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
    }
    _process = subprocess.Popen(
        [str(_python()), str(WORKER)],
        cwd=ROOT,
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=log,
        text=True,
        encoding="utf8",
        bufsize=1,
        start_new_session=(os.name != "nt"),
        creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0,
    )
    _reader_thread = threading.Thread(target=_reader, args=(_process,), name="hermes-operator-reader", daemon=True)
    _reader_thread.start()


def chat(message: str):
    global _busy, _progress
    message = str(message or "").strip()
    if not message:
        raise ValueError("지시를 입력하세요.")
    if len(message) > 12000:
        raise ValueError("지시는 12,000자 이하로 입력하세요.")
    with LOCK:
        if _installing:
            raise RuntimeError("Browser Use 설치 중입니다.")
        if _busy:
            raise RuntimeError("이전 조작이 아직 진행 중입니다.")
        _start_worker()
        if not _process or not _process.stdin:
            raise RuntimeError("Operator 실행기를 시작하지 못했습니다.")
        _append("user", message)
        _busy = True
        _progress = "지시 전달 중"
        payload = json.dumps({"task": message}, ensure_ascii=False)
        try:
            with WRITE_LOCK:
                _process.stdin.write(payload + "\n")
                _process.stdin.flush()
        except OSError as exc:
            _busy = False
            _progress = ""
            raise RuntimeError("Operator에 지시를 전달하지 못했습니다.") from exc
        return status()


def stop():
    global _process, _busy, _progress
    with LOCK:
        process = _process
        _process = None
        _busy = False
        _progress = ""
    if process and process.poll() is None:
        try:
            if os.name != "nt":
                os.killpg(process.pid, signal.SIGTERM)
            else:
                process.terminate()
            process.wait(timeout=8)
        except (OSError, subprocess.TimeoutExpired):
            try:
                process.kill()
            except OSError:
                pass
    return status()


def busy_reason():
    with LOCK:
        if _installing:
            return "Hermes Operator 설치 중"
        if _busy:
            return "Hermes Operator가 브라우저를 조작 중"
        return ""
