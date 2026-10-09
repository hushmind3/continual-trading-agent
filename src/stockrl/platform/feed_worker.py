"""Continuous broker flush and bounded polling share one durable market writer."""
import argparse
from concurrent.futures import Future
import queue
import threading
import time
from ..live_feed import LiveMarketCollector
from ..market_storage import AppendOnlyMarketCSV
from ..state_io import atomic_json,read_json
from .config import load_settings,CONFIG_PATH
from .worker_state import publish,stopped
from .worker_state import control


class MarketWriter:
    def __init__(self,path,capacity,settings):
        self.settings=settings
        self.path=path; self.queue=queue.Queue(capacity); self.stopping=threading.Event()
        self.thread=threading.Thread(target=self.run,name='market-writer',daemon=True); self.thread.start()

    def append(self,rows):
        if not rows:return 0
        future=Future(); self.queue.put((rows,future),timeout=10)
        return future.result(timeout=30)

    def run(self):
        index=AppendOnlyMarketCSV(self.path)
        try:
            while not self.stopping.is_set() or not self.queue.empty():
                try:rows,future=self.queue.get(timeout=.2)
                except queue.Empty:continue
                try:
                    if not control(self.settings).get('engine'):
                        atomic_json({'last_timestamp':max(str(r['date']) for r in rows)},self.path.parent/'agent'/'live_cursor.json')
                    future.set_result(index.append(rows))
                except Exception as exc:future.set_exception(exc)
        finally:index.close()

    def close(self):
        # The collector also calls close. The owning worker closes the writer after all producers stop.
        pass

    def shutdown(self):
        self.stopping.set(); self.thread.join(timeout=10)


def run(settings,source):
    from pathlib import Path
    source=Path(source);source_signature=source.stat().st_mtime_ns;reconfigured=False
    output=settings.state_dir/'live'/'market.csv'
    writer=MarketWriter(output,settings.resources.market_queue_batches,settings)
    shared={}; initialized=threading.Event()
    progress_lock=threading.Lock();progress={'new_rows_total':0,'poll_cycles_total':0,'last_new_bar_at':None,'source_as_of':None}
    def report(**values):
        with progress_lock:publish(settings,'feed',**progress,**values)
    def record_added(count,source_as_of=None,poll=False):
        with progress_lock:
            progress['new_rows_total']+=count;progress['poll_cycles_total']+=int(poll)
            if count:progress.update(last_new_bar_at=time.time(),source_as_of=source_as_of)

    class Collector(LiveMarketCollector):
        def run(self,*args,**kwargs):
            streams=None
            if self.broker_provider=='kiwoom':
                from .kiwoom_data import BrokerStreams
                streams=BrokerStreams(self);streams.start()
                self.broker_instruments=[]
            try:super().run(*args,**kwargs)
            finally:
                if streams:streams.close()

        def collect_once(self):
            report(status='polling',message='공개 시세와 과거 일봉 갱신 중')
            result=super().collect_once()
            record_added(result,max(self.latest_completed.values(),default=None),poll=True)
            report(status='running',rows_appended=result,message=None)
            return result

    def poll():
        try:
            collector=Collector(source,output,settings.data.poll_seconds,settings.data.timeout_seconds,
                                stop_file=settings.state_dir/'workers'/'feed.stop')
            from .integrated_asset import read_header
            model=settings.resolve(settings.expert_checkpoint)
            header=read_header(model) if model.is_file() else {}
            catalog={'experts':[{**e,'universe':e.get('stock_policy',{}).get('universe')} for k,e in header.get('expert_mapping',{}).items() if k in settings.enabled_experts]}
            native_symbols=set()
            for entry in catalog.get('experts',[]):
                native_symbols.update(entry.get('universe') or [])
            collector.daily_instruments.sort(key=lambda i:(0 if i['symbol']=='SPY' else 1 if i['symbol']=='MSFT' else 2 if i['symbol'] in native_symbols else 3))
            collector.index.close();collector.index=writer
            shared['collector']=collector; initialized.set()
            collector.run()
        except BaseException as exc:
            shared['error']=exc; initialized.set()
        finally:shared['finished']=True

    publish(settings,'feed',status='loading',message='시세 수집기 준비')
    polling=threading.Thread(target=poll,name='market-polling',daemon=True);polling.start()
    last_metrics=0
    try:
        initialized.wait(timeout=30)
        while not shared.get('finished'):
            collector=shared.get('collector')
            if source.stat().st_mtime_ns!=source_signature:
                reconfigured=True
                if collector:collector.stop.set();collector.broker_stop.set()
                break
            if stopped(settings,'feed'):
                if collector:collector.stop.set();collector.broker_stop.set()
                break
            if collector:
                rows=[]
                while len(rows)<512:
                    try:rows.append(collector.broker_rows.get_nowait())
                    except queue.Empty:break
                if rows:
                    added=writer.append(rows)
                    from datetime import datetime
                    for row in rows:
                        self_stamp=datetime.fromisoformat(row['date']).timestamp()
                        collector.latest_completed[row['symbol']]=max(self_stamp,collector.latest_completed.get(row['symbol'],0))
                    record_added(added,rows[-1]['date'])
                    report(status='running',broker_rows_appended=added,last_as_of=rows[-1]['date'])
                if time.monotonic()-last_metrics>1:
                    metrics=read_json(collector.metrics_path)
                    metrics.update(broker_connected=bool(collector.broker_status.get('connected')),
                        broker_last_message_utc=collector.broker_status.get('last_message_utc'),
                        broker_us_connected=bool(collector.broker_status.get('us_connected')),
                        broker_kr_connected=bool(collector.broker_status.get('kr_connected')),
                        fresh_symbols_5m=[s for s,t in list(collector.latest_completed.items()) if t>=time.time()-300],
                        broker_error=collector.broker_status.get('last_error',''))
                    atomic_json(metrics,collector.metrics_path);last_metrics=time.monotonic()
                    if getattr(collector,'latest_quotes',None):
                        atomic_json(dict(collector.latest_quotes),collector.output.with_name('quotes.json'))
            time.sleep(.2)
        polling.join(timeout=30)
        if shared.get('error'):raise shared['error']
    finally:
        writer.shutdown();publish(settings,'feed',status='stopped',reason='configuration_changed' if reconfigured else None)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--config',default=str(CONFIG_PATH));parser.add_argument('--source',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();settings=load_settings(args.config)
    try:run(settings,args.source)
    except Exception as exc:
        publish(settings,'feed',status='error',error=f'{type(exc).__name__}: {exc}')
        raise
