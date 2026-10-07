"""Point-in-time native inputs from the collector's completed, identified bars."""
from contextlib import closing
from pathlib import Path
import json
import sqlite3
import numpy as np
import pandas as pd

from .experience import IncrementalMarketCSV
from .market_panel import GlobalMarketPanel
from .paper_account import _currency


class LiveInputStream:
    def __init__(self, market, last=None):
        self.market = Path(market)
        self.reader = IncrementalMarketCSV(self.market)
        self.last = pd.Timestamp(last) if last else None
        self.reader.processed_through = last

    def next_frame(self):
        if not self.market.is_file():
            return None
        frame, _ = self.reader.refresh()
        if frame.empty:
            return None
        frame = frame.copy()
        frame['date'] = pd.to_datetime(frame.date, utc=True).dt.tz_convert(None)
        dates = sorted(frame.date.unique())
        # A new live account starts at the latest completed quote, not a replay
        # of yesterday's feed backlog. Resumption consumes every later quote.
        if self.last is None:
            stamp = pd.Timestamp(dates[-1])
        else:
            future = [pd.Timestamp(d) for d in dates if pd.Timestamp(d) > self.last]
            if not future:
                return None
            stamp = future[0]
        self.last = stamp
        self.reader.processed_through = str(stamp)
        return frame.loc[frame.date <= stamp], stamp


def daily_history(market, stamp):
    path = Path(market).with_name('timeframes.sqlite3')
    if not path.is_file():
        return pd.DataFrame()
    # Only completed days. Native policies must never observe today's partial day.
    limit = int(pd.Timestamp(stamp).normalize().value)
    with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro', uri=True)) as db:
        rows = db.execute('SELECT symbol,stamp_ns,open,high,low,close,volume FROM daily_bars WHERE stamp_ns<? ORDER BY stamp_ns,symbol', (limit,)).fetchall()
    result = pd.DataFrame(rows, columns=['symbol','stamp_ns','open','high','low','close','volume'])
    if not result.empty:
        result['date'] = pd.to_datetime(result.pop('stamp_ns'))
    return result


