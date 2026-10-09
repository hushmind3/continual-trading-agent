"""Expert outputs enter the official learner solely through Gymnasium observation API."""
import gymnasium as gym
import numpy as np
import pandas as pd


class ExpertObservation(gym.ObservationWrapper):
    def __init__(self,env,registry,frame,symbols):
        super().__init__(env);self.registry=registry;self.frame=frame;self.symbols=symbols
        self.dates=np.sort(frame.date.unique());self.assets=[]
        self.observation_space=gym.spaces.Box(
            np.concatenate([env.observation_space.low,np.full(8,-np.inf)]).astype(np.float32),
            np.concatenate([env.observation_space.high,np.full(8,np.inf)]).astype(np.float32),dtype=np.float32)

    def observation(self,value):
        base=self.unwrapped;stamp=pd.Timestamp(self.dates[base.day]);self.assets.append(float(base.total_asset))
        history=self.frame[self.frame.date<=stamp]
        nav=max(float(base.total_asset),1e-9)
        account={'currency':getattr(self,'currency','USD'),'cash':float(base.amount),'nav':nav,'positions':dict(zip(self.symbols,base.stocks.tolist())),
            'drawdown':1-nav/max(self.assets),'volatility':float(np.std(np.diff(np.log(np.maximum(self.assets,1e-9))))) if len(self.assets)>1 else 0.}
        signals=self.registry.outputs(history,account)
        return np.concatenate([np.asarray(value,dtype=np.float32),signals])

    def reset(self,**kwargs):self.assets=[];return super().reset(**kwargs)
    def close(self):self.registry.close();return super().close()
