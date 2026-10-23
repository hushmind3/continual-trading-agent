"""Native company session routing, capability separation and adapter upgrades."""
import base64,hashlib,json,sys,tempfile,unittest,uuid
from pathlib import Path
from unittest.mock import patch,Mock
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
from platform_modules import mount_namespaces
mount_namespaces()
from platform_plugins.projects import conversation,workspaces
class ConversationTests(unittest.TestCase):
 def setUp(self):
  self.record={'id':'demo','name':'Demo','stage':'ready','workspace_ui':{'recipe':'company-v1','native':{'token':'secret'}},'harness':{'enabled':True}}
  self.calls=[];p=patch.object(conversation.store,'read',return_value=self.record);p.start();self.addCleanup(p.stop)
  p=patch.object(conversation.runtime,'invoke',side_effect=self.invoke);p.start();self.addCleanup(p.stop)
 def invoke(self,record,data,origin):
  self.calls.append(data);path=data['path']
  if path=='/api/local/session':value={'token':'app-token'}
  elif path=='/api/admin/ceo':value={'messages':[{'id':'old1','speaker':'owner','body':'원본 대화'}]}
  elif path=='/api/admin/control':value={'ventures':[{'id':'approved','status':'approved'}]}
  elif path=='/api/store/info':value={'published':False}
  else:value={'ok':True}
  return {'status':200,'body':base64.b64encode(json.dumps(value).encode()).decode()}
 def test_native_session_created_once_by_original_worker_and_original_history_imported(self):
  with tempfile.TemporaryDirectory() as d,patch.object(conversation.store,'project_folder',return_value=Path(d)),patch.object(conversation.store,'save'),patch('ai_agent.Hermes.engine.bridge.bridge') as bridge:
   bridge.call.return_value={'session_id':'native'}
   self.assertEqual(conversation.call('demo',{'action':'session'})['session_id'],'native')
   operation,payload=bridge.call.call_args.args;self.assertEqual(operation,'company/session');self.assertEqual(payload['messages'][0]['body'],'원본 대화');self.assertEqual(payload['token'],'secret')
   self.assertTrue(all(c['method']=='GET' for c in self.calls))
 def test_state_reads_business_records_never_calls_another_planner(self):
  result=conversation.call('demo',{});self.assertEqual(result['progress']['approved'],1)
  self.assertNotIn('messages',result);self.assertNotIn('token',json.dumps(result));self.assertNotIn('/api/admin/ceo',[c['path'] for c in self.calls])
  with self.assertRaisesRegex(ValueError,'영구 세션'):conversation.call('demo',{'action':'send','message':'hello'})
 def test_tools_cannot_approve_and_capability_does_not_leak(self):
  sid=uuid.uuid5(uuid.NAMESPACE_URL,'platform-company:demo').hex
  for token,command in [('wrong',{'action':'overview'}),('secret',{'action':'decision'}),('secret',{'action':'overview','_owner':True})]:
   with self.assertRaises(ValueError):conversation.call('demo',{'action':'tool','session_id':sid,'token':token,'command':command})
  conversation.call('demo',{'action':'tool','session_id':sid,'token':'secret','command':{'action':'overview'}})
  self.assertEqual(json.loads(self.calls[-1]['body']),{'action':'overview','_session':sid});self.assertEqual(self.calls[-1]['headers']['X-Project-Zero-Token'],'app-token')
 def test_owner_decision_is_json_and_does_not_run_legacy_queue(self):
  conversation.call('demo',{'action':'decision','venture_id':'venture_demo','approve':True})
  self.assertEqual(self.calls[-1]['path'],'/api/admin/hermes/records');self.assertEqual(json.loads(self.calls[-1]['body']),{'action':'decision','_owner':True,'venture_id':'venture_demo','approve':True})
 def test_removed_or_disconnected_apps_are_rejected(self):
  self.record['stage']='removed'
  with self.assertRaises(ValueError):conversation.call('demo',{})
  self.assertEqual(self.calls,[])
 def test_owned_adapter_upgrade_and_failed_save_rollback(self):
  with tempfile.TemporaryDirectory() as d,patch.object(workspaces.store,'project_folder',return_value=Path(d)):
   path=Path(d)/'workflow.py';old=b'# old owned adapter';path.write_bytes(old)
   self.record['workspace_ui'].update(adapter='workflow.py',adapter_sha256=hashlib.sha256(old).hexdigest())
   with patch.object(workspaces.store,'save',side_effect=OSError('save failed')),self.assertRaises(OSError):workspaces.adapter(self.record)
   self.assertEqual(path.read_bytes(),old)
   with patch.object(workspaces.store,'save'):workspaces.adapter(self.record)
   self.assertEqual(path.read_bytes(),(ROOT/'modules/projects/backend/integrations/company_records.py').read_bytes())
   path.write_text('# tampered',encoding='utf-8')
   with self.assertRaisesRegex(ValueError,'무결성'):workspaces.adapter(self.record)
if __name__=='__main__':unittest.main()
