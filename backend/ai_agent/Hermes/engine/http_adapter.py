"""Shared HTTP error translation for this submenu only."""
from fastapi import HTTPException
from ai_agent.Hermes.engine.bridge import bridge


def invoke(operation, payload=None):
    try:
        return bridge.call(operation, payload)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc
