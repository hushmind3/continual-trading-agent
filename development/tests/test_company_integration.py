"""Real original company DB/ASGI with native records adapter; no model fixture claims."""
import asyncio,importlib,importlib.util,json,os,shutil,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
RECORDS=list((ROOT/'runtime/projects/manage/registry').glob('*project-zero*.json'))
@unittest.skipUnless(RECORDS,'Original company contract app is not installed')
class CompanyTests(unittest.IsolatedAsyncioTestCase):
 def setUp(self):
  source=Path(json.loads(RECORDS[0].read_text(encoding='utf-8'))['active_source'])
  checks=ROOT/'runtime/projects/manage/verification';checks.mkdir(parents=True,exist_ok=True)
  self.temp=tempfile.TemporaryDirectory(prefix='native-records-',dir=checks);self.addCleanup(self.temp.cleanup)
  self.base=Path(self.temp.name);copied=self.base/'source';copied.mkdir();names=[]
  for file in source.glob('*.py'):shutil.copyfile(file,copied/file.name);names.append(file.stem)
  previous={name:sys.modules.pop(name,None) for name in names}
  def restore():
   for name in names:
    sys.modules.pop(name,None)
    if previous[name] is not None:sys.modules[name]=previous[name]
  self.addCleanup(restore)
  env=patch.dict(os.environ,{'PROJECT_ZERO_DATA_DIR':str(self.base/'data'),'PROJECT_ZERO_ADMIN_TOKEN':'native-test-token'});env.start();self.addCleanup(env.stop)
  paths=patch.object(sys,'path',[str(copied),str(source/'.platform-runtime/python'),*sys.path]);paths.start();self.addCleanup(paths.stop)
  spec=importlib.util.spec_from_file_location('company_records_fixture',ROOT/'modules/projects/backend/integrations/company_records.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  self.server=importlib.import_module('server');module.install(self.server.app,self.base)
  self.db=importlib.import_module('database');self.db.initialize()
 async def call(self,command,status=200):
  import httpx
  async with httpx.AsyncClient(transport=httpx.ASGITransport(app=self.server.app),base_url='http://127.0.0.1') as client:
   response=await client.post('/api/admin/hermes/records',json=command,headers={'X-Project-Zero-Token':'native-test-token'})
  self.assertEqual(response.status_code,status,response.text);return response.json()
 async def test_dynamic_roles_owner_approval_and_no_automatic_pipeline(self):
  result=await self.call({'action':'propose','title':'Website','proposal':{'goal':'실제 홈페이지'}});v=result['venture_id']
  await self.call({'action':'begin','venture_id':v,'role':'CTO','title':'구현'},409)
  await self.call({'action':'decision','venture_id':v,'approve':True},409)
  await self.call({'action':'decision','venture_id':v,'approve':True,'_owner':True})
  self.assertEqual(self.db.many('SELECT * FROM jobs'),[])
  job=await self.call({'action':'begin','venture_id':v,'role':'CFO','title':'비용 확인'})
  repeated=await self.call({'action':'begin','venture_id':v,'role':'CFO','title':'비용 확인'})
  self.assertEqual(job['job_id'],repeated['job_id']);self.assertEqual(len(self.db.many('SELECT * FROM jobs')),1)
  self.assertTrue(Path(job['workspace']).is_relative_to(self.base/'workspaces'))
  await self.call({'action':'finish','job_id':job['job_id'],'body':'현재 검증 가능한 매출 0원'})
  self.assertEqual(self.db.one('SELECT status FROM jobs WHERE id=?',(job['job_id'],))['status'],'completed')
 async def test_direct_owner_task_and_failure_are_records_not_another_agent(self):
  job=await self.call({'action':'begin','role':'CTO','title':'대표가 지시한 홈페이지 제작'})
  await self.call({'action':'finish','job_id':job['job_id']},409)
  await self.call({'action':'finish','job_id':job['job_id'],'error':'실제 빌드 실패'})
  state=await self.call({'action':'overview'});self.assertEqual(state['jobs'][0]['status'],'failed')
  self.assertEqual(state['jobs'][0]['mode'],'hermes-native')
  await self.call({'action':'meeting','title':'구현 논의','minutes':[{'role':'CTO','opinion':'구현 먼저'}],'body':'합의: 홈페이지 제작 후 QA'})
  self.assertEqual(len((await self.call({'action':'overview'}))['meetings']),1)
  self.assertFalse(any(getattr(r,'path','').startswith('/api/admin/ceo/chat') for r in self.server.app.routes))
  with self.assertRaisesRegex(RuntimeError,'Hermes'):await importlib.import_module('ai_provider').compose('x','y')
  shutdown=asyncio.Event();task=asyncio.create_task(importlib.import_module('operations').worker_loop(shutdown));await asyncio.sleep(0)
  self.assertFalse(task.done());shutdown.set();await task
 async def test_records_keep_original_authentication(self):
  import httpx
  async with httpx.AsyncClient(transport=httpx.ASGITransport(app=self.server.app),base_url='http://127.0.0.1') as client:
   response=await client.post('/api/admin/hermes/records',json={'action':'overview'})
  self.assertEqual(response.status_code,401)
 async def test_native_run_failure_closes_its_unfinished_records(self):
  started=await self.call({'action':'run_start','body':'대표가 맡긴 홈페이지','_session':'native-session'})
  child=await self.call({'action':'begin','role':'CTO','title':'구현','_session':'native-session'})
  await self.call({'action':'run_finish','job_id':started['job_id'],'state':'stopped','_session':'another'},409)
  await self.call({'action':'run_finish','job_id':started['job_id'],'state':'stopped','_session':'native-session'})
  self.assertEqual(self.db.one('SELECT status FROM jobs WHERE id=?',(started['job_id'],))['status'],'failed')
  self.assertEqual(self.db.one('SELECT mode FROM jobs WHERE id=?',(child['job_id'],))['mode'],'incomplete')
 async def test_overview_summarizes_large_reports_without_deleting_them(self):
  job=await self.call({'action':'begin','role':'CTO','title':'긴 보고서'})
  await self.call({'action':'finish','job_id':job['job_id'],'body':'REPORT'*4000})
  data=await self.call({'action':'overview'})
  self.assertLessEqual(len(data['jobs'][0]['summary']),600)
  self.assertGreater(len(self.db.one('SELECT result FROM jobs WHERE id=?',(job['job_id'],))['result']),20000)
if __name__=='__main__':unittest.main()
