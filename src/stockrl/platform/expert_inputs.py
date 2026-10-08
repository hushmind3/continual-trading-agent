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


def admission_input(batches,snapshot,ttl=300):
    """Use a live batch, rather than whichever closed-market symbols sort first."""
    if batches==[None]:return None
    def score(batch):
        allowed=4*86400 if batch.get('sampling_seconds')==86400 else ttl
        stamps=[rows[-1] for rows in batch.get('observation_timestamps',[]) if rows]
        if not stamps:stamps=[rows[-1]['timestamp'] for rows in batch.get('bars',[]) if rows]
        if not stamps:stamps=[batch['as_of']]
        ages=[(pd.Timestamp(snapshot['as_of'])-pd.Timestamp(stamp)).total_seconds() for stamp in stamps]
        return sum(0<=age<=allowed for age in ages),-min(ages)
    selected=max(batches,key=score)
    if not score(selected)[0]:raise ValueError('현재 사용 가능한 완료 시세가 없습니다. 해당 시장의 새 시세를 기다리세요.')
    return selected
