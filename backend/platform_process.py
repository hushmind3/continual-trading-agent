"""Identify and stop only processes owned by an original-app launcher."""
import json
import os
from pathlib import Path

import psutil


def identity(pid, source, entries):
    if type(pid) is not int or pid <= 0:
        return ''
    try:
        process = psutil.Process(pid)
        if Path(process.cwd()).resolve() != source.resolve():
            return ''
        command = process.cmdline()
        allowed = {os.path.normcase(str(path.resolve())) for path in entries}
        if not any(os.path.normcase(str(Path(arg).resolve())) in allowed for arg in command):
            return ''
        return json.dumps([process.create_time(), command], ensure_ascii=False)
    except (OSError, ValueError, psutil.Error):
        return ''


def stop_tree(pid, expected, source, entries):
    if not expected or identity(pid, source, entries) != expected:
        return
    parent = psutil.Process(pid)
    processes = list(reversed(parent.children(recursive=True))) + [parent]
    created = {p.pid: p.create_time() for p in processes}
    for process in processes:
        try:
            if process.create_time() == created[process.pid]:
                process.terminate()
        except psutil.NoSuchProcess:
            pass
    _, alive = psutil.wait_procs(processes, timeout=5)
    for process in alive:
        try:
            if process.create_time() == created[process.pid]:
                process.kill()
        except psutil.NoSuchProcess:
            pass
    _, alive = psutil.wait_procs(alive, timeout=3)
    if alive:
        raise RuntimeError('원본 프로세스 종료를 확인하지 못했습니다.')
