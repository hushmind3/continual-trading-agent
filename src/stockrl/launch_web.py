"""One-click local web application launcher."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from .web.server import serve
from .paths import default_runtime_dir, DEFAULT_MODEL_DIR


def main() -> None:
    server_only = "--server-only" in sys.argv[1:]
    dashboard_only = "--dashboard-only" in sys.argv[1:]
    port = 8766
    runtime = default_runtime_dir()
    model_dir = Path(os.environ.get("STOCKRL_MODEL_DIR", str(DEFAULT_MODEL_DIR)))
    print(f"StockRL starting: http://127.0.0.1:{port}/", flush=True)
    serve(
        host="127.0.0.1", port=port,
        runtime=str(runtime),
        fee=0.001, auto_start=not dashboard_only,
        open_browser=not server_only,
        horizon="1m", config="configs/live_symbols_korea.json",
        model_dir=str(model_dir),
    )


if __name__ == "__main__":
    main()