def live_snapshot(model, market, frame, stamp, account,*,daily_frame=None):
    panel = GlobalMarketPanel(market, raw_frame=frame)
    index = len(panel.dates)-1
    pstate, astate = account.model_inputs(panel, index)
    snapshot = dict(as_of=str(panel.dates[index]), symbols=panel.symbols,
        currencies={s:_currency(*panel.groups[s]) or 'USD' for s in panel.symbols},
        current_weights={s:float(pstate[j][1]) for j,s in enumerate(panel.symbols)},
        tradable_symbols=[s for j,s in enumerate(panel.symbols) if panel.observed[index,j] and _currency(*panel.groups[s])],
        expert_inputs={}, source_kind='live', market_path=str(Path(market).resolve()))
    histories = {}
    for symbol, group in frame.groupby('symbol'):
        bars = group.sort_values('date').tail(128)
        if len(bars)>=32 and bars.date.iloc[-1]==pd.Timestamp(stamp):
            histories[symbol] = bars
    if histories:
        length = min(len(bars) for bars in histories.values())
        price = dict(symbols=list(histories), as_of=str(stamp),
            series=[bars.close.astype(float).tail(length).tolist() for bars in histories.values()],
            observation_timestamps=[bars.date.astype(str).tail(length).tolist() for bars in histories.values()],
            horizon=1, sampling_seconds=60, frequency_id=0, units='price', input_authenticity='live_completed_OHLCV')
        for key in ('fincast','exaone','timemoe','toto'):
            snapshot['expert_inputs'][key] = price
        candles=[]
        for bars in histories.values():
            bars=bars.tail(length).rename(columns={'date':'timestamp'}).copy()
            bars['timestamp']=bars.timestamp.astype(str)
            bars['amount']=bars.close*bars.volume
            candles.append(bars[['timestamp','open','high','low','close','volume','amount']].to_dict('records'))
        snapshot['expert_inputs']['kronos'] = dict(symbols=list(histories), as_of=str(stamp), bars=candles,
            horizon=1, sampling_seconds=60, future_timestamps=[str(pd.Timestamp(stamp)+pd.Timedelta(minutes=1))],
            amount_observed=False, input_authenticity='live_OHLCV_amount_price_volume_proxy')
    daily = daily_history(market, stamp) if daily_frame is None else daily_frame.loc[daily_frame.date<pd.Timestamp(stamp).normalize()].copy()
    if not daily.empty:
        news_path=Path(market).with_name('stock_policy_news.csv')
        if news_path.is_file():
            news=pd.read_csv(news_path)
            news['date']=pd.to_datetime(news.date,utc=True).dt.tz_convert(None)
            news=news.loc[news.date<pd.Timestamp(stamp).normalize()].drop_duplicates(['date','symbol'],keep='last')
            daily=daily.merge(news[['date','symbol','llm_sentiment','llm_risk']],on=['date','symbol'],how='left')
        # The released DAPO backtest explicitly defines score 3 for missing news.
        # Report that fallback; never present it as a measured LLM opinion.
        missing_news=any(k not in daily or daily[k].isna().any() for k in ('llm_sentiment','llm_risk'))
        for key in ('llm_sentiment','llm_risk'):
            daily[key]=daily[key].fillna(3.) if key in daily else 3.
        snapshot['stock_policy_news_status']='native_missing_news_neutral_3' if missing_news else 'observed'
        history=daily.copy();history['date']=history.date.astype(str)
        snapshot['stock_policy_history']=history.to_dict('records')
    book=account.snapshot()['books']['USD']
    metrics=account.state.setdefault('policy_metrics',{})
    peak=max(float(metrics.get('USD_peak',book['initial_cash'])),float(book['equity']))
    metrics['USD_peak']=peak
    volatility=0.
    if not daily.empty and book['positions']:
        prices=daily.pivot(index='date',columns='symbol',values='close')
        weights={s:float(p['quantity'])*float(book['marks'].get(s,p['average_cost']))/float(book['equity'])
            for s,p in book['positions'].items() if s in prices}
        if weights:
            changes=prices[list(weights)].pct_change(fill_method=None).dropna()
            if len(changes)>1:volatility=float((changes*pd.Series(weights)).sum(axis=1).std())
    snapshot['policy_account']=dict(cash=float(book['cash']),nav=float(book['equity']),
        positions={s:float(p['quantity']) for s,p in book['positions'].items()},trades=int(book['trade_count']),
        costs=sum(float(book.get(k,0)) for k in ('fees','slippage','spread','sell_tax')),
        drawdown=max(0.,1-float(book['equity'])/peak),volatility=volatility)
    if not daily.empty:
        closes=daily.pivot(index='date',columns='symbol',values='close')
        if '^GSPC' in closes:
            returns=closes.pct_change(fill_method=None)
            series={s:(returns[s]-returns['^GSPC']).dropna().tail(128) for s in panel.symbols if s in returns and s!='^GSPC'}
            series={s:v for s,v in series.items() if len(v)>=32}
            if series:
                length=min(len(v) for v in series.values())
                rates=dict(symbols=list(series), as_of=str(max(v.index[-1] for v in series.values())),
                    series=[v.tail(length).tolist() for v in series.values()], horizon=1,sampling_seconds=86400,
                    units='daily_excess_return', observation_timestamps=[v.index.astype(str).tolist()[-length:] for v in series.values()],
                    input_authenticity='completed_live_daily_return_minus_SP500')
                snapshot['expert_inputs'].update(chronos=rates,timesfm=rates)
    # Optional authentic native streams: no old packaged feature/ITCH fallback.
    feature_path=Path(market).with_name('native_macrophft.csv')
    if feature_path.is_file() and 'ETHUSDT' in panel.symbols:
        native=pd.read_csv(feature_path)
        native.timestamp=pd.to_datetime(native.timestamp,utc=True).dt.tz_convert(None)
        native=native.loc[native.timestamp==pd.Timestamp(stamp)]
        if len(native)==1:
            held=bool(account.state['books']['USD']['positions'].get('ETHUSDT'))
            data=model.macro_input_adapter(native,0,int(held))
            for key in model.controller.macro_policy_ids:
                snapshot['expert_inputs'][key]={**data,'variant':model.experts[key].entry['variant']}
    itch_path=Path(market).with_name('native_itch.json')
    if itch_path.is_file():
        data=json.loads(itch_path.read_text(encoding='utf-8'))
        if data.get('native_features_verified') and data.get('token_schema')=='MarketGPT_ITCH_Vocab_v3' and pd.Timestamp(data['as_of'])==pd.Timestamp(stamp) and set(data['symbols']).issubset(panel.symbols):
            snapshot['expert_inputs']['marketgpt']=data
    reasons={key:'no compatible completed live input' for key in model.config['feature_sizes'] if key not in snapshot['expert_inputs']}
    for key in model.controller.macro_policy_ids:
        if key in reasons:reasons[key]='live ETHUSDT native 36+9 fields are required in native_macrophft.csv'
    if 'marketgpt' in reasons:reasons['marketgpt']='contemporaneous native ITCH tokens are required in native_itch.json'
    snapshot['input_status']={key:dict(status='ready' if key in snapshot['expert_inputs'] else 'blocked',reason=reasons.get(key)) for key in model.config['feature_sizes']}
    for key in model.config.get('stock_policy_ids',[]):
        snapshot['input_status'][key]=dict(status='pending',reason='native observation preparation',
            news_status=snapshot.get('stock_policy_news_status'))
    return panel,index,snapshot,np.column_stack([pstate,np.broadcast_to(astate,(len(pstate),len(astate)))])[None]
