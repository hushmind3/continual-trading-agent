"""Registered instruments: stored prices and official Kiwoom historical inputs."""
from ... import ROOT
from .storage import PriceStore
import threading

_collection_lock=threading.Lock()


def kiwoom_collection_state():
    from stockrl.state_io import read_json
    state=read_json(ROOT/'runtime/operations/market_history/collection.json') or {'status':'idle','rows':0,'symbols':[],'errors':[]}
    if state.get('status')=='running' and not _collection_lock.locked():
        return {**state,'status':'interrupted','error':'이전 수집 작업의 완료 기록이 없습니다. 다시 수집하세요.'}
    return state


def start_kiwoom_collection():
    from stockrl.management.connection_settings.provider_credentials import public_status
    from stockrl.state_io import atomic_json
    status=public_status(ROOT/'runtime/operations')
    if status['provider']!='kiwoom' or not status['saved']:raise ValueError('키움 App Key·Secret 연결을 먼저 설정하세요.')
    if not _collection_lock.acquire(blocking=False):return kiwoom_collection_state()
    path=ROOT/'runtime/operations/market_history/collection.json'
    try:
        atomic_json({'status':'running','source':'kiwoom','timeframe':'1d','rows':0,'symbols':[],'errors':[]},path)
        def run():
            try:collect_kiwoom_prices()
            except Exception as error:atomic_json({'status':'failed','source':'kiwoom','error':str(error),'rows':0,'symbols':[],'errors':[]},path)
            finally:_collection_lock.release()
        threading.Thread(target=run,name='kiwoom-historical-prices',daemon=True).start()
    except BaseException:
        _collection_lock.release();raise
    return kiwoom_collection_state()

def price_store(directory=None):
    return PriceStore(directory)


def normalize_kiwoom_daily(result):
    """Validate adjusted, completed daily bars before committing a symbol."""
    import math
    import pandas as pd
    if result.get('error'):raise ValueError(result['error'])
    payload=result['response']
    if str(payload.get('return_code'))!='0':raise ValueError('키움 가격 조회 실패: '+str(payload.get('return_msg','응답 확인 필요')))
    if payload.get('stk_cd') and payload['stk_cd'].split('_')[0]!=result['symbol'].split('.')[0]:raise ValueError('키움 응답 종목과 요청 종목이 다릅니다.')
    rows=payload.get('stk_dt_pole_chart_qry')
    if not isinstance(rows,list) or not rows:raise ValueError('키움에서 완료된 일봉을 받지 못했습니다.')
    records=[];base=pd.Timestamp(result['base_date'])
    for row in rows:
        date=pd.to_datetime(row.get('dt'),format='%Y%m%d',errors='coerce')
        if pd.isna(date) or date>base:raise ValueError('키움 일봉의 거래일이 유효하지 않습니다.')
        try:
            values={target:float(str(row[source]).replace(',','')) for target,source in
                    [('open','open_pric'),('high','high_pric'),('low','low_pric'),('close','cur_prc'),('volume','trde_qty')]}
            values={key:abs(value) if key!='volume' else value for key,value in values.items()}
        except (KeyError,TypeError,ValueError) as error:raise ValueError('키움 일봉의 가격·거래량이 유효하지 않습니다.') from error
        if not all(math.isfinite(value) for value in values.values()) or min(values[k] for k in ('open','high','low','close'))<=0 or values['volume']<0:
            raise ValueError('키움 일봉의 가격은 유한한 양수여야 합니다.')
        if not values['low']<=min(values['open'],values['close'])<=max(values['open'],values['close'])<=values['high']:
            raise ValueError('키움 일봉의 고가·저가 범위가 일치하지 않습니다.')
        records.append({'ticker':result['symbol'],'date':date.strftime('%Y-%m-%d'),'adj_close':values['close'],**values})
    frame=pd.DataFrame(records).drop_duplicates()
    if frame.duplicated(['ticker','date']).any():raise ValueError('키움 일봉의 같은 날짜에 상충하는 가격이 있습니다.')
    return frame.sort_values('date').reset_index(drop=True)


