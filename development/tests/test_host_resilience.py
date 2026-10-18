"""Host isolation and restart rollback without business workers or model execution."""
import importlib.util
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch
from fastapi import APIRouter,FastAPI
from fastapi.testclient import TestClient

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))

def load(filename,stub=None):
 spec=importlib.util.spec_from_file_location('isolated_'+filename,ROOT/'backend'/(filename+'.py'))
 module=importlib.util.module_from_spec(spec)
 with patch.dict(sys.modules,{'platform_modules':stub} if stub else {}):spec.loader.exec_module(module)
 return module

def entry(key,**hooks):
 return ({'id':key,'group':{'id':key,'title':key}},SimpleNamespace(MENU={'id':key,'operations':[]},**hooks))

class HostResilienceTests(unittest.TestCase):
 def setUp(self):
  base=ROOT/'runtime/platform/verification';base.mkdir(parents=True,exist_ok=True)
  self.temp=tempfile.TemporaryDirectory(dir=base)
  self.entries=[]
  self.stub=SimpleNamespace(ROOT=Path(self.temp.name),registrations=lambda:self.entries,busy_reasons=lambda:[],lifecycle=lambda method:None,signature=lambda:'fixture')
 def tearDown(self):self.temp.cleanup()
 def client(self):
  context=load('platform_context',self.stub);router=APIRouter()
  with patch.dict(sys.modules,{'platform_modules':self.stub}):context.register_controls(router)
  app=FastAPI();app.include_router(router)
  return context,TestClient(app,raise_server_exceptions=False)
 def test_catalog_keeps_healthy_module_when_another_module_is_reserved(self):
  action={'id':'healthy_action','name':'Healthy','fields':[]}
  self.entries[:]=[entry('broken',actions=Mock(side_effect=RuntimeError('module reserved'))),entry('healthy',actions=lambda:[action])]
  catalog=load('menu_registry',self.stub).catalog([])
  self.assertEqual([item['id'] for item in catalog['actions']],['healthy_action'])
  self.assertIn('module reserved',catalog['module_errors']['broken'])
  self.assertNotIn('group',action)
 def test_state_merges_each_modules_views_and_errors(self):
  self.entries[:]=[entry('one',snapshot=lambda *args:{'views':{'one':{'data':1}},'module_errors':{'existing':'old'}}),entry('two',snapshot=lambda *args:{'views':{'two':{'data':2}}})]
  context,client=self.client();response=client.get('/api/state')
  self.assertEqual(response.status_code,200)
  self.assertEqual(set(response.json()['views']),{'one','two'})
  self.assertEqual(response.json()['module_errors']['existing'],'old')
 def test_unexpected_snapshot_error_preserves_other_state_and_cached_view(self):
  callback=Mock(side_effect=[{'views':{'cached':{'data':'last good'}}},ValueError('plugin invalid')])
  self.entries[:]=[entry('bad',snapshot=callback),entry('good',snapshot=lambda *args:{'views':{'good':{'data':1}}})]
  context,client=self.client();self.assertEqual(client.get('/api/state').status_code,200)
  response=client.get('/api/state');self.assertEqual(response.status_code,200)
  self.assertIn('cached',response.json()['views']);self.assertIn('good',response.json()['views'])
  self.assertIn('plugin invalid',response.json()['module_errors']['bad'])
 def test_catalog_failures_are_visible_in_host_state(self):
  context,client=self.client()
  catalog=SimpleNamespace(catalog=lambda routes:{'groups':[],'actions':[],'commands':[],'module_errors':{'bad':'reserved'}})
  with patch.dict(sys.modules,{'menu_registry':catalog}):response=client.get('/api/state',params={'views':'["menu_catalog"]'})
  self.assertEqual(response.status_code,200)
  self.assertEqual(response.json()['module_errors']['bad'],'reserved')
 def test_busy_hook_failure_blocks_restart_without_losing_other_jobs(self):
  modules=load('platform_modules')
  with patch.object(modules,'registrations',return_value=[entry('broken',busy_reason=Mock(side_effect=ValueError('unavailable'))),entry('good',busy_reason=lambda:'active job')]):
   reasons=modules.busy_reasons()
  self.assertTrue(any('broken' in item and 'unavailable' in item for item in reasons));self.assertIn('active job',reasons)
 def test_failed_rollback_does_not_prevent_other_reservations_from_cancelling(self):
  modules=load('platform_modules');first=Mock();second=Mock(side_effect=RuntimeError('rollback failed'))
  entries=[entry('first',reserve_restart=Mock(),cancel_restart=first),entry('second',reserve_restart=Mock(),cancel_restart=second),entry('third',reserve_restart=Mock(side_effect=ValueError('original reservation failure')))]
  with patch.object(modules,'registrations',return_value=entries),self.assertRaisesRegex(ValueError,'original reservation failure'):modules.lifecycle('reserve_restart')
  first.assert_called_once();second.assert_called_once()
 def test_close_failure_releases_restart_reservations(self):
  cancelled=Mock();self.entries[:]=[entry('one',cancel_restart=cancelled)]
  context,client=self.client()
  def lifecycle(method):
   if method=='close':raise RuntimeError('close failed')
  self.stub.lifecycle=lifecycle
  # register_controls keeps the callback selected when routes are registered.
  context,client=self.client();response=client.post('/api/system/prepare-restart')
  self.assertEqual(response.status_code,409);self.assertIn('close failed',response.text)
  self.assertFalse(context.system.restarting);cancelled.assert_called_once()
 def test_cleanup_notification_reaches_all_modules_after_unexpected_error(self):
  callback=Mock();self.entries[:]=[entry('bad',cancel_restart=Mock(side_effect=TypeError('bad hook'))),entry('good',cancel_restart=callback)]
  context=load('platform_context',self.stub);context.system.notify('cancel_restart');callback.assert_called_once()

if __name__=='__main__':unittest.main()
