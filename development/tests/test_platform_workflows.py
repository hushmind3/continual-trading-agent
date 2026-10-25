"""REA source/storage workflows using temporary fixtures, never model weights."""
import json
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from rea.program_analysis import extract
from rea.project_explorer import projects
from rea.program_analysis.handlers import router

def module_app():
 app=FastAPI();app.include_router(router);return app


class REAWorkflowTests(unittest.TestCase):
 def setUp(self):
  self.cancel_patch=patch.object(extract,'_cancel',threading.Event())
  self.cancel_patch.start()
  self.addCleanup(self.cancel_patch.stop)

 def test_status_restores_latest_saved_result_without_starting_analysis(self):
  app=module_app()
  with tempfile.TemporaryDirectory() as temporary:
   root=Path(temporary);source=root/'README.md';source.write_text('# saved result')
   with patch.object(extract,'OUTPUT',root/'saved'),patch.object(projects,'OUTPUT',root/'saved'):
    saved=extract.analyze('file',str(source))
    with patch.object(extract,'_state',{'stage':'idle','detail':'','project':None}),TestClient(app) as client:
     response=client.get('/api/rea/status')
     self.assertEqual(response.status_code,200)
     self.assertFalse(response.json()['active'])
     self.assertEqual(response.json()['project']['id'],saved['id'])
     self.assertEqual(response.json()['stage'],'saved')

 def test_native_metadata_separates_recovered_and_unavailable_functions(self):
  with tempfile.TemporaryDirectory() as temporary:
   root=Path(temporary);source=root/'fixture.exe';source.write_bytes(b'MZ-test-fixture')
   recovered={'source':'/* inferred pseudocode */','sha256':'fixture','total':2,'succeeded':1,'failed':1,'discovered':2,'external_references':0,'limitations':['fixture only'],
              'items':[{'address':'0x1000','status':'ok','pseudocode':'int main() { return 0; }'},{'address':'0x2000','status':'failed','error':'unavailable'}]}
   with patch.object(extract,'OUTPUT',root/'saved'),patch.object(extract,'native_recover',return_value=recovered):
    result=extract.analyze('file',str(source))
   self.assertEqual((result['function_total'],result['decompiled_functions'],result['unavailable_functions']),(2,1,1))
   self.assertEqual((Path(result['folder'])/'original/fixture.exe').read_bytes(),source.read_bytes())
   self.assertTrue((Path(result['folder'])/'inferred/decompiled.c').is_file())

 def test_corrupt_archive_is_a_user_error_through_module_router(self):
  app=module_app()
  with tempfile.TemporaryDirectory() as temporary:
   root=Path(temporary);archive=root/'broken.zip';archive.write_bytes(b'not a zip')
   with patch.object(extract,'OUTPUT',root/'saved'),TestClient(app) as client:
    response=client.post('/api/rea/analyze',json={'kind':'file','target':str(archive)})
    self.assertEqual(response.status_code,400)
    self.assertIn('ZIP/APK/IPA',response.json()['detail'])
   self.assertFalse(extract._gate.locked())

 def test_plain_text_is_copied_without_native_decompilation(self):
  with tempfile.TemporaryDirectory() as temporary:
   root=Path(temporary);source=root/'README.md';source.write_text('# original documentation',encoding='utf8')
   with patch.object(extract,'OUTPUT',root/'saved'),patch.object(extract,'native_recover') as native:
    result=extract.analyze('file',str(source))
   native.assert_not_called()
   self.assertEqual(result['state'],'saved')
   self.assertEqual((Path(result['folder'])/'original/README.md').read_text(),'# original documentation')

 def test_missing_and_mismatched_inputs_create_no_project_record(self):
  with tempfile.TemporaryDirectory() as temporary:
   root=Path(temporary);source=root/'source.py';source.write_text('value=7');directory=root/'directory';directory.mkdir()
   with patch.object(extract,'OUTPUT',root/'saved'):
    for kind,target in [('folder',source),('file',directory),('file',root/'missing.py')]:
     with self.subTest(kind=kind,target=target):
      with self.assertRaises(ValueError):extract.analyze(kind,str(target))
      self.assertFalse(extract._gate.locked())
   self.assertFalse((root/'saved').exists())

 def test_archive_preserves_resources_and_rejects_escape_paths(self):
  with tempfile.TemporaryDirectory() as temporary:
   root=Path(temporary);archive=root/'source.zip'
   with zipfile.ZipFile(archive,'w') as zipfile_out:zipfile_out.writestr('src/app.js','export const value=7;')
   with patch.object(extract,'OUTPUT',root/'saved'):
    result=extract.analyze('file',str(archive))
    self.assertEqual((Path(result['folder'])/'original/src/app.js').read_text(),'export const value=7;')
    self.assertTrue((Path(result['folder'])/'analysis/graph.json').is_file())
    with zipfile.ZipFile(archive,'w') as zipfile_out:zipfile_out.writestr('../../escaped.js','not allowed')
    with self.assertRaisesRegex(ValueError,'프로젝트 내부'):extract.analyze('file',str(archive))
   self.assertFalse((root/'escaped.js').exists())
   self.assertFalse(extract._gate.locked())

 def test_cancelled_copy_releases_lock_and_next_analysis_succeeds(self):
  with tempfile.TemporaryDirectory() as temporary:
   root=Path(temporary);source=root/'source';source.mkdir();(source/'a.py').write_text('a=1');(source/'b.py').write_text('b=2')
   entered=threading.Event();resume=threading.Event();errors=[];original=extract.shutil.copyfile
   def slow_copy(*args,**kwargs):entered.set();resume.wait(3);return original(*args,**kwargs)
   def run():
    try:extract.analyze('folder',str(source))
    except RuntimeError as error:errors.append(str(error))
   with patch.object(extract,'OUTPUT',root/'saved'),patch.object(extract.shutil,'copyfile',side_effect=slow_copy):
    worker=threading.Thread(target=run);worker.start()
    try:
     self.assertTrue(entered.wait(2))
     current=extract.analysis_status()
     self.assertTrue(current['active']);self.assertEqual(current['stage'],'extract')
     self.assertEqual(current['project']['input'],str(source))
     extract.stop()
    finally:resume.set();worker.join(5)
   self.assertFalse(worker.is_alive());self.assertFalse(extract._gate.locked())
   self.assertEqual(errors,['사용자가 분석을 중지했습니다.'])
   states=[json.loads(path.read_text())['state'] for path in (root/'saved').glob('*/project.json')]
   self.assertEqual(states,['stopped'])
   with patch.object(extract,'OUTPUT',root/'saved'):
    self.assertEqual(extract.analyze('file',str(source/'a.py'))['state'],'saved')

 def test_storage_failure_releases_lock_and_next_analysis_succeeds(self):
  with tempfile.TemporaryDirectory() as temporary:
   root=Path(temporary);source=root/'sample.py';source.write_text('value = 7\n')
   blocked=root/'blocked';blocked.write_text('not a directory')
   with patch.object(extract,'OUTPUT',blocked):
    with self.assertRaises(OSError):extract.analyze('file',str(source))
   self.assertFalse(extract._gate.locked())
   with patch.object(extract,'OUTPUT',root/'saved'):
    result=extract.analyze('file',str(source))
   self.assertEqual(result['state'],'saved')
   self.assertEqual((Path(result['folder'])/'original/sample.py').read_text(),'value = 7\n')

 def test_catalog_keeps_valid_projects_when_other_records_are_invalid(self):
  with tempfile.TemporaryDirectory() as temporary:
   root=Path(temporary)
   valid={'id':'a'*32,'name':'valid','folder':str(root/'valid'),'created_at':'2026-10-14T00:00:00Z','state':'saved'}
   for name,record in [('valid',valid),('empty',{}),('array',[]),('wrong-date',{**valid,'created_at':None})]:
    folder=root/name;folder.mkdir();(folder/'project.json').write_text(json.dumps(record))
   with patch.object(projects,'OUTPUT',root):
    self.assertEqual(projects.catalog()['items'],[valid])
    self.assertEqual(projects.tree(valid['id'])['items'][0]['name'],'project.json')

 def test_folder_snapshot_excludes_project_trash(self):
  with tempfile.TemporaryDirectory() as temporary:
   root=Path(temporary);(root/'app.js').write_text('export const value=7;')
   trash=root/'휴지통';trash.mkdir();(trash/'discarded.js').write_text('discarded fixture')
   output=root/'saved';destination=output/'example/original/source'
   with patch.object(extract,'ROOT',root),patch.object(extract,'OUTPUT',output):
    extract._copy_directory(root,destination)
   self.assertTrue((destination/'app.js').is_file())
   self.assertFalse((destination/'휴지통').exists())

 def test_real_javascript_analysis_saves_original_code_and_structure(self):
  with tempfile.TemporaryDirectory() as temporary:
   root=Path(temporary);source=root/'source';source.mkdir()
   code='import {double} from "./math.js"; export function run(value) { return double(value); }'
   (source/'app.js').write_text(code,encoding='utf8')
   (source/'math.js').write_text('export function double(value) { return value * 2; }',encoding='utf8')
   with patch.object(extract,'OUTPUT',root/'saved'),patch.object(projects,'OUTPUT',root/'saved'):
    result=extract.analyze('folder',str(source))
    self.assertEqual(result['state'],'saved')
    self.assertEqual(result['original_files'],2)
    self.assertEqual(projects.read_file(result['id'],'original/source/app.js')['content'],code)
    folder=Path(result['folder'])
    self.assertTrue((folder/'analysis/graph.json').is_file())
    self.assertTrue((folder/'inferred/relationships.json').is_file())
    self.assertIn('원문',projects.read_file(result['id'],'README.md')['content'])


if __name__=='__main__':unittest.main()
