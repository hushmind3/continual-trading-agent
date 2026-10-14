"""Expert outputs enter the official learner solely through Gymnasium observation API."""
import gymnasium as gym
import numpy as np
import pandas as pd


class ExpertObservation(gym.ObservationWrapper):
    def __init__(self,env,registry,frame,symbols,champion_ids=None,structure_only=False):
        super().__init__(env);self.registry=registry;self.frame=frame;self.symbols=symbols
        self.champion_ids=list(registry.catalog().get('active',[])) if champion_ids is None else list(champion_ids)
        self.structure_only=structure_only
        extra=64*len(self.champion_ids)+16
        self.dates=np.sort(frame.date.unique());self.assets=[]
        self.observation_space=gym.spaces.Box(
            np.concatenate([env.observation_space.low.reshape(-1),np.full(extra,-np.inf)]).astype(np.float32),
            np.concatenate([env.observation_space.high.reshape(-1),np.full(extra,np.inf)]).astype(np.float32),dtype=np.float32)

    def observation(self,value):
        if self.structure_only:return np.zeros(self.observation_space.shape,dtype=np.float32)
        base=self.unwrapped
        stamp=pd.Timestamp(base._info['end_time'])
        portfolio_value=float(base._portfolio_value);self.assets.append(portfolio_value)
        history=self.frame[self.frame.date<=stamp];nav=max(portfolio_value,1e-9)
        allocation=base._final_weights[-1];weights=allocation[1:]
        marks=history.sort_values('date').groupby('symbol').close.last()
        cash=nav*float(allocation[0])
        account={'currency':getattr(self,'currency','USD'),'cash':cash,'nav':nav,
            'positions':{symbol:float(weight*nav/marks[symbol]) for symbol,weight in zip(self.symbols,weights) if weight and symbol in marks},
            'drawdown':1-nav/max(self.assets),'volatility':float(np.std(np.diff(np.log(np.maximum(self.assets,1e-9))))) if len(self.assets)>1 else 0.}
        initial_amount=float(base._initial_amount)
        if getattr(self,'live_account',None):
            account.update(self.live_account);nav=float(account['nav']);cash=float(account['cash'])
            initial_amount=float(account['initial_cash'])
            if not np.isfinite(initial_amount) or initial_amount<=0:raise ValueError('계좌 초기자본이 유효하지 않습니다.')
            positions=account['positions'];live_marks=account['marks']
            outside=sorted(symbol for symbol,quantity in positions.items() if quantity and symbol not in self.symbols)
            if outside:raise ValueError('모델 관측 종목에 없는 보유 포지션: '+', '.join(outside))
            if any(float(positions.get(symbol,0)) and symbol not in live_marks for symbol in self.symbols):
                raise ValueError('실제 보유 종목의 평가 시세가 없습니다.')
            weights=np.asarray([float(positions.get(symbol,0))*float(live_marks.get(symbol,0))/nav if nav>0 else 0 for symbol in self.symbols])
            values=[float(point['nav']) for point in account['equity_history']]
            if not values or values[-1]!=nav:values.append(nav)
            account['drawdown']=1-nav/max(initial_amount,*values)
            account['volatility']=float(np.std(np.diff(np.log(np.maximum(values,1e-9))))) if len(values)>1 else 0.
            if hasattr(base,'observation_for_account'):value=base.observation_for_account(value,account)
        signals=self.registry.outputs(history,account,champion_ids=self.champion_ids)
        fractions=np.asarray(weights,dtype=np.float32)
        quantiles=np.quantile(fractions,[0,.25,.5,.75,1]).astype(np.float32) if len(fractions) else np.zeros(5,dtype=np.float32)
        account_features=np.asarray([nav/initial_amount,cash/initial_amount,account['drawdown'],account['volatility'],
            len(fractions)/max(1,len(self.symbols)),float(fractions.sum()),float(fractions.mean()) if len(fractions) else 0.,
            float(fractions.std()) if len(fractions) else 0.,*quantiles,
            float((fractions>0).sum())/max(1,len(fractions)),float(np.square(fractions).sum()),0.],dtype=np.float32)
        return np.concatenate([np.asarray(value,dtype=np.float32).reshape(-1),signals,account_features])

    def reset(self,**kwargs):self.assets=[];return super().reset(**kwargs)

    @property
    def df(self):
        return self.unwrapped._df

    def get_sb_env(self):
        from stable_baselines3.common.vec_env import DummyVecEnv
        env=DummyVecEnv([lambda:self])
        return env,env.reset()
