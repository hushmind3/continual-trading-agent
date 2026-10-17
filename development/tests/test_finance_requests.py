"""Finance worker-router boundaries with in-process mocks and isolated accounts.

The host forwards over IPC, so patching its process cannot mock the worker.
Valid write requests are tested only against the module router in this process.
"""
import copy
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch

import pandas as pd
from fastapi import FastAPI
from fastapi.testclient import TestClient
from stockrl.trading.operation_control import operations_runtime
from stockrl.trading.operation_control import handlers as control_handlers
from stockrl.trading.operation_control import operations_settings
from stockrl.trading.virtual_account_orders import handlers
from stockrl.trading.virtual_account_orders.paper_account import PaperAccount


class ManualQuoteValidationTests(unittest.TestCase):
 def setUp(self):
  self.runtime=operations_runtime.OperationsRuntime()
  self.runtime.account=PaperAccount.in_memory(0,0)
  self.now=pd.Timestamp.now(tz='UTC').isoformat()

 def order(self,quote,action='BUY'):
  self.runtime.quotes['AAPL']=quote
  with patch.object(operations_runtime,'read_json',return_value={'instruments':[{'symbol':'AAPL','market':'US','asset_class':'equity'}]}),patch.dict(sys.modules,{'stockrl.live_feed':SimpleNamespace(LIVE_QUOTE_MAX_AGE_SECONDS=300)}):
   return self.runtime.manual_order('AAPL','USD',action,1)

 def test_invalid_quotes_are_rejected_without_changing_account(self):
  invalid=[{'date':'NaT','close':100},{'date':None,'close':100},
           *[{'date':self.now,'close':price} for price in (0,-1,None,float('nan'),float('inf'))],
           *[{'date':self.now,'close':100,'bid':bid,'ask':ask} for bid,ask in ((101,99),(0,100),(float('nan'),100),(99,float('inf')),('bad',100))]]
  before=copy.deepcopy(self.runtime.account.state)
  for quote in invalid:
   with self.subTest(quote=quote):
    with self.assertRaises(ValueError):self.order(quote)
    self.assertEqual(self.runtime.account.state,before)

 def test_valid_buy_and_sell_keep_the_existing_execution_rule(self):
  quote={'date':self.now,'close':100,'bid':99.9,'ask':100.1}
  bought=self.order(quote)
  self.assertEqual(bought['fill']['quantity'],1)
  self.assertEqual(bought['price_source'],'live')
  self.assertGreaterEqual(bought['fill']['price'],100)
  sold=self.order(quote,'SELL')
  self.assertEqual(sold['fill']['quantity'],1)
  self.assertLessEqual(sold['fill']['price'],100)
  self.assertEqual(len(self.runtime.account.state['fills']),2)


class UnifiedOrderRequestTests(unittest.TestCase):
 def test_invalid_quantity_never_reaches_runtime(self):
  app=FastAPI();app.include_router(handlers.router)
  runtime=SimpleNamespace(manual_order=Mock(return_value={'fill':{'quantity':1},'price_source':'live'}))
  with patch.object(handlers,'runtime',runtime),TestClient(app) as client:
   for quantity in (True,False,0,-1,1.5,'1'):
    with self.subTest(quantity=quantity):
     response=client.post('/api/orders',json={'currency':'USD','symbol':'AAPL','action':'BUY','quantity':quantity})
     self.assertEqual(response.status_code,422)
   runtime.manual_order.assert_not_called()
   response=client.post('/api/orders',json={'currency':'USD','symbol':'AAPL','action':'BUY','quantity':1})
   self.assertEqual(response.status_code,200)
   runtime.manual_order.assert_called_once_with('AAPL','USD','BUY',1)

 def test_invalid_quote_reason_remains_a_command_error(self):
  app=FastAPI();app.include_router(handlers.router)
  runtime=SimpleNamespace(manual_order=Mock(side_effect=ValueError('유효한 시세 가격이 없습니다.')))
  with patch.object(handlers,'runtime',runtime),TestClient(app) as client:
   response=client.post('/api/orders',json={'currency':'USD','symbol':'AAPL','action':'BUY','quantity':1})
   self.assertEqual(response.status_code,400)
   self.assertEqual(response.json()['detail'],'유효한 시세 가격이 없습니다.')


class OperationInputTests(unittest.TestCase):
 def test_invalid_currency_inputs_cannot_launch_the_system(self):
  app=FastAPI();app.include_router(control_handlers.router)
  system=SimpleNamespace(start=Mock(return_value={'status':'pending'}))
  with patch.object(control_handlers,'system',system),TestClient(app) as client:
   for currencies in (1,True,['USD',{}],['EUR'],[],None,'USD'):
    with self.subTest(currencies=currencies):
     response=client.post('/api/system/start',json={'currencies':currencies})
     self.assertEqual(response.status_code,400)
   system.start.assert_not_called()
   response=client.post('/api/system/start',json={'currencies':['USD','KRW','USD']})
   self.assertEqual(response.status_code,200)
   system.start.assert_called_once_with(['USD','KRW'])

 def test_invalid_settings_do_not_replace_existing_values(self):
  with tempfile.TemporaryDirectory() as temporary,patch.object(operations_settings,'CONFIG_PATH',Path(temporary)/'settings.json'):
   operations_settings.update({'symbols':['AAPL'],'expert_devices':{'chronos':'cuda'}})
   original=operations_settings.CONFIG_PATH.read_bytes()
   for values in ({'symbols':'AAPL'},{'symbols':[None]},{'symbols':['']},{'expert_devices':{'chronos':7}},{'expert_devices':{'chronos':''}}):
    with self.subTest(values=values):
     with self.assertRaises(ValueError):operations_settings.update(values)
     self.assertEqual(operations_settings.CONFIG_PATH.read_bytes(),original)


if __name__=='__main__':unittest.main()