def collect_kiwoom_prices(symbols=None):
    """Use the existing isolated official SDK, never broker order endpoints."""
    import json
    import os
    import subprocess
    from stockrl.management.connection_settings.provider_credentials import read_settings
    from stockrl.state_io import atomic_json
    cfg=read_settings(ROOT/'runtime/operations')
    if cfg.get('provider')!='kiwoom':raise ValueError('키움 시세 연결을 먼저 설정하세요.')
    instruments=json.loads((ROOT/'configs/instruments.json').read_text(encoding='utf-8'))['instruments']
    allowed={i['symbol'] for i in instruments if i.get('market') in ('KRX','KOSDAQ') and i.get('asset_class') in ('equity','etf')}
    names=sorted(allowed) if symbols is None else list(dict.fromkeys(symbols))
    if not names or any(name not in allowed for name in names):raise ValueError('등록된 국내 주식·ETF의 종목 코드를 선택하세요.')
    python=ROOT/'.venv/kiwoom/Scripts/python.exe'
    if not python.is_file():raise RuntimeError('기존 키움 SDK 실행 환경을 확인하세요.')
    env={**os.environ,'PYTHONPATH':str(ROOT/'backend'),'PYTHONUTF8':'1'}
    request={'operation':'daily_history','runtime_dir':str(ROOT/'runtime/operations'),'symbols':names}
    process=subprocess.run([str(python),'-B','-m','stockrl.platform.kiwoom_worker'],input=json.dumps(request)+'\n',
        text=True,encoding='utf-8',capture_output=True,env=env,cwd=ROOT,timeout=max(30,20*len(names)),
        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if process.returncode:raise RuntimeError('키움 SDK 가격 조회 작업이 실패했습니다. 인증 상태를 확인하세요.')
    events=[json.loads(line) for line in process.stdout.splitlines() if line.startswith('{')]
    results=next((event['value'] for event in events if event.get('kind')=='history'),None)
    if results is None:raise RuntimeError('키움 SDK의 가격 조회 결과가 없습니다.')
    summary={'source':'kiwoom','api_id':'ka10081','timeframe':'1d','adjusted':True,'symbols':[],'errors':[],'rows':0}
    store=price_store()
    for result in results:
        try:
            frame=normalize_kiwoom_daily(result);frame.attrs.update(source='kiwoom',timeframe='1d');saved=store.save_price_data(frame)
            if saved!=len(frame):raise ValueError('가격 저장 개수가 수신 결과와 다릅니다.')
            summary['symbols'].append({'symbol':result['symbol'],'rows':saved,'start':frame.date.min(),'end':frame.date.max()});summary['rows']+=saved
        except (ValueError,KeyError) as error:summary['errors'].append({'symbol':result.get('symbol'),'error':str(error)})
    summary['status']='partial' if summary['errors'] else 'completed'
    atomic_json(summary,ROOT/'runtime/operations/market_history/collection.json')
    return summary


def collection_status():
    from ..provider_settings.operations import provider_status
    sources=[item['name'] for item in provider_status()['items'] if item['name']=='FMP' and item['configured']]
    return {'status':'configured' if sources else 'requires_configuration','source':'FMP',
        'available_sources':sources,'reason':None if sources else 'FMP 인증이 없어 원격 가격 수집을 실행할 수 없습니다.'}


def prices(currency='USD',symbols=None):
    import pandas as pd
    store=price_store()
    import sqlite3
    from contextlib import closing
    with closing(sqlite3.connect(store.db_path)) as connection:
        available=pd.read_sql_query('SELECT DISTINCT ticker FROM price_data',connection).ticker.tolist()
        start,end=connection.execute('SELECT MIN(date),MAX(date) FROM price_data').fetchone()
    import json
    market=json.loads((ROOT/'configs/instruments.json').read_text(encoding='utf8'))
    allowed=set(available) if currency is None else {i['symbol'] for i in market['instruments'] if i.get('market') in (('KRX','KOSDAQ') if currency=='KRW' else ('US','NASDAQ','NYSE','NYSEARCA','AMEX')) and i.get('asset_class') in ('equity','etf')}
    names=symbols or [s for s in available if s in allowed]
    if start is None:return pd.DataFrame()
    from stockrl.management.connection_settings.provider_credentials import read_settings
    kiwoom=currency=='KRW' and read_settings(ROOT/'runtime/operations').get('provider')=='kiwoom'
    data=store.get_price_data(names,start,end,source='kiwoom',timeframe='1d') if kiwoom else store.get_price_data(names,start,end)
    if data.empty:return pd.DataFrame()
    data=data.rename(columns={'tic':'symbol','datadate':'date','prcod':'open','prchd':'high','prcld':'low','prccd':'close','cshtrd':'volume'})
    dates=pd.to_datetime(data.date,utc=True,format='mixed')
    if kiwoom:
        data['date']=dates.dt.tz_localize(None)
        data=data.sort_values(['date','symbol']).reset_index(drop=True);data.attrs.update(timeframe='1d',source='kiwoom')
        return data
    feed=ROOT/'runtime/operations/live/timeframes.sqlite3'
    if feed.is_file():
        with closing(sqlite3.connect('file:'+feed.as_posix()+'?mode=ro',uri=True)) as connection:
            tables={row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if 'received_bars' in tables:
                raw=set(connection.execute('SELECT symbol,stamp_ns FROM received_bars'))
                daily=set(connection.execute('SELECT symbol,stamp_ns FROM daily_bars')) if 'daily_bars' in tables else set()
                keep=[(str(symbol),int(stamp.value)) not in raw or (str(symbol),int(stamp.value)) in daily for symbol,stamp in zip(data.symbol,dates)]
                data=data.loc[keep].copy();dates=dates.loc[keep]
            if 'daily_bars' in tables:
                placeholders=','.join('?' for _ in names)
                authoritative=pd.read_sql_query('SELECT symbol,stamp_ns,open,high,low,close,volume FROM daily_bars WHERE symbol IN ('+placeholders+')',connection,params=names) if names else pd.DataFrame()
                if not authoritative.empty:
                    authoritative['date']=pd.to_datetime(authoritative.pop('stamp_ns'),utc=True)
                    keys=set(zip(authoritative.symbol,authoritative.date.dt.normalize()))
                    keep=[(symbol,date.normalize()) not in keys for symbol,date in zip(data.symbol,dates)]
                    historical=data.loc[keep]
                    data=authoritative.copy() if historical.empty else pd.concat([historical,authoritative],ignore_index=True)
                    dates=pd.to_datetime(data.date,utc=True,format='mixed')
    data['date']=dates.dt.tz_localize(None).dt.normalize()
    data=data.drop_duplicates(subset=['symbol','date','open','high','low','close','volume'])
    if data.duplicated(['symbol','date']).any():raise ValueError('서로 다른 주기의 가격 또는 상충하는 일봉이 남아 있어 학습에 사용할 수 없습니다.')
    data=data.sort_values(['date','symbol']).reset_index(drop=True)
    data.attrs['timeframe']='1d'
    return data
