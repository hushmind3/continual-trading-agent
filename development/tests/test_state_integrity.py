import json
import tempfile
import threading
import unittest
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
import pandas as pd
from stockrl import ROOT
from stockrl.trading.virtual_account_orders.paper_account import PaperAccount
from stockrl.expert_observation import ExpertObservation
from stockrl.trading.operation_control.operations_runtime import OperationsRuntime
from stockrl.trading.operation_control import operations_settings
from stockrl.market_storage import AppendOnlyMarketCSV
def panel(symbol,date,price=100):
 return SimpleNamespace(dates=[date],symbols=[symbol],groups={symbol:('US','equity')},observed=np.ones((1,1),bool),closes=np.array([[price]]),features=np.zeros((1,1,8)))
def row(symbol,date,price=100):
 return dict(symbol=symbol,date=date,market='US',asset_class='equity',open=price,high=price,low=price,close=price,volume=1)
class IntegrityTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  (ROOT/'runtime').mkdir(parents=True,exist_ok=True)
 def test_same_time_different_symbols_and_duplicate(self):
  ledger=PaperAccount.in_memory(0,0)
  for symbol in ('AAPL','MSFT'):ledger.state['pending'][symbol]={'date':'2026-01-01','action':'BUY','budget':100,'requested_quantity':1}
  self.assertEqual(len(ledger.process_bar(panel('AAPL','2026-01-02'),0,True)),1)
  self.assertEqual(len(ledger.process_bar(panel('MSFT','2026-01-02'),0,True)),1)
  self.assertEqual(ledger.process_bar(panel('AAPL','2026-01-02T00:00:00Z'),0,True),[])
  self.assertEqual(ledger.state['books']['USD']['trade_count'],2)
 def test_late_other_symbol_and_older_same_symbol(self):
  ledger=PaperAccount.in_memory(0,0)
  ledger.process_bar(panel('AAPL','2026-01-03',100),0,False)
  ledger.process_bar(panel('MSFT','2026-01-02',200),0,False)
  ledger.process_bar(panel('AAPL','2026-01-02',80),0,False)
  self.assertEqual(ledger.state['books']['USD']['marks'],{'AAPL':100.,'MSFT':200.})
 def observation(self,seed,currency):
  frame=pd.DataFrame([row('AAPL','2026-01-01'),row('MSFT','2026-01-01')]);frame['date']=pd.to_datetime(frame.date)
  raw=SimpleNamespace(_info={'end_time':'2026-01-01'},_portfolio_value=1000000,_final_weights=[np.array([1.,0.,0.])],_initial_amount=1000000)
  subject=SimpleNamespace(structure_only=False,unwrapped=SimpleNamespace(gym_env=raw),frame=frame,symbols=['AAPL','MSFT'],assets=[],currency=currency,champion_ids=[],registry=SimpleNamespace(outputs=lambda *args,**kwargs:np.empty(0)),
   live_account={'currency':currency,'initial_cash':seed,'nav':seed,'cash':seed*.7,'positions':{'AAPL':seed*.3/100},'marks':{'AAPL':100},'equity_history':[{'nav':seed}]})
  return ExpertObservation.observation(subject,np.zeros(6))[-16:]
 def test_equal_relative_accounts_have_equal_features(self):
  np.testing.assert_allclose(self.observation(10000,'USD'),self.observation(10000000,'KRW'),rtol=1e-6)
 def test_live_holdings_replace_environment_weights(self):
  features=self.observation(10000,'USD')
  self.assertAlmostEqual(features[0],1);self.assertAlmostEqual(features[1],.7,places=6)
  self.assertAlmostEqual(features[5],.3,places=6);self.assertAlmostEqual(features[13],.5)
 def test_signal_cannot_fill_its_observation_bar(self):
  ledger=PaperAccount.in_memory(0,0)
  ledger.state['pending']['AAPL']={'date':'2026-01-02','action':'BUY','budget':100,'requested_quantity':1}
  self.assertEqual(ledger.process_bar(panel('AAPL','2026-01-02'),0,True),[])
  self.assertEqual(len(ledger.process_bar(panel('AAPL','2026-01-03'),0,True)),1)
 def test_invalid_settings_do_not_write(self):
  with tempfile.TemporaryDirectory() as directory,patch.object(operations_settings,'CONFIG_PATH',Path(directory)/'config.json'):
   for values in ({'risk':{'fee':-1}},{'risk':{'slippage':float('nan')}},{'data':{'poll_seconds':0}},{'data':{'timeout_seconds':-1}},{'risk':{'fee':None}}):
    with self.assertRaises(ValueError):operations_settings.update(values)
   self.assertFalse(operations_settings.CONFIG_PATH.exists())
 def test_partial_settings_preserve_other_values(self):
  with tempfile.TemporaryDirectory() as directory,patch.object(operations_settings,'CONFIG_PATH',Path(directory)/'config.json'):
   operations_settings.update({'risk':{'fee':.001,'slippage':.01}})
   self.assertEqual(operations_settings.update({'risk':{'fee':.002}})['risk']['slippage'],.01)
 def test_saved_rows_are_unique_and_not_daily_published(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'runtime') as directory:
   writer=AppendOnlyMarketCSV.__new__(AppendOnlyMarketCSV)
   writer.path=Path(directory)/'market.csv';writer.raw_path=Path(directory)/'timeframes.sqlite3'
   import sqlite3
   with closing(sqlite3.connect(writer.raw_path)) as db,db:db.execute('CREATE TABLE received_bars(symbol TEXT,stamp_ns INTEGER,PRIMARY KEY(symbol,stamp_ns))')
   writer._save_prices=lambda frame:self.fail('Raw bars must not enter daily data')
   self.assertEqual(writer.append([row('AAPL','2026-01-01')]),1)
   self.assertEqual(writer.append([row('AAPL','2026-01-01'),row('MSFT','2026-01-01')]),1)
   self.assertEqual([item['symbol'] for item in writer.last_added_rows],['MSFT'])
 def test_slow_or_failed_policy_does_not_block_accept(self):
  runtime=OperationsRuntime();runtime.account=PaperAccount.in_memory(0,0);runtime.controls.update(feed=True,engine=True)
  entered=threading.Event();release=threading.Event()
  def slow():entered.set();release.wait(3);raise RuntimeError('expected inference failure')
  runtime.sac_decision=slow
  worker=threading.Thread(target=runtime.process_updates);worker.start();runtime.feed_cycle.set()
  self.assertTrue(entered.wait(1))
  accepted=threading.Event()
  consumer=threading.Thread(target=lambda:(runtime.accept([row('AAPL','2026-01-02')]),accepted.set()));consumer.start()
  try:self.assertTrue(accepted.wait(1))
  finally:runtime.controls['feed']=False;release.set();runtime.feed_cycle.set();consumer.join(3);worker.join(3)
  self.assertEqual(runtime.account.state['books']['USD']['marks']['AAPL'],100)
 def test_runtime_quotes_do_not_move_backwards(self):
  runtime=OperationsRuntime();runtime.account=PaperAccount.in_memory(0,0)
  runtime.accept([row('AAPL','2026-01-03',100)]);runtime.accept([row('AAPL','2026-01-02',80)])
  self.assertEqual(runtime.quotes['AAPL']['close'],100)
 def test_mixed_provider_quotes_keep_missing_fields_json_safe(self):
  runtime=OperationsRuntime();runtime.account=PaperAccount.in_memory(0,0)
  first=row('AAPL','2026-01-03');second={**row('MSFT','2026-01-03'), 'bid':99.,'ask':101.,'trade_count':2}
  runtime.accept([first,second])
  self.assertIsNone(runtime.quotes['AAPL']['bid'])
  self.assertIsNone(runtime.quotes['AAPL']['trade_count'])
  json.dumps(runtime.quotes,allow_nan=False)
 def test_deleted_champion_clears_file_caches_without_hiding_other_errors(self):
  from stockrl.platform.system_operations import SystemOperations
  cache=SystemOperations.__new__(SystemOperations);cache.state_lock=threading.RLock();cache.state_revision=0
  with tempfile.TemporaryDirectory() as directory:
   present=Path(directory)/'present.pt';present.touch()
   kept='champion:'+str(present);removed='champion:'+str(Path(directory)/'deleted.pt')
   for name in ('states','state_signatures','state_errors','state_updates'):
    setattr(cache,name,{kept:'invalid existing file',removed:'deleted file','import:other':'other error'})
   cache.prune_missing_file_states('champion:')
   for name in ('states','state_signatures','state_errors','state_updates'):
    self.assertNotIn(removed,getattr(cache,name));self.assertIn(kept,getattr(cache,name));self.assertIn('import:other',getattr(cache,name))
   self.assertEqual(cache.state_revision,1)
   cache.prune_missing_file_states('champion:');self.assertEqual(cache.state_revision,1)
   present.unlink();cache.prune_missing_file_states('champion:')
   self.assertNotIn(kept,cache.state_errors);self.assertEqual(cache.state_revision,2)
 def test_broker_worker_events_preserve_existing_collector_contract(self):
  import queue
  from stockrl.platform.kiwoom_data import BrokerStreams
  collector=SimpleNamespace(broker_stop=threading.Event(),broker_rows=queue.Queue(),broker_status={},latest_quotes={},broker_symbols=set())
  streams=BrokerStreams(collector)
  sample=row('AAPL','2026-01-03')
  streams._event({'kind':'bar','value':sample})
  self.assertEqual(collector.broker_rows.get_nowait(),sample)
  streams._event({'kind':'quote','value':{'symbol':'AAPL','quote':{'price':100,'date':'2026-01-03'}}})
  self.assertEqual(collector.latest_quotes['AAPL']['price'],100)
  streams._event({'kind':'status','value':{'connected':True,'us_connected':True}})
  streams._event({'kind':'symbols','value':['AAPL']})
  self.assertTrue(collector.broker_status['connected']);self.assertEqual(collector.broker_symbols,{'AAPL'})
 def test_daily_read_excludes_intraday_rows(self):
  import sqlite3
  from stockrl.finrl_trading import data as framework
  with tempfile.TemporaryDirectory(dir=ROOT/'runtime') as directory:
   root=Path(directory);(root/'configs').mkdir();(root/'configs/instruments.json').write_text(json.dumps({'instruments':[{'symbol':'AAPL','market':'US','asset_class':'equity'}]}),encoding='utf8')
   dbpath=root/'prices.sqlite3'
   with closing(sqlite3.connect(dbpath)) as db,db:
    db.execute('CREATE TABLE price_data(ticker TEXT,date TEXT)')
    db.executemany('INSERT INTO price_data VALUES (?,?)',[('AAPL','2026-01-01'),('AAPL','2026-01-01T10:00:00')])
   feed=root/'runtime/operations/live/timeframes.sqlite3';feed.parent.mkdir(parents=True)
   with closing(sqlite3.connect(feed)) as db,db:
    db.execute('CREATE TABLE received_bars(symbol TEXT,stamp_ns INTEGER)')
    db.execute('INSERT INTO received_bars VALUES (?,?)',('AAPL',pd.Timestamp('2026-01-01T10:00:00Z').value))
    db.execute('CREATE TABLE daily_bars(symbol TEXT,stamp_ns INTEGER,open REAL,high REAL,low REAL,close REAL,volume REAL)')
    db.execute('INSERT INTO daily_bars VALUES (?,?,?,?,?,?,?)',('AAPL',pd.Timestamp('2026-01-01T00:00:00Z').value,100,100,100,100,1))
   frame=pd.DataFrame([{'tic':'AAPL','datadate':'2026-01-01','prcod':100,'prchd':100,'prcld':100,'prccd':100,'cshtrd':1},{'tic':'AAPL','datadate':'2026-01-01T10:00:00','prcod':900,'prchd':900,'prcld':900,'prccd':900,'cshtrd':1}])
   store=SimpleNamespace(db_path=dbpath,get_price_data=lambda *args:frame.copy())
   with patch.object(framework,'ROOT',root),patch.object(framework,'finrlx',lambda name:SimpleNamespace(DataStore=lambda:store)):
    actual=framework.prices('USD',['AAPL'])
   self.assertEqual(actual.close.tolist(),[100]);self.assertEqual(actual.attrs['timeframe'],'1d')
 def test_unchanged_daily_data_does_not_repeat_learning(self):
  import sys
  from stockrl.trading.operation_control import operations_runtime
  from stockrl.finrl import framework
  runtime=OperationsRuntime();runtime.controls['learning']=True
  frame=pd.DataFrame([row('AAPL','2026-01-01')]);launched=[]
  def launch(*args,**kwargs):launched.append(args);return {'job':{'id':str(len(launched))}}
  api=SimpleNamespace(RunRequest=lambda **kwargs:SimpleNamespace(**kwargs),launch=launch)
  identity={'symbols':['AAPL'],'currency':'USD','algorithm':'sac'}
  def read(path):return {'USD':'policies/x/sac.zip'} if path.name=='policies.json' else identity
  with patch.dict(sys.modules,{'stockrl.finrl.policy_learning.handlers':api}),patch.object(operations_runtime,'read_json',read),patch.object(operations_runtime,'prices',return_value=frame) as prices,patch.object(framework,'policy_files',return_value=ROOT/'runtime/official/policies/x'),patch.object(operations_runtime.system,'job_state',return_value={'running':False}):
   runtime.queue_learning(['AAPL']);runtime.queue_learning(['AAPL'])
   self.assertEqual(len(launched),1)
   prices.return_value=frame.assign(close=101)
   runtime.queue_learning(['AAPL']);self.assertEqual(len(launched),2)
 def test_old_manual_quote_is_rejected(self):
  import sys
  from stockrl.trading.operation_control import operations_runtime
  runtime=OperationsRuntime();runtime.account=PaperAccount.in_memory(0,0);runtime.quotes['AAPL']=row('AAPL','2000-01-01')
  with patch.dict(sys.modules,{'stockrl.live_feed':SimpleNamespace(LIVE_QUOTE_MAX_AGE_SECONDS=300)}),patch.object(operations_runtime,'read_json',return_value={'instruments':[{'symbol':'AAPL','market':'US','asset_class':'equity'}]}):
   with self.assertRaisesRegex(ValueError,'최신 시세'):runtime.manual_order('AAPL','USD','BUY',1)
  self.assertEqual(runtime.account.state['fills'],[])
 def test_learning_input_error_does_not_kill_worker(self):
  runtime=OperationsRuntime();runtime.controls.update(feed=True,learning=True)
  attempted=threading.Event()
  def fail(symbols):attempted.set();raise ValueError('ambiguous daily input')
  runtime.queue_learning=fail
  worker=threading.Thread(target=runtime.process_updates);worker.start();runtime.feed_cycle.set()
  try:
   self.assertTrue(attempted.wait(1));self.assertTrue(worker.is_alive())
  finally:runtime.controls['feed']=False;runtime.feed_cycle.set();worker.join(3)
  self.assertEqual(runtime.status.get('learning_error'),'ambiguous daily input')
 def test_stock_expert_uses_latest_complete_past_session(self):
  from stockrl.platform.expert_inference import complete_policy_day
  history=pd.DataFrame({'Date':pd.to_datetime(['2026-10-07','2026-10-07','2026-10-08']),'Ticker':['AAPL','META','AAPL'],'Close':[100,200,110]})
  actual=complete_policy_day(history,['AAPL','META'])
  self.assertEqual(actual.Date.unique().tolist(),[pd.Timestamp('2026-10-07')])
  self.assertEqual(actual.Close.tolist(),[100,200])
  with self.assertRaisesRegex(ValueError,'실제 과거 일봉'):
   complete_policy_day(history,['AAPL','META','T'])
 def test_trading_menu_and_dedicated_actions_are_removed(self):
  from menu_registry import GROUPS
  from stockrl.platform.framework_operations import ACTIONS
  self.assertEqual(set(ACTIONS),{'native_call'})
  self.assertEqual([group['id'] for group in GROUPS],['finance','rea'])
 def test_rea_refuses_project_trash_inputs(self):
  from rea.program_analysis.operations import validate_arguments
  with self.assertRaisesRegex(ValueError,'휴지통'):
   validate_arguments({'arguments':{'input_path':str(ROOT/'휴지통/sample')}})
  validate_arguments({'input_path':str(ROOT/'frontend/src')})
 def test_rea_timeout_closes_the_session(self):
  import io,queue
  from rea.program_analysis.operations import REAConnection
  connection=REAConnection();connection.process=SimpleNamespace(poll=lambda:None,stdin=io.StringIO());connection.responses=queue.Queue()
  with patch.object(connection,'close') as close:
   with self.assertRaisesRegex(RuntimeError,'응답 시간이 초과'):
    connection.request({'operation':'tools'},timeout=.001)
   close.assert_called_once()

