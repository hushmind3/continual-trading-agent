"""Expert outputs enter the official learner solely through Gymnasium observation API."""
import gymnasium as gym
import numpy as np
import pandas as pd


class ExpertObservation(gym.ObservationWrapper):
    def __init__(self,env,registry,frame,symbols,champion_ids=None):
        super().__init__(env);self.registry=registry;self.frame=frame;self.symbols=symbols
        self.champion_ids=None if champion_ids is None else list(champion_ids)
        extra=8 if champion_ids is None else 64*len(champion_ids)+16
        self.dates=np.sort(frame.date.unique());self.assets=[]
        self.observation_space=gym.spaces.Box(
            np.concatenate([env.observation_space.low.reshape(-1),np.full(extra,-np.inf)]).astype(np.float32),
            np.concatenate([env.observation_space.high.reshape(-1),np.full(extra,np.inf)]).astype(np.float32),dtype=np.float32)

    def observation(self,value):
        base=self.unwrapped;stamp=pd.Timestamp(base.data.date.iloc[0]);self.assets.append(float(base.portfolio_value))
        history=self.frame[self.frame.date<=stamp]
        nav=max(float(base.portfolio_value),1e-9)
        weights=base.actions_memory[-1]
        marks=base.data.set_index('tic').close
        cash=max(0.,nav*(1-float(np.sum(weights))))
        account={'currency':getattr(self,'currency','USD'),'cash':cash,'nav':nav,
            'positions':{symbol:float(weight*nav/marks[symbol]) for symbol,weight in zip(self.symbols,weights)},
            'drawdown':1-nav/max(self.assets),'volatility':float(np.std(np.diff(np.log(np.maximum(self.assets,1e-9))))) if len(self.assets)>1 else 0.}
        signals=self.registry.outputs(history,account,champion_ids=self.champion_ids)
        if self.champion_ids is None:return np.concatenate([np.asarray(value,dtype=np.float32).reshape(-1),signals])
        fractions=np.asarray(weights,dtype=np.float32)
        quantiles=np.quantile(fractions,[0,.25,.5,.75,1]).astype(np.float32) if len(fractions) else np.zeros(5,dtype=np.float32)
        initial_amount=float(getattr(base,'initial_amount',1000000.))
        account_features=np.asarray([nav/max(initial_amount,1.),cash/max(initial_amount,1.),account['drawdown'],account['volatility'],
            len(fractions)/max(1,len(self.symbols)),float(fractions.sum()),float(fractions.mean()) if len(fractions) else 0.,
            float(fractions.std()) if len(fractions) else 0.,*quantiles,
            float((fractions>0).sum())/max(1,len(fractions)),float(np.square(fractions).sum()),0.],dtype=np.float32)
        return np.concatenate([np.asarray(value,dtype=np.float32).reshape(-1),signals,account_features])

    def reset(self,**kwargs):self.assets=[];return super().reset(**kwargs)
    def close(self):self.registry.close(cleanup=True);return super().close()

    @property
    def df(self):return self.unwrapped.df

    def get_sb_env(self):
        from stable_baselines3.common.vec_env import DummyVecEnv
        env=DummyVecEnv([lambda:self])
        return env,env.reset()
