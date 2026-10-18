"""Built-in source export excludes other modules and private state."""
import importlib.util
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from platform_modules import mount_namespaces
mount_namespaces()
from platform_plugins.projects import builtin_packages,store


class BuiltinPackageTests(unittest.TestCase):
    def test_each_export_contains_only_its_module_and_a_self_contained_launcher(self):
        base=ROOT/'runtime/projects/manage/verification';base.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=base) as temporary,patch.object(store,'STATE',Path(temporary)):
            for key in ('finance','rea','hermes'):
                with self.subTest(module=key):
                    result=builtin_packages.export(key)
                    archive=Path(temporary)/'projects'/key/'exports'/result['filename']
                    with zipfile.ZipFile(archive) as bundle:
                        names=bundle.namelist()
                        modules={name.split('/')[1] for name in names if name.startswith('modules/') and len(name.split('/'))>2}
                        self.assertEqual(modules,{key})
                        self.assertIn('backend/web_api.py',names)
                        self.assertIn('frontend/src/tailwind.css',names)
                        self.assertIn('development/scripts/requirements/platform.txt',names)
                        self.assertIn('설치.cmd',names)
                        self.assertFalse(any('/.venv/' in name or '/node_modules/' in name or name.startswith('runtime/') for name in names))
                        self.assertFalse(any('/configs/local/' in name or name.endswith(('.env','.sqlite3')) for name in names))
                        outside=Path(temporary)/key;bundle.extractall(outside)
                    checked=subprocess.run([sys.executable,'-I','-X','utf8',str(outside/'run.py'),'check'],cwd=outside,
                                           capture_output=True,text=True,encoding='utf8',timeout=20)
                    self.assertNotEqual(checked.returncode,0)
                    self.assertIn('setup',checked.stderr)
                    spec=importlib.util.spec_from_file_location('standalone_probe',outside/'run.py')
                    runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
                    with patch.dict('os.environ',{'PLATFORM_ROOT':str(ROOT),'PLATFORM_MODULES_DIR':str(ROOT/'modules'),'PYTHONPATH':str(ROOT/'backend'),'HERMES_HOME':'old'}):
                        environment=runner.environment()
                    self.assertEqual(environment['PLATFORM_ROOT'],str(outside.resolve()))
                    self.assertNotIn('PYTHONPATH',environment)
                    self.assertNotIn('HERMES_HOME',environment)
                    # The source manifest notices a missing source before attempting setup.
                    (outside/'backend/web_api.py').unlink()
                    with self.assertRaisesRegex(ValueError,'무결성'):runner.verify()

    def test_export_rejects_unknown_builtin(self):
        with self.assertRaises(ValueError):builtin_packages.export('../finance')

    def test_local_runner_download_is_pinned_and_cannot_escape_its_folder(self):
        spec=importlib.util.spec_from_file_location('resource_runner',ROOT/'modules/projects/backend/standalone_runner.py')
        runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
        base=ROOT/'runtime/projects/manage/verification';base.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=base) as temporary,patch.object(runner,'ROOT',Path(temporary)):
            data=io.BytesIO()
            with zipfile.ZipFile(data,'w') as bundle:bundle.writestr('llama-server.exe',b'test executable')
            payload=data.getvalue()
            metadata={'llama_cpp':{'source':'https://github.com/ggml-org/llama.cpp/releases/download/test/package.zip',
                                  'sha256':hashlib.sha256(payload).hexdigest(),'release':'test'}}
            with patch.object(runner,'urlopen',return_value=io.BytesIO(payload)) as fetch:runner.install_runner(metadata)
            fetch.assert_called_once()
            self.assertEqual((Path(temporary)/'runtime/shared/engines/llama.cpp/llama-server.exe').read_bytes(),b'test executable')
            with patch.object(runner,'urlopen',side_effect=AssertionError('must reuse verified runner')):runner.install_runner(metadata)
            data=io.BytesIO()
            with zipfile.ZipFile(data,'w') as bundle:bundle.writestr('../../../../escape.txt',b'escape')
            payload=data.getvalue();metadata['llama_cpp']['sha256']=hashlib.sha256(payload).hexdigest()
            with patch.object(runner,'urlopen',return_value=io.BytesIO(payload)),self.assertRaisesRegex(ValueError,'경로'):runner.install_runner(metadata)
            metadata['llama_cpp']['sha256']='0'*64
            with patch.object(runner,'urlopen',return_value=io.BytesIO(payload)),self.assertRaisesRegex(ValueError,'SHA-256'):runner.install_runner(metadata)


if __name__=='__main__':unittest.main()
