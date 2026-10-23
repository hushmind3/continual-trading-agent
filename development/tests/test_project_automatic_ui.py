"""No project-specific UI: original source -> typed schema -> actual execution."""
import json
import subprocess
import zipfile
import shutil
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
from platform_modules import mount_namespaces
mount_namespaces()
from platform_plugins.projects import cli_schema,adapters,runtime,store,packages,installer
SCRIPT='''import argparse,json
from pathlib import Path

def main():
    parser=argparse.ArgumentParser(description="Automatic command UI")
    parser.add_argument('--verbose',action='store_true')
    commands=parser.add_subparsers(dest='command',required=True)
    report=commands.add_parser('report',help='Create a report')
    report.add_argument('name',help='Report name')
    report.add_argument('--count',type=int,default=2)
    report.add_argument('--format',choices=['text','json'],default='text')
    report.add_argument('--tag',action='append')
    total=commands.add_parser('sum',help='Sum values')
    total.add_argument('numbers',type=int,nargs='+')
    args=parser.parse_args()
    Path('generated-result.json').write_text(json.dumps(vars(args)),encoding='utf8')
    print(json.dumps(vars(args),ensure_ascii=False))
if __name__=='__main__':main()
'''
class AutomaticInterfaceTests(unittest.TestCase):
 def setUp(self):
  base=ROOT/'runtime/projects/manage/verification';base.mkdir(parents=True,exist_ok=True)
  self.temp=tempfile.TemporaryDirectory(dir=base);self.source=Path(self.temp.name)/'source';self.source.mkdir()
  (self.source/'main.py').write_text(SCRIPT,encoding='utf8')
  self.record={'id':'auto_ui','active_source':str(self.source),'adapter':{'kind':'python-cli','directory':'.','script':'main.py'}}
  self.restart=patch.object(runtime,'RESTARTING',False);self.restart.start()
 def tearDown(self):self.restart.stop();self.temp.cleanup()
 def test_plain_source_is_detected_without_descriptor_or_manual_ui(self):
  self.assertEqual(adapters.detect(self.source),self.record['adapter'])
  self.assertFalse((self.source/'generated-result.json').exists())
  schema=cli_schema.describe(self.record);self.assertEqual(len(schema['commands']),2)
  fields={field['key']:field for field in schema['commands'][0]['fields']}
  self.assertEqual(fields['count']['kind'],'number');self.assertEqual(fields['verbose']['kind'],'boolean')
  self.assertTrue(fields['name']['required']);self.assertEqual(fields['format']['choices'],['text','json'])
 def test_generated_inputs_execute_original_subcommand_and_save_result(self):
  command=cli_schema.describe(self.record)['commands'][0]
  result=cli_schema.execute(self.record,command['id'],{'name':'자동 보고서','count':3,'format':'json','verbose':True,'tag':['one','two']})
  value=json.loads((self.source/'generated-result.json').read_text(encoding='utf8'))
  self.assertEqual(value,{'command':'report','verbose':True,'name':'자동 보고서','count':3,'format':'json','tag':['one','two']})
  self.assertIn('자동 보고서',result['text'])
  second=cli_schema.execute(self.record,command['id'],{'name':'fresh result'})
  self.assertNotIn('자동 보고서',second['text'])
  with patch.object(runtime,'CLI_ACTIVE',{self.record['id']}),self.assertRaises(ValueError):cli_schema.execute(self.record,command['id'],{'name':'duplicate'})
 def test_invalid_inputs_cannot_become_arbitrary_commands(self):
  command=cli_schema.describe(self.record)['commands'][0]
  for values in ({},{'name':'x','count':'3.5'},{'name':'x','format':'bad'},{'name':'x','unknown':'command'},{'name':'x','verbose':'false'}):
   with self.subTest(values=values),self.assertRaises(ValueError):cli_schema.arguments(command,values)
  with self.assertRaises(ValueError):cli_schema.execute(self.record,'../../outside.py',{})
  self.assertFalse((self.source/'generated-result.json').exists())
 def test_original_web_ui_stays_primary(self):
  (self.source/'index.html').write_text('<h1>Original UI</h1>')
  self.assertEqual(adapters.detect(self.source)['kind'],'static')
 def test_console_entry_without_main_guard_calls_original_function(self):
  (self.source/'main.py').write_text(SCRIPT.split("if __name__")[0],encoding='utf8')
  record={**self.record,'adapter':{'kind':'python-cli','directory':'.','entry':'main:main'}}
  command=cli_schema.describe(record)['commands'][0]
  cli_schema.execute(record,command['id'],{'name':'entry'})
  self.assertEqual(json.loads((self.source/'generated-result.json').read_text())['name'],'entry')
 def test_generated_script_package_runs_independently(self):
  state=self.source.parent/'state';source=state/'projects/p_ui/versions/v/source'
  shutil.copytree(self.source,source)
  record={**self.record,'id':'p_ui','active_source':str(source),'title':'Automatic UI','url':'https://github.com/verification/automatic-ui'}
  with patch.object(store,'STATE',state),patch.object(installer,'JOBS',{}),patch.object(installer,'RESTARTING',False),patch.object(runtime,'busy_reason',return_value=''):
   store.save(record);result=packages.export('p_ui')
  outside=self.source.parent/'standalone'
  with zipfile.ZipFile(state/'projects/p_ui/exports'/result['filename']) as archive:archive.extractall(outside)
  for arguments in (['check'],['run','report','portable','--count','4']):
   result=subprocess.run([sys.executable,'-I','-X','utf8',str(outside/'run.py'),*arguments],cwd=outside,capture_output=True,text=True,encoding='utf8')
   self.assertEqual(result.returncode,0,result.stderr)
  self.assertEqual(json.loads((outside/'source/generated-result.json').read_text())['count'],4)
 def test_argparse_alias_and_boolean_false_are_supported(self):
  (self.source/'main.py').write_text("from argparse import ArgumentParser as AP\np=AP()\np.add_argument('--color',action='store_false',default=True)\np.parse_args()\n",encoding='utf8')
  command=cli_schema.describe(self.record)['commands'][0]
  self.assertEqual(cli_schema.arguments(command,{'color':False}),['--color'])

if __name__=='__main__':unittest.main()