class REAProjectStorageTests(unittest.TestCase):
 def test_project_reader_cannot_leave_saved_folder(self):
  from rea.project_explorer.projects import _inside
  with self.assertRaisesRegex(ValueError,'프로젝트 내부'):
   _inside(ROOT/'backend/rea/project_explorer/saved_projects/example','../../../configs/experts.json')
 def test_folder_snapshot_does_not_copy_generated_output_into_itself(self):
  import tempfile
  from unittest.mock import patch
  from rea.program_analysis import extract
  with tempfile.TemporaryDirectory() as temporary:
   source=Path(temporary);(source/'app.js').write_text('export const value=7;',encoding='utf8')
   output=source/'backend/rea/project_explorer/saved_projects';destination=output/'test/original/source'
   with patch.object(extract,'OUTPUT',output):
    extract._copy_directory(source,destination)
   self.assertEqual((destination/'app.js').read_text(encoding='utf8'),'export const value=7;')
   self.assertFalse((destination/'backend/rea/project_explorer/saved_projects').exists())

class FrameworkFailureAttributionTests(unittest.TestCase):
 def test_failed_native_call_uses_requested_module_and_function(self):
  from stockrl.job_worker import framework_failure_record
  job={'id':'requested','action':'native_call','parameters':{'module':'FinRL:a','callable':'load'}}
  record=framework_failure_record(job,ValueError('failed'),{'module':'FinRL:b','function':'other'})
  self.assertEqual(record['request_target'],{'module':'FinRL:a','function':'load'})
  self.assertEqual(record['module'],'FinRL:a')
  self.assertEqual(record['function'],'load')
  self.assertEqual(record['status'],'failed')

 def test_success_for_another_module_does_not_clear_failure(self):
  from stockrl.platform.framework_operations import execution_records
  import os
  with tempfile.TemporaryDirectory() as temporary:
   directory=Path(temporary)
   records=[{'error':'unattributed','module':None},
            {'error':'target failed','request_target':{'module':'FinRL:a','function':'load'}},
            {'module':'FinRL:b','function':'run','executed_functions':{'FinRL:b':[None,'run']}}]
   for index,record in enumerate(records):
    path=directory/str(index)/'result.json';path.parent.mkdir()
    path.write_text(json.dumps(record),encoding='utf8');os.utime(path,(index+1,index+1))
   verified,failed,unknown=execution_records(directory,{'FinRL:a','FinRL:b'})
   self.assertEqual(failed['FinRL:a']['function'],'load')
   self.assertNotIn(None,failed)
   self.assertEqual(verified,{'FinRL:b':['run','run']})
   self.assertEqual(len(unknown),1)
   path=directory/'success'/'result.json';path.parent.mkdir()
   path.write_text(json.dumps({'module':'FinRL:a','function':'load'}),encoding='utf8')
   _,failed,unknown=execution_records(directory,{'FinRL:a','FinRL:b'})
   self.assertNotIn('FinRL:a',failed)
   self.assertEqual(len(unknown),1)

if __name__=='__main__':unittest.main()
