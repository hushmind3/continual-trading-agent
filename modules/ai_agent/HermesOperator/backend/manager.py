"""API for the external Browser Use operator that drives Hermes through its UI."""
from fastapi import APIRouter, HTTPException
from . import runtime

MENU = {
    "id": "ai_agent/HermesOperator",
    "title": "Hermes 조종기",
    "operations": ["ai_agent/HermesOperator/"],
    "views": [],
    "manager": "ai_agent.HermesOperator.manager",
}
router = APIRouter(prefix="/api/ai_agent/HermesOperator")


def _call(fn, *args):
    try:
        return fn(*args)
    except (ValueError, RuntimeError, OSError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/status")
def status():
    return runtime.status()


@router.post("/install")
def install():
    return _call(runtime.install)


@router.post("/chat")
def chat(request: dict):
    return _call(runtime.chat, request.get("message", ""))


@router.post("/stop")
def stop():
    return _call(runtime.stop)


def busy_reason():
    return runtime.busy_reason()


def close():
    runtime.stop()
