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
            db.execute('''CREATE TABLE IF NOT EXISTS price_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,ticker TEXT NOT NULL,date TEXT NOT NULL,
                open REAL,high REAL,low REAL,close REAL,adj_close REAL,volume REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,UNIQUE(ticker,date))''')

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
        if not isinstance(data.date.iloc[0],str):data['date']=pd.to_datetime(data.date).dt.strftime('%Y-%m-%d')
        affected=0
        with closing(sqlite3.connect(self.db_path)) as db,db:
            for _,row in data.iterrows():
                try:
                    values=[row.ticker,row.date,*[float(row[name]) if pd.notna(row[name]) else None for name in ('open','high','low','close','adj_close','volume')]]
                    db.execute('INSERT OR REPLACE INTO price_data (ticker,date,open,high,low,close,adj_close,volume) VALUES (?,?,?,?,?,?,?,?)',values)
                    affected+=1
                except (sqlite3.Error,TypeError,ValueError) as exc:logging.getLogger(__name__).warning('Price save failed: %s',exc)
        return affected

    def get_price_data(self,tickers,start,end):
        names=tickers.astype(str).tolist() if isinstance(tickers,pd.Series) else list(tickers or [])
        if not names:return pd.DataFrame()
        placeholders=','.join('?' for _ in names)
        with closing(sqlite3.connect(self.db_path)) as db:
            data=pd.read_sql_query('SELECT ticker,date,open,high,low,close,adj_close,volume FROM price_data WHERE ticker IN ('+placeholders+') AND date>=? AND date<=? ORDER BY ticker,date',db,params=[*names,start,end])
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
