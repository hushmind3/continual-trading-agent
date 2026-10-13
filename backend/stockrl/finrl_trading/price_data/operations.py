"""Existing FinRL-Trading DataStore reader."""
from ... import ROOT
from .. import finrlx

def price_store(directory=None):
    store=finrlx('data.data_store').DataStore
    return store() if directory is None else store(str(directory))


def price_processor(directory):
    return finrlx('data.data_processor').DataProcessor(str(directory))


def collection_status():
    try:
        manager=finrlx('data.data_fetcher').get_data_manager()
        sources=[name for name,source in manager.data_sources if source.is_available()]
        return {'status':'configured' if sources else 'requires_configuration',
            'source':getattr(manager,'current_source_name',None),'available_sources':sources,
            'reason':None if sources else 'FMP 인증이 없어 원격 가격 수집을 실행할 수 없습니다.'}
    except Exception as exc:
        return {'status':'unavailable','source':None,'available_sources':[],'reason':str(exc)}


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
    data=store.get_price_data(names,start,end)
    data=data.rename(columns={'tic':'symbol','datadate':'date','prcod':'open','prchd':'high','prcld':'low','prccd':'close','cshtrd':'volume'})
    dates=pd.to_datetime(data.date,utc=True,format='mixed')
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
