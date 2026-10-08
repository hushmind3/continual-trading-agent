"""One-click local web application launcher."""
from __future__ import annotations

import sys
from .platform.api import serve


def main() -> None:
    server_only = "--server-only" in sys.argv[1:]
    port = 8766
    print(f"StockRL starting: http://127.0.0.1:{port}/", flush=True)
    serve(host="127.0.0.1",port=port,open_browser=not server_only)


if __name__ == "__main__":
    main()
