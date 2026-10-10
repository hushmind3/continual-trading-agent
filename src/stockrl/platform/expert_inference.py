"""Shared Expert input construction and output checks for inspection and SAC."""
import numpy as np
import pandas as pd

from .observations import InputUnavailable,native_input


def prepare_inputs(entry, frame, account):
    if frame.empty:
        raise InputUnavailable('실제 가격 데이터가 없습니다.')
    frame=frame.sort_values('date')
    stamp=str(frame.date.max())
    daily=frame[frame.date<pd.Timestamp(stamp).normalize()]
    policy=bool(entry.get('stock_policy'))
    if policy and account.get('currency','USD')!='USD':
        raise InputUnavailable('이 Expert의 원본 계약은 USD 계좌입니다.')
    snapshot={'symbols':sorted(frame.symbol.unique()),'as_of':stamp,'policy_account':account}
    if policy:
        snapshot['stock_policy_history']=daily.assign(date=daily.date.astype(str)).to_dict('records')
    batches=[None] if policy else native_input(entry['backend'],frame,daily,stamp)
    if not batches:
        raise InputUnavailable('Expert 추론 입력 묶음이 없습니다.')
    return snapshot,batches


def run_batches(pool,key,snapshot,batches):
    packets=[]
    for data in batches:
        packet=pool.run(key,data,snapshot)
        values=np.asarray(packet['native_output'],dtype=float)
        symbols=packet.get('symbols',[])
        if not symbols or values.size==0:
            raise ValueError('Expert 출력 또는 종목이 비어 있습니다.')
        if not np.isfinite(values).all():
            raise ValueError('Expert 출력에 NaN/Inf가 있습니다.')
        if 'output_shape' in packet and tuple(packet['output_shape'])!=values.shape:
            raise ValueError('Expert 선언 출력 크기와 실제 출력 크기가 다릅니다.')
        if packet.get('layout')=='nine_quantiles,batch,variate,horizon':
            valid=values.ndim==4 and values.shape[0]==9 and values.shape[2]==len(symbols)
        else:
            valid=values.ndim>=1 and values.shape[0]==len(symbols)
        if not valid:
            raise ValueError('Expert 출력 차원과 종목 수가 일치하지 않습니다.')
        if data is not None and list(symbols)!=list(data['symbols']):
            raise ValueError('Expert 입력·출력 종목 순서가 다릅니다.')
        if data is None and not set(symbols).issubset(snapshot['symbols']):
            raise ValueError('Expert 출력에 입력하지 않은 종목이 있습니다.')
        packets.append(packet)
    if not packets:
        raise ValueError('Expert가 실행한 추론 묶음이 없습니다.')
    return packets
