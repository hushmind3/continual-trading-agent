"""Same point-in-time input preparation for live inference and admission tests."""
import numpy as np
import pandas as pd
from .observations import daily_history,native_input


def snapshot_for(entry,frame,journal,daily_path,daily=None):
    frame=frame.copy();frame['date']=pd.to_datetime(frame.date,utc=True).dt.tz_localize(None)
    if frame.empty:raise ValueError('실제 시세가 아직 없습니다.')
    stamp=str(frame.date.max())
    if daily is None:daily=daily_history(daily_path,stamp)
    policy=entry.get('stock_policy')
    if policy and not daily.empty:daily=daily[daily.symbol.isin(policy['universe'])]
    account=journal.get_state('account') or {};book=account.get('books',{}).get('USD',{})
    nav=book.get('cash',0)+sum(p['quantity']*book.get('marks',{}).get(s,p['average_cost']) for s,p in book.get('positions',{}).items())
    history=[r['equity'] for r in journal.history('USD',128)]
    snapshot=dict(symbols=sorted(frame.symbol.unique()),as_of=stamp,
        stock_policy_history=daily.assign(date=daily.date.astype(str)).to_dict('records') if policy and not daily.empty else [],
        policy_account=dict(cash=book.get('cash',0),nav=nav,positions={s:p['quantity'] for s,p in book.get('positions',{}).items()},
            trades=book.get('trade_count',0),costs=sum(book.get(k,0) for k in ('fees','slippage','spread','sell_tax')),
            drawdown=1-nav/max([nav,*history],default=1) if nav else 0,
            volatility=float(np.std(np.diff(np.log(np.maximum(history,1e-9))))) if len(history)>1 else 0))
    batches=[None] if policy else native_input(entry['backend'],frame,daily,stamp)
    return batches,snapshot
