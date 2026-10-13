"""Run the official Kiwoom SDK with its compatible dependencies, without another HTTP server."""
import asyncio
import importlib.metadata
import json
import os
import sys
import threading
from pathlib import Path
from types import SimpleNamespace

os.environ['STOCKRL_KIWOOM_WORKER']='1'
from .kiwoom_data import _SDKBrokerStreams

_output_lock=threading.Lock()

def emit(kind,value):
    with _output_lock:
        print(json.dumps({'protocol':'stockrl-kiwoom-v1','kind':kind,'value':value},ensure_ascii=False),flush=True)

class EventRows:
    def put(self,value):emit('bar',value)

class EventStatus(dict):
    def update(self,*args,**kwargs):
        super().update(*args,**kwargs);emit('status',dict(self))

class EventQuotes(dict):
    def __setitem__(self,key,value):
        super().__setitem__(key,value);emit('quote',{'symbol':key,'quote':value})

class EventSymbols(set):
    def update(self,*values):
        super().update(*values);emit('symbols',sorted(self))

def main():
    if '--check' in sys.argv:
        import kiwoom
        print(json.dumps({'sdk':importlib.metadata.version('kwcli'),'websockets':importlib.metadata.version('websockets'),'imported':bool(kiwoom.KiwoomAuth)}))
        return
    request=json.loads(sys.stdin.readline())
    if request.get('operation')=='daily_history':
        from datetime import datetime,timedelta
        import time
        from .kiwoom_data import request_daily_history
        from zoneinfo import ZoneInfo
        from stockrl.management.connection_settings.provider_credentials import get_credentials,read_settings
        from kiwoom import KiwoomAuth,KiwoomClient
        from kiwoom.core.secrets import StaticSecretProvider
        from kiwoom.core.token_store import MemoryTokenStore
        runtime=Path(request['runtime_dir']);cfg=read_settings(runtime);keys=get_credentials(runtime)
        client=KiwoomClient(KiwoomAuth('real' if cfg['environment']=='real' else 'demo',
            StaticSecretProvider(keys['app_key'],keys['secret']),MemoryTokenStore(),timeout_seconds=10),timeout_seconds=15)
        base=(datetime.now(ZoneInfo('Asia/Seoul'))-timedelta(days=1)).strftime('%Y%m%d')
        results=[];next_request=0
        try:
            for symbol in request['symbols']:
                try:
                    time.sleep(max(0,next_request-time.monotonic()))
                    next_request=time.monotonic()+.3
                    response=request_daily_history(client,symbol,base)
                    results.append({'symbol':symbol,'base_date':base,'response':response})
                except Exception as error:
                    detail=str(error)
                    for key in ('app_key','secret'):detail=detail.replace(keys[key],'[redacted]') if keys[key] else detail
                    results.append({'symbol':symbol,'error':detail})
        finally:client.session.close()
        emit('history',results)
        return
    collector=SimpleNamespace(runtime_dir=Path(request['runtime_dir']),instruments=request['instruments'],
        broker_instruments=request['broker_instruments'],broker_symbols=EventSymbols(request['broker_symbols']),
        broker_stop=threading.Event(),broker_rows=EventRows(),broker_status=EventStatus(),latest_quotes=EventQuotes())
    def commands():
        for line in sys.stdin:
            if json.loads(line).get('stop'):break
        collector.broker_stop.set()
    threading.Thread(target=commands,name='kiwoom-stop',daemon=True).start()
    try:
        streams=_SDKBrokerStreams(collector)
        collector.latest_quotes=EventQuotes()
        asyncio.run(streams.run_async())
    except Exception as exc:
        emit('status',{'connected':False,'last_error':f'{type(exc).__name__}: {exc}'})
        raise

if __name__=='__main__':main()
