from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


from .paths import default_runtime_dir


def main() -> None:
    p=argparse.ArgumentParser(prog="stockrl",description="TradingMoE market feed and paper runtime")
    sub=p.add_subparsers(dest="command",required=True)
    lf=sub.add_parser("live-feed",help="poll public minute market data and append de-duplicated UTC bars for the paper runtime")
    lf.add_argument("--config",default="configs/live_symbols.json"); lf.add_argument("--output",default=str(default_runtime_dir()/"live"/"market.csv"))
    lf.add_argument("--poll-seconds",type=float,default=15.0); lf.add_argument("--timeout",type=float,default=15.0)
    lf.add_argument("--once",action="store_true",help="poll every configured instrument once and exit")
    lf.add_argument("--stop-file",default=None,help="stop cleanly when this file is created")
    lf.add_argument("--provider-plugin",action="append",default=[],help="import a module that registers a MarketDataProviderAdapter; may be repeated")
    lf.add_argument("--max-cycles",type=int,default=None,help=argparse.SUPPRESS)
    def run_live_feed(args):
        import logging
        import importlib,os
        from .live_feed import LiveMarketCollector
        plugins=list(args.provider_plugin)+[x.strip() for x in os.environ.get("STOCKRL_MARKET_PROVIDER_PLUGINS","").split(",") if x.strip()]
        for plugin in plugins: importlib.import_module(plugin)
        logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)s %(message)s")
        LiveMarketCollector(args.config,args.output,args.poll_seconds,args.timeout,stop_file=args.stop_file).run(args.once,args.max_cycles)
    lf.set_defaults(func=run_live_feed)
    mf=sub.add_parser("mock-feed",help="stream real historical CSV bars at a controllable pace into the live paper feed")
    mf.add_argument("--source",default="data/global_market_daily.csv"); mf.add_argument("--output",default=str(default_runtime_dir()/"desktop"/"mock_market.csv"))
    mf.add_argument("--bars",type=int,default=24); mf.add_argument("--interval-seconds",type=float,default=.5)
    mf.add_argument("--start-offset",type=int,default=0); mf.add_argument("--max-cycles",type=int,default=None)
    mf.add_argument("--stop-file",default=None)
    def run_mock_feed(args):
        import logging
        from .mock_feed import replay_market_csv
        logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)s %(message)s")
        result=replay_market_csv(args.source,args.output,args.bars,args.interval_seconds,args.start_offset,args.max_cycles,args.stop_file)
        print(json.dumps(result,indent=2))
    mf.set_defaults(func=run_mock_feed)
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
