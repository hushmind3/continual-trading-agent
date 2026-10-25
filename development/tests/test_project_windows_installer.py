"""Original Windows installer discovery, typed controls and real execution."""
import json
import os
from unittest import skipUnless
import sys
import tempfile
import time
from pathlib import Path
from unittest import TestCase,main
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
from platform_modules import mount_namespaces
mount_namespaces()
from platform_plugins.projects import adapters,powershell_app,runtime,installer,requirements,store

@skipUnless(os.name=='nt','Windows 설치기 실제 실행은 Windows 작업에서 검증합니다.')
class WindowsInstallerTests(TestCase):
 def setUp(self):
  base=ROOT/'runtime/projects/manage/verification';base.mkdir(parents=True,exist_ok=True)
  self.temp=tempfile.TemporaryDirectory(dir=base);self.source=Path(self.temp.name)/'source';(self.source/'windows').mkdir(parents=True)
  self.script=self.source/'windows/install-example.ps1'
  self.script.write_text("param([Parameter(Mandatory)][string]$Output,[ValidateSet('Fast','Full')][string]$Mode='Fast',[switch]$Windowed,[string]$Text='original')\n@{mode=$Mode;windowed=[bool]$Windowed;text=$Text}|ConvertTo-Json|Set-Content -LiteralPath $Output -Encoding utf8\nWrite-Output 'original installer result'\n",encoding='utf8')
  self.record={'id':'test_setup','active_source':str(self.source),'adapter':{'kind':'powershell','directory':'.','script':'windows/install-example.ps1'}}
  self.patches=[patch.object(store,'STATE',self.source.parent/'runtime/projects/manage'),patch.object(runtime,'ACTIVE',0),patch.object(runtime,'RESTARTING',False),patch.object(installer,'RESTARTING',False),patch.object(installer,'JOBS',{})]
  for item in self.patches:item.start()
 def tearDown(self):
  deadline=time.monotonic()+30
  while runtime.ACTIVE and time.monotonic()<deadline:time.sleep(.05)
  for item in reversed(self.patches):item.stop()
  self.temp.cleanup()
 def test_discovery_only_parses_original_and_does_not_run_installer(self):
  self.assertEqual(adapters.detect(self.source),self.record['adapter'])
  metadata=powershell_app.inspect(self.source,self.record['adapter'])
  self.assertTrue(metadata['parameters'][0]['required'])
  self.assertEqual(metadata['parameters'][1]['choices'],['Fast','Full'])
  self.assertEqual(metadata['parameters'][1]['default'],'Fast')
  self.assertEqual(metadata['parameters'][2]['kind'],'switch')
  self.assertFalse((self.source.parent/'setup-state.json').exists())
 def test_original_installer_executes_typed_values_as_literal_arguments(self):
  output=self.source.parent/'result.json';text='quoted value $(Write-Output bad); 파일'
  powershell_app.start(self.record,{'Output':str(output),'Mode':'Full','Windowed':True,'Text':text})
  deadline=time.monotonic()+25
  while runtime.ACTIVE and time.monotonic()<deadline:time.sleep(.05)
  self.assertEqual(powershell_app.state(self.record)['state'],'complete')
  value=json.loads(output.read_text(encoding='utf-8-sig'))
  self.assertEqual(value,{'mode':'Full','windowed':True,'text':text})
  self.assertIn('original installer result',powershell_app.state(self.record)['log'])
 def test_missing_required_invalid_choice_and_unknown_parameter_are_rejected(self):
  for values in ({},{'Output':'file','Mode':'invalid'},{'Output':'file','Unknown':'x'}):
   with self.subTest(values=values),self.assertRaises(ValueError):powershell_app.start(self.record,values)
  self.assertEqual(runtime.ACTIVE,0)
 def test_install_destination_is_automatic_and_existing_program_input_is_separate(self):
  self.script.write_text("param([Parameter(Mandatory)][string]$InstallDir,[Parameter(Mandatory)][string]$StarCraftDir)\n",encoding='utf8')
  metadata=powershell_app.describe(self.record)
  destination,prerequisite=metadata['parameters']
  self.assertTrue(destination['managed'])
  self.assertEqual(Path(destination['default']),store.project_folder(self.record)/'application')
  self.assertFalse(prerequisite['managed']);self.assertIsNone(prerequisite['default'])
  self.assertFalse(store.project_folder(self.record).exists())
 def test_original_installer_writes_inside_its_managed_folder_without_path_input(self):
  self.script.write_text("param([Parameter(Mandatory)][string]$InstallDir)\nSet-Content -LiteralPath (Join-Path $InstallDir 'installed.txt') -Value 'real install'\n",encoding='utf8')
  powershell_app.start(self.record,{})
  deadline=time.monotonic()+25
  while runtime.ACTIVE and time.monotonic()<deadline:time.sleep(.05)
  self.assertEqual(powershell_app.state(self.record)['state'],'complete')
  self.assertEqual((store.install_folder(self.record)/'installed.txt').read_text().strip(),'real install')
 def test_analysis_tool_repository_is_not_classified_as_documentation_only(self):
  (self.source/'docs').mkdir();(self.source/'docs/notes.md').write_text('notes')
  requirements.check(self.source)

if __name__=='__main__':main()
