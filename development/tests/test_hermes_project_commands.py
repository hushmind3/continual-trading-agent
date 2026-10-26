"""Native npm helper: actual command receipts and owned-folder argument boundaries."""
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from platform_modules import mount_namespaces
mount_namespaces()
from ai_agent.choki.chat import project_commands as commands


class ProjectCommandTests(unittest.TestCase):
    def setUp(self):
        checks=ROOT/'runtime/ai_agent/choki/verification';checks.mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(prefix='project-command-',dir=checks);self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.worker=SimpleNamespace(company_link={'workspace':str(self.root)},stopping=False)
    def call(self,action,**kw):return json.loads(commands.run(self.worker,{'workspace':str(self.root),'action':action,**kw}))
    def test_outside_folder_and_global_flags_never_start_a_process(self):
        (self.root/'package.json').write_text('{}')
        with patch.object(commands.subprocess,'Popen') as process:
            outside=json.loads(commands.run(self.worker,{'workspace':str(self.root.parent),'action':'versions'}))
            self.assertIn('error',outside)
            for packages in (['--global','react'],['react;whoami'],['../evil'],['@scope/name','--prefix']):
                self.assertIn('error',self.call('install',packages=packages))
            process.assert_not_called()
    def test_actual_node_test_and_build_receipts_and_failure_exit_code(self):
        (self.root/'package.json').write_text(json.dumps({'scripts':{'test':'node test.cjs','build':'node build.cjs'}}))
        (self.root/'test.cjs').write_text("const assert=require('node:assert/strict');assert.equal(2+2,4);console.log('ACTUAL_NODE_TEST');")
        (self.root/'build.cjs').write_text("require('node:fs').mkdirSync('dist',{recursive:true});require('node:fs').writeFileSync('dist/index.html','<h1>Actual build fixture</h1>');")
        result=self.call('test');self.assertEqual(result['exit_code'],0,result);self.assertIn('ACTUAL_NODE_TEST',result['output'])
        self.assertTrue(Path(result['receipt']).is_relative_to(self.root/'verification'))
        result=self.call('build');self.assertEqual(result['exit_code'],0,result);self.assertTrue((self.root/'dist/index.html').is_file())
        (self.root/'test.cjs').write_text('process.exit(7)')
        result=self.call('test');self.assertEqual(result['exit_code'],7)
        self.assertEqual(json.loads(Path(result['receipt']).read_text())['exit_code'],7)

if __name__=='__main__':unittest.main()
