"""REA source/storage workflows using temporary fixtures, never model weights."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from rea.program_analysis import extract
from rea.project_explorer import projects


class REAWorkflowTests(unittest.TestCase):
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
