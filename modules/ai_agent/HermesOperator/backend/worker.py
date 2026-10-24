"""Visible Browser Use agent that operates the local Hermes UI."""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import re
import sys

from browser_use import Agent, Browser, ChatOpenAI

ROOT = Path(os.environ.get("PLATFORM_ROOT") or Path(__file__).resolve().parents[4]).resolve()
HERMES_HOME = ROOT / "runtime/ai_agent/HermesOriginal/home"
PROFILE = Path(os.environ.get("HERMES_OPERATOR_PROFILE") or ROOT / "runtime/ai_agent/HermesOperator/browser-profile")
TARGET = os.environ.get("HERMES_OPERATOR_TARGET", "http://127.0.0.1:8766/#ai_agent/HermesOriginal")
MODEL = os.environ.get("HERMES_OPERATOR_MODEL", "auto")


def emit(event: str, **payload):
    print(json.dumps({"event": event, **payload}, ensure_ascii=False), flush=True)


def _env_value(path: Path, name: str) -> str:
    try:
        text = path.read_text(encoding="utf8")
    except OSError:
        return ""
    match = re.search(rf"(?m)^\s*{re.escape(name)}\s*=\s*(.+?)\s*$", text)
    if not match:
        return ""
    value = match.group(1).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1]
    return value


def _provider_url(config: Path) -> str:
    try:
        text = config.read_text(encoding="utf8")
    except OSError:
        return ""
    lowered = text.lower()
    anchors = [lowered.find("freellmapi-shared"), lowered.find("freellmapi_api_key"), lowered.find("freellmapi")]
    for index in [value for value in anchors if value >= 0]:
        block = text[max(0, index - 1800): index + 4500]
        match = re.search(r"(?m)^\s*base_url\s*:\s*['\"]?([^'\"\s#]+)", block)
        if match:
            return match.group(1).rstrip("/")
    for match in re.finditer(r"(?m)^\s*base_url\s*:\s*['\"]?([^'\"\s#]+)", text):
        url = match.group(1).rstrip("/")
        if "/api/projects/freellmapi/" in url.lower():
            return url
    return ""


def discover_freellmapi() -> tuple[str, str]:
    if not HERMES_HOME.is_dir():
        raise RuntimeError("Hermes Original home을 찾지 못했습니다.")
    env_files = sorted(HERMES_HOME.rglob(".env"), key=lambda p: ("/lead/" not in p.as_posix(), len(p.parts)))
    api_key = ""
    preferred_parent = None
    for path in env_files:
        value = _env_value(path, "FREELLMAPI_API_KEY")
        if value:
            api_key = value
            preferred_parent = path.parent
            break
    if not api_key:
        raise RuntimeError("Hermes 설정에서 FREELLMAPI_API_KEY를 찾지 못했습니다.")

    configs = list(HERMES_HOME.rglob("config.yaml")) + list(HERMES_HOME.rglob("config.yml"))
    configs.sort(key=lambda p: (preferred_parent is None or p.parent != preferred_parent, "/lead/" not in p.as_posix(), len(p.parts)))
    base_url = ""
    for path in configs:
        base_url = _provider_url(path)
        if base_url:
            break
    if not base_url:
        raise RuntimeError("Hermes 설정에서 FreeLLMAPI base_url을 찾지 못했습니다.")
    if not base_url.endswith("/v1"):
        base_url += "/v1"
    return base_url, api_key


SYSTEM = f"""
You are the user's external UI operator for Hermes Original.
Operate the visible browser UI yourself. The user should not have to hunt through menus.
Start from {TARGET}. Use Hermes chat, settings, Kanban, plugins, Agora, model/profile pages, and other Hermes UI as needed.
Prefer normal UI interaction over editing source files or configuration files.
Do not merely explain where the user should click: perform the requested UI actions.
Keep the browser window open when the task ends.
Before claiming a change succeeded, inspect the resulting UI state and verify it.
If the requested action is destructive, publishes externally, spends money, or changes credentials, stop before the irreversible step and report exactly what approval is needed.
Answer in concise Korean with what you actually changed or what blocked the operation.
"""


async def main():
    base_url, api_key = discover_freellmapi()
    llm = ChatOpenAI(model=MODEL, base_url=base_url, api_key=api_key)
    browser = Browser(
        headless=False,
        keep_alive=True,
        user_data_dir=str(PROFILE),
        window_size={"width": 1440, "height": 1000},
    )
    await browser.start()
    emit("ready")

    try:
        while True:
            raw = await asyncio.to_thread(sys.stdin.readline)
            if not raw:
                break
            try:
                request = json.loads(raw)
                task = str(request.get("task") or "").strip()
            except (ValueError, TypeError):
                continue
            if not task:
                continue
            emit("progress", text="Hermes 화면 확인 중")
            try:
                agent = Agent(
                    task=f"Open {TARGET} if it is not already open.\n\nUser request:\n{task}",
                    llm=llm,
                    browser=browser,
                    use_vision=False,
                    use_judge=False,
                    max_actions_per_step=5,
                    extend_system_message=SYSTEM,
                    directly_open_url=True,
                    enable_signal_handler=False,
                )

                async def on_step_end(current):
                    try:
                        state = await current.browser_session.get_browser_state_summary()
                        emit("progress", text=f"조작 중 · {state.url}")
                    except Exception:
                        emit("progress", text="조작 중")

                history = await agent.run(max_steps=60, on_step_end=on_step_end)
                result = history.final_result() or "작업은 끝났지만 최종 보고가 비어 있습니다."
                emit("result", text=str(result))
            except Exception as exc:
                emit("error", text=f"{type(exc).__name__}: {exc}")
    finally:
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
