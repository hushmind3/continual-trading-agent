"""Gymnasium market learning with the same whole-share ledger as paper operation."""
from types import SimpleNamespace
import gymnasium as gym
import numpy as np
import pandas as pd
from stockrl.trading.virtual_account_orders.paper_account import PaperAccount
from stockrl.trading.operation_control.operations_settings import settings


class MarketLearningEnv(gym.Env):
    metadata={'render_modes':[]}
    WARMUP_BARS=32
    def __init__(self,frame,symbols,currency,fee=None,slippage=None,start_index=None,continuous=False):
        self.symbols=list(symbols);self.currency=currency
        self._df=frame.copy();self._df['date']=pd.to_datetime(self._df.date)
        if self._df.duplicated(['date','symbol']).any():raise ValueError('같은 시각·종목의 가격이 중복돼 있습니다.')
        columns=['open','high','low','close','volume']
        values=self._df[columns].to_numpy(dtype=float)
        if not np.isfinite(values).all() or (values[:,:4]<=0).any() or (values[:,4]<0).any():raise ValueError('학습 시세의 가격·거래량이 유효하지 않습니다.')
        if ((values[:,2]>values[:,:4].min(axis=1))|(values[:,1]<values[:,:4].max(axis=1))).any():raise ValueError('학습 시세의 고저 범위가 유효하지 않습니다.')
        if not set(self._df.symbol)<=set(self.symbols):raise ValueError('학습 시세와 등록 종목 구성이 다릅니다.')
        self._sorted_times=np.sort(self._df.date.unique())
        if len(self._sorted_times)<2:raise ValueError('학습에 서로 다른 시각의 시세가 2개 이상 필요합니다.')
        self._start_index=min(self.WARMUP_BARS-1,len(self._sorted_times)-2) if start_index is None else int(start_index)
        if not 0<=self._start_index<len(self._sorted_times)-1:raise ValueError('이어 학습 시작 시각이 가격 범위 밖입니다.')
        self.consumed_until=None;self.transition_count=0;self.continuous=bool(continuous)
        self.fields={name:self._df.pivot(index='date',columns='symbol',values=name).reindex(index=self._sorted_times,columns=self.symbols).to_numpy(dtype=float) for name in columns}
        observed=np.isfinite(self.fields['close'])
        groups={symbol:('KRX' if currency=='KRW' else 'US','equity') for symbol in self.symbols}
        self.panel=SimpleNamespace(dates=self._sorted_times,symbols=self.symbols,groups=groups,
            closes=self.fields['close'],observed=observed,features=np.zeros((len(self._sorted_times),len(symbols),8)))
        self.previous=pd.DataFrame(self.fields['close']).ffill().shift(1).to_numpy()
        risk=settings().risk
        self.fee=risk.fee if fee is None else fee;self.slippage=risk.slippage if slippage is None else slippage
        self.action_space=gym.spaces.Box(0,1,shape=(len(symbols)+1,),dtype=np.float32)
        self.observation_space=gym.spaces.Box(-np.inf,np.inf,shape=(6,len(symbols)),dtype=np.float32)
        self.reset()

    def _get_state_and_info_from_time_index(self,index):
        observed=self.panel.observed[index];close=self.fields['close'][index]
        previous=self.previous[index]
        with np.errstate(divide='ignore',invalid='ignore'):
            state=np.stack([close/previous-1,self.fields['high'][index]/close-1,
                self.fields['low'][index]/close-1,np.log1p(self.fields['volume'][index])/16,
                observed.astype(float),np.zeros(len(self.symbols))])
        state=np.nan_to_num(state,nan=0,posinf=0,neginf=0).astype(np.float32)
        state[:,~observed]=0
        nav=self.account._equity(self.currency);book=self.account.state['books'][self.currency]
        state[-1]=[book['positions'].get(symbol,{}).get('quantity',0)*book['marks'].get(symbol,0)/max(nav,1e-9) for symbol in self.symbols]
        self._portfolio_value=nav
        return state,{'end_time':str(pd.Timestamp(self._sorted_times[index])),'observed_symbols':[self.symbols[j] for j in np.flatnonzero(observed)]}

    def reset(self,seed=None,options=None):
        super().reset(seed=seed)
        self.account=PaperAccount.in_memory(self.fee,self.slippage)
        self._initial_amount=self.account.state['books'][self.currency]['initial_cash']
        self._time_index=self._start_index
        for index in range(self._time_index+1):self.account.process_bar(self.panel,index,False)
        self._final_weights=[np.r_[1.,np.zeros(len(self.symbols))]]
        self._state,self._info=self._get_state_and_info_from_time_index(self._time_index)
        return self._state.copy(),dict(self._info)

    def step(self,action):
        if self._time_index>=len(self._sorted_times)-1:raise RuntimeError('종료된 학습 에피소드는 reset 후 실행하세요.')
        values=self.normalized_action(action)
        previous=self.account._equity(self.currency)
        self.account.queue_allocations(self.panel,self._time_index,values,self.currency)
        self._time_index+=1
        fills=self.account.process_bar(self.panel,self._time_index,True)
        self._state,self._info=self._get_state_and_info_from_time_index(self._time_index)
        stamp=pd.Timestamp(self._info['end_time'])
        if self.consumed_until is None or stamp>self.consumed_until:self.consumed_until=stamp
        self.transition_count+=1
        nav=self._portfolio_value;book=self.account.state['books'][self.currency]
        weights=np.r_[book['cash']/max(nav,1e-9),self._state[-1]]
        self._final_weights.append(weights)
        reward=float(np.log(max(nav,1e-9)/max(previous,1e-9)))
        info={**self._info,'portfolio_value':nav,'fills':fills,'reward_basis':'net_equity_log_return'}
        end=self._time_index==len(self._sorted_times)-1
        return self._state.copy(),reward,end and not self.continuous,end and self.continuous,info

    def normalized_action(self,action):
        values=np.asarray(action,dtype=float)
        if values.shape!=self.action_space.shape or not np.isfinite(values).all() or (values<0).any():raise ValueError('정책의 현금·종목 비중이 유효하지 않습니다.')
        return values/values.sum() if values.sum()>0 else np.r_[1.,np.zeros(len(self.symbols))]

    def observation_for_account(self,value,account):
        state=np.asarray(value,dtype=np.float32).reshape(self.observation_space.shape).copy()
        nav=max(float(account['nav']),1e-9)
        state[-1]=[float(account['positions'].get(symbol,0))*float(account['marks'].get(symbol,0))/nav for symbol in self.symbols]
        return state
