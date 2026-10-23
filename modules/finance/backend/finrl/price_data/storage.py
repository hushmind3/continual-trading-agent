"""Local SQLite price storage used by FinRL inputs and live bars."""
from contextlib import closing
from pathlib import Path
import sqlite3
import logging
import pandas as pd
from ... import ROOT

class PriceStore:
    def __init__(self,directory=None):
        self.db_path=Path(directory or ROOT/'data')/'market_prices.sqlite3'
        self.db_path.parent.mkdir(parents=True,exist_ok=True)
        with closing(sqlite3.connect(self.db_path)) as db,db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('''CREATE TABLE IF NOT EXISTS price_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,ticker TEXT NOT NULL,date TEXT NOT NULL,
                open REAL,high REAL,low REAL,close REAL,adj_close REAL,volume REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source TEXT NOT NULL DEFAULT 'unknown',timeframe TEXT NOT NULL DEFAULT 'unknown',
                UNIQUE(ticker,date,source,timeframe))''')
            columns={row[1] for row in db.execute('PRAGMA table_info(price_data)')}
            for name in ('source','timeframe'):
                if name not in columns:db.execute('ALTER TABLE price_data ADD COLUMN '+name+" TEXT NOT NULL DEFAULT 'unknown'")
            indexes=list(db.execute('PRAGMA index_list(price_data)'))
            old_unique={index[1] for index in indexes if index[2] and [row[2] for row in db.execute('PRAGMA index_info("'+index[1].replace('"','""')+'")')]==['ticker','date']}
            if old_unique:
                fields='id,ticker,date,open,high,low,close,adj_close,volume,created_at,source,timeframe'
                if {row[1] for row in db.execute('PRAGMA table_info(price_data)')}!=set(fields.split(',')):
                    raise RuntimeError('가격 저장소에 알 수 없는 열이 있어 자동 이관하지 않습니다.')
                definitions=[row[1] for row in db.execute("SELECT name,sql FROM sqlite_master WHERE tbl_name='price_data' AND type IN ('index','trigger') AND sql IS NOT NULL") if row[0] not in old_unique]
                sequence=db.execute("SELECT seq FROM sqlite_sequence WHERE name='price_data'").fetchone()
                db.execute('''CREATE TABLE price_data_by_origin (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,ticker TEXT NOT NULL,date TEXT NOT NULL,
                    open REAL,high REAL,low REAL,close REAL,adj_close REAL,volume REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    source TEXT NOT NULL DEFAULT 'unknown',timeframe TEXT NOT NULL DEFAULT 'unknown',
                    UNIQUE(ticker,date,source,timeframe))''')
                db.execute('INSERT INTO price_data_by_origin ('+fields+') SELECT '+fields+' FROM price_data')
                if db.execute('SELECT COUNT(*) FROM price_data_by_origin').fetchone()!=db.execute('SELECT COUNT(*) FROM price_data').fetchone():
                    raise RuntimeError('가격 저장소 이관 개수가 일치하지 않아 취소합니다.')
                db.execute('DROP TABLE price_data')
                db.execute('ALTER TABLE price_data_by_origin RENAME TO price_data')
                if sequence:db.execute("UPDATE sqlite_sequence SET seq=MAX(seq,?) WHERE name='price_data'",sequence)
                for definition in definitions:db.execute(definition)

    def save_price_data(self,frame):
        if frame.empty:return 0
        data=frame.copy().rename(columns={key:value for key,value in {
            'tic':'ticker','datadate':'date','prcod':'open','prchd':'high',
            'prcld':'low','prccd':'close','cshtrd':'volume'}.items() if value not in frame.columns})
        for name in ('ticker','date','open','high','low','close','adj_close','volume'):
            if name not in data:
                if name=='ticker':data[name]=data.get('gvkey','UNKNOWN')
                elif name=='date':data[name]=data.index if isinstance(data.index,pd.DatetimeIndex) else data.get('datadate')
                else:data[name]=float('nan')
        affected=0
        with closing(sqlite3.connect(self.db_path)) as db,db:
            for _,row in data.iterrows():
                try:
                    origin=[]
                    for name in ('source','timeframe'):
                        value=row.get(name)
                        origin.append(str(data.attrs.get(name,'unknown') if value is None or pd.isna(value) else value))
                    stamp=pd.Timestamp(row.date)
                    if pd.isna(stamp):raise ValueError('가격 시각이 유효하지 않습니다.')
                    if origin[1]=='1d' or (origin[1]=='unknown' and stamp==stamp.normalize()):date=stamp.date().isoformat()
                    else:date=(stamp.tz_localize('UTC') if stamp.tzinfo is None else stamp.tz_convert('UTC')).isoformat()
                    values=[row.ticker,date,*[float(row[name]) if pd.notna(row[name]) else None for name in ('open','high','low','close','adj_close','volume')],*origin]
                    db.execute('''INSERT INTO price_data (ticker,date,open,high,low,close,adj_close,volume,source,timeframe)
                        VALUES (?,?,?,?,?,?,?,?,?,?) ON CONFLICT(ticker,date,source,timeframe) DO UPDATE SET
                        open=excluded.open,high=excluded.high,low=excluded.low,close=excluded.close,
                        adj_close=excluded.adj_close,volume=excluded.volume''',values)
                    affected+=1
                except (sqlite3.Error,TypeError,ValueError) as exc:logging.getLogger(__name__).warning('Price save failed: %s',exc)
        return affected

    def get_price_data(self,tickers,start,end,source=None,timeframe=None):
        names=tickers.astype(str).tolist() if isinstance(tickers,pd.Series) else list(tickers or [])
        if not names:return pd.DataFrame()
        placeholders=','.join('?' for _ in names)
        with closing(sqlite3.connect(self.db_path)) as db:
            upper=end
            if isinstance(end,str) and len(end)==10 and end[4]=='-' and end[7]=='-':
                upper=(pd.Timestamp(end)+pd.Timedelta(days=1)-pd.Timedelta(nanoseconds=1)).isoformat()+'+00:00'
            clause='';params=[*names,start,upper]
            for key,value in [('source',source),('timeframe',timeframe)]:
                if value is not None:clause+=' AND '+key+'=?';params.append(value)
            data=pd.read_sql_query('SELECT ticker,date,open,high,low,close,adj_close,volume,source,timeframe FROM price_data WHERE ticker IN ('+placeholders+') AND date>=? AND date<=?'+clause+' ORDER BY ticker,date',db,params=params)
        if not data.empty:
            data=data.rename(columns={'ticker':'tic','date':'datadate','open':'prcod','high':'prchd','low':'prcld','close':'prccd','volume':'cshtrd'})
            data['gvkey']=data.tic
        return data


def clean_price_data(frame):
    data=frame.drop_duplicates(subset=['gvkey','datadate']).copy()
    data['datadate']=pd.to_datetime(data.datadate)
    data=data[(data.prccd>0)&(data.ajexdi>0)].copy()
    data['adj_close']=data.prccd/data.ajexdi
    for target,source in (('adj_open','prcod'),('adj_high','prchd'),('adj_low','prcld')):
        data[target]=data[source]/data.ajexdi if source in data else data.adj_close
    return data
