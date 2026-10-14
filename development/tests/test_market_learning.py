import unittest
from types import SimpleNamespace
import numpy as np
import pandas as pd
from stockrl.finrl.policy_learning.market_environment import MarketLearningEnv
from stockrl.trading.virtual_account_orders.paper_account import PaperAccount


def row(symbol,date,close=100):
    return dict(symbol=symbol,date=pd.Timestamp(date),open=close,high=close,low=close,close=close,volume=10)


class MarketLearningTests(unittest.TestCase):
    def test_continuation_includes_latest_completed_data_while_initial_keeps_holdout(self):
        from stockrl.finrl.framework import learning_frame
        frame=pd.DataFrame([row('A',date) for date in pd.date_range('2024-01-01',periods=600)])
        initial=learning_frame(frame);continued=learning_frame(frame,include_latest=True)
        self.assertLess(initial.date.max(),frame.date.max())
        self.assertEqual(continued.date.max(),frame.date.max())

    def test_live_account_observation_uses_actual_positions(self):
        frame=pd.DataFrame([row('A','2026-01-01'),row('A','2026-01-02')])
        env=MarketLearningEnv(frame,['A'],'USD',fee=0,slippage=0)
        value=env.reset()[0];actual=env.observation_for_account(value,{'nav':10000,'positions':{'A':50},'marks':{'A':100}})
        self.assertEqual(actual[-1,0],.5)
        self.assertEqual(value[-1,0],0)

    def test_prelisting_asset_stays_masked_and_cannot_be_bought(self):
        dates=pd.date_range('2026-01-01',periods=4)
        frame=pd.DataFrame([row('A',date) for date in dates]+[row('B',dates[-1],200)])
        env=MarketLearningEnv(frame,['A','B'],'USD',fee=0,slippage=0)
        state,_=env.reset()
        self.assertEqual(state[4].tolist(),[1,0])
        self.assertTrue(np.isfinite(state).all())
        self.assertTrue(np.isnan(env.panel.closes[:-1,1]).all())
        _,reward,done,_,info=env.step([0,0,1])
        self.assertTrue(done);self.assertEqual(reward,0);self.assertEqual(info['fills'],[])
        self.assertEqual(env.account.state['books']['USD']['positions'],{})

    def test_net_reward_includes_fees_and_future_price_changes(self):
        dates=pd.date_range('2026-01-01',periods=34)
        frame=pd.DataFrame([row('A',date,200 if j==33 else 100) for j,date in enumerate(dates)])
        env=MarketLearningEnv(frame,['A'],'USD',fee=.01,slippage=0)
        _,cost_reward,done,_,info=env.step([0,1])
        self.assertFalse(done);self.assertLess(cost_reward,0)
        self.assertEqual(info['fills'][0]['price'],100)
        self.assertGreater(info['fills'][0]['fee'],0)
        self.assertEqual(info['fills'][0]['date'][:10],'2026-02-02')
        _,growth_reward,done,_,info=env.step([0,1])
        self.assertTrue(done);self.assertGreater(growth_reward,0)
        self.assertAlmostEqual(cost_reward+growth_reward,np.log(info['portfolio_value']/10000),places=6)

    def test_unobserved_held_asset_is_preserved_without_stale_fill(self):
        dates=pd.date_range('2026-01-01',periods=34)
        frame=pd.DataFrame([row('A',date) for date in dates]+[row('B',date) for date in dates[:-1]])
        env=MarketLearningEnv(frame,['A','B'],'USD',fee=0,slippage=0)
        env.step([0,0,1])
        book=env.account.state['books']['USD'];quantity=book['positions']['B']['quantity']
        _,_,_,_,info=env.step([1,0,0])
        self.assertEqual(info['fills'],[])
        self.assertEqual(book['positions']['B']['quantity'],quantity)
        self.assertEqual(env._state[4,1],0)

    def test_sells_release_cash_before_same_bar_buys(self):
        account=PaperAccount.in_memory(0,0)
        account._fill('B','USD','BUY',100,0,10000,'2026-01-01')
        panel=SimpleNamespace(dates=['2026-01-02','2026-01-03'],symbols=['A','B'],
            groups={'A':('US','equity'),'B':('US','equity')},
            observed=np.ones((2,2),bool),closes=np.full((2,2),100.),features=np.zeros((2,2,8)))
        account.process_bar(panel,0,False)
        account.queue_allocations(panel,0,[0,1,0],'USD')
        fills=account.process_bar(panel,1,True)
        self.assertEqual([fill['action'] for fill in fills],['SELL','BUY'])
        self.assertEqual(account.state['books']['USD']['positions']['A']['quantity'],100)
        self.assertEqual(account.state['books']['USD']['positions'].get('B',{}).get('quantity',0),0)

    def test_future_row_does_not_change_current_observation(self):
        dates=pd.date_range('2026-01-01',periods=34)
        frame=pd.DataFrame([row('A',date) for date in dates])
        changed=frame.copy();changed.loc[33,['open','high','low','close']]=1000
        original=MarketLearningEnv(frame,['A'],'USD',fee=0,slippage=0)
        future=MarketLearningEnv(changed,['A'],'USD',fee=0,slippage=0)
        np.testing.assert_array_equal(original.reset()[0],future.reset()[0])

    def test_registered_asset_without_history_keeps_fixed_action_slot(self):
        frame=pd.DataFrame([row('A','2026-01-01'),row('A','2026-01-02')])
        env=MarketLearningEnv(frame,['A','B'],'USD',fee=0,slippage=0)
        self.assertEqual(env.action_space.shape,(3,))
        self.assertEqual(env.observation_space.shape,(6,2))
        self.assertEqual(env.reset()[0][4,1],0)

    def test_short_history_training_and_evaluation_are_disjoint(self):
        from stockrl.finrl.framework import learning_frame
        frame=pd.DataFrame([row('A',date) for date in pd.date_range('2026-01-01',periods=10)])
        training=learning_frame(frame)
        evaluation=learning_frame(frame,training=False)
        self.assertEqual(training.date.nunique(),8)
        self.assertEqual(evaluation.date.nunique(),2)
        self.assertLess(training.date.max(),evaluation.date.min())
        self.assertFalse(set(training.date)&set(evaluation.date))

    def test_insufficient_history_raises_before_split_indexing(self):
        from stockrl.finrl.framework import learning_frame
        for frame in (pd.DataFrame([row('A','2026-01-01')]),pd.DataFrame(columns=['date','symbol'])):
            with self.subTest(rows=len(frame)),self.assertRaisesRegex(ValueError,'실제 가격이 부족'):
                learning_frame(frame)
