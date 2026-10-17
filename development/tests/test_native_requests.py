"""Native execution and gateway contracts with harmless fixtures and fake vaults."""
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
from fastapi.testclient import TestClient
from fastapi import FastAPI
from stockrl.platform import framework_operations as framework
from stockrl.finrl.provider_settings import operations as providers
from stockrl.management.all_backend_features import handlers


def fixture():
 def field(name,annotation='int'):return {'name':name,'annotation':annotation,'required':True}
 return {'id':'FinRL:fixture','path':'fixture.py','framework':'FinRL',
         'functions':['combine','Counter','Counter.add'],
         'parameters':{'combine':[field('value','str')],'Counter.__init__':[field('base')],'Counter.add':[field('value')]},
         'keyword_contracts':{'Counter.add':{'instance':True,'variadic':False,'positional_only':[]}}}


class NativeExecutionTests(unittest.TestCase):
 def test_installed_finrl_function_uses_local_csv_without_models(self):
  import pandas as pd
  with tempfile.TemporaryDirectory(dir=framework.ROOT/'runtime') as temporary:
   root=Path(temporary);source=root/'source.csv'
   pd.DataFrame([{'date':'2026-01-01','tic':'AAPL','close':100},{'date':'2026-01-02','tic':'AAPL','close':101},{'date':'2026-01-03','tic':'AAPL','close':102}]).to_csv(source,index=False)
   result=framework.native_call({'module':'FinRL:meta.preprocessor.preprocessors','callable':'data_split','kwargs':{'df':'$data','start':'2026-01-01','end':'2026-01-03'},'source':str(source),'symbols':['AAPL'],'currency':'USD'},root)
   self.assertEqual(result['value']['total_rows'],2)
   self.assertEqual([row['date'] for row in result['value']['rows']],['2026-01-01','2026-01-02'])

 def test_real_callable_preserves_strings_and_restores_cli_arguments(self):
  item=fixture();original=sys.argv
  module=SimpleNamespace(combine=lambda value:{'value':value,'argv':sys.argv[1:]})
  with tempfile.TemporaryDirectory(dir=framework.ROOT/'runtime') as directory,patch.object(framework,'source_catalog',return_value=[item]),patch.object(framework,'finrl_file',return_value=module):
   result=framework.native_call({'module':item['id'],'callable':'combine','kwargs':{'value':'{"literal":7}'},'argv':['--fixture']},Path(directory))
   self.assertEqual(result['value'],{'value':'{"literal":7}','argv':['--fixture']})
   self.assertIs(sys.argv,original)

 def test_method_chain_normalizes_json_arguments_and_reuses_result(self):
  class Counter:
   def __init__(self,base):self.base=base
   def add(self,value):self.base+=value;return self.base
  item=fixture()
  with tempfile.TemporaryDirectory(dir=framework.ROOT/'runtime') as directory,patch.object(framework,'source_catalog',return_value=[item]),patch.object(framework,'finrl_file',return_value=SimpleNamespace(Counter=Counter)):
   result=framework.native_call({'module':item['id'],'callable':'Counter.add','init_kwargs':{'base':2},'steps':[{'method':'add','kwargs':'{"value":3}','save_as':'first'},{'method':'add','kwargs':{'value':'$first'}}]},Path(directory))
   self.assertEqual(result['value'],10)

 def test_invalid_cli_arguments_are_rejected_before_module_loading(self):
  item=fixture()
  with patch.object(framework,'source_catalog',return_value=[item]),patch.object(framework,'finrl_file') as load:
   with self.assertRaisesRegex(ValueError,'문자열 JSON 배열'):
    framework.native_call({'module':item['id'],'callable':'combine','kwargs':{'value':'x'},'argv':[7]},framework.ROOT/'runtime')
   load.assert_not_called()

 def test_module_router_queues_valid_native_request_and_keeps_invalid_one_out(self):
  app=FastAPI();app.include_router(handlers.router)
  item=fixture();start=Mock(return_value={'id':'fixture','running':False})
  with patch.object(framework,'source_catalog',return_value=[item]),patch.object(handlers.system,'start_job',start),patch.object(handlers.system,'job_state',return_value={'running':False}),TestClient(app) as client:
   payload={'module':item['id'],'callable':'combine','kwargs':{'value':'fixture'}}
   rejected=client.post('/api/framework/native_call',json={**payload,'argv':[7]})
   self.assertEqual(rejected.status_code,400);start.assert_not_called()
   accepted=client.post('/api/framework/native_call',json=payload)
   self.assertEqual(accepted.status_code,200);start.assert_called_once()


class ProviderSaveTests(unittest.TestCase):
 def test_provider_name_survives_module_dispatch(self):
  app=FastAPI();app.include_router(handlers.router)
  with patch.object(providers,'save_provider',return_value={'items':[]}) as save,TestClient(app) as client:
   response=client.post('/api/framework/providers/FMP',json={'FMP_API_KEY':'fake-not-saved'})
   self.assertEqual(response.status_code,200)
   save.assert_called_once_with('FMP',{'FMP_API_KEY':'fake-not-saved'})

 def test_bad_provider_field_cannot_partially_change_credentials(self):
  with patch('stockrl.management.connection_settings.provider_credentials._vault') as vault:
   with self.assertRaises(ValueError):providers.save_provider('FMP',{'FMP_API_KEY':'fake-not-saved','UNKNOWN':'reject'})
   vault.assert_not_called()


class GatewayAndMenuContractTests(unittest.TestCase):
 def test_malformed_envelopes_and_internal_paths_are_rejected(self):
  from web_api import app
  with TestClient(app) as client:
   for body in ([],None,{'operation':'state','payload':[]},{'operation':7,'payload':{}},{'payload':{}}):
    with self.subTest(body=body):
     response=client.post('/api',content=__import__('json').dumps(body),headers={'Content-Type':'application/json'})
     self.assertEqual(response.status_code,400)
   self.assertEqual(client.post('/api/orders',json={}).status_code,404)
   self.assertEqual(client.get('/api',params={'operation':'orders','payload':'{}'}).status_code,404)
   self.assertEqual(client.get('/api',params={'operation':'state','payload':'[]'}).status_code,400)

 def test_every_command_belongs_to_a_current_menu(self):
  from menu_registry import catalog
  from api_context import private_api
  current=catalog(private_api.routes)
  ids={menu['id'] for group in current['groups'] for menu in group['menus']}
  self.assertEqual([(row['operation'],row['menu']) for row in current['commands'] if row['menu'] not in ids],[])
