from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


from .paths import default_runtime_dir


def main() -> None:
    p=argparse.ArgumentParser(prog="stockrl",description="TradingMoE market feed and paper runtime")
    sub=p.add_subparsers(dest="command",required=True)
    web=sub.add_parser("web",help="serve FinRL-X operations and the built React UI")
    web.add_argument("--host",default="127.0.0.1")
    web.add_argument("--port",type=int,default=8766)
    web.add_argument("--config",default="configs/operations.json")
    web.add_argument("--no-browser",action="store_true")
    def run_web(args):
        from .platform.api import serve
        serve(host=args.host,port=args.port,config=args.config,open_browser=not args.no_browser)
    web.set_defaults(func=run_web)
    args=p.parse_args(); args.func(args)


if __name__=="__main__": main()
