"""Run PROJECT ZERO's actual business tests against copied public source and an isolated DB."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def run():
    state = ROOT/'runtime/projects/manage'
    record = next(json.loads(p.read_text(encoding='utf8')) for p in (state/'registry').glob('*.json')
                  if json.loads(p.read_text(encoding='utf8')).get('repository') == 'hushmind3/project-zero')
    source = Path(record['active_source'])
    import site
    site.addsitedir(str(source/'.platform-runtime/python'))
    os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
    import pytest
    verification = state/'verification'; verification.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='project-zero-', dir=verification) as folder:
        base = Path(folder); app = base/'source'; app.mkdir()
        names = subprocess.check_output(['git', '-C', str(source), 'ls-files', '-z'], encoding='utf8').split('\0')
        for name in filter(None, names):
            file = (source/name).resolve()
            if not file.is_relative_to(source.resolve()) or not file.is_file(): continue
            target=app/name; target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(file, target)
        os.environ['PROJECT_ZERO_DATA_DIR'] = str(base/'data')
        os.environ['PLATFORM_PROJECT_ZERO_WORKFLOW_TEST'] = '1'
        os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
        os.environ.pop('PROJECT_ZERO_ADMIN_TOKEN', None)
        config=base/'pytest.ini';config.write_text('[pytest]\n',encoding='utf8')
        sys.path[:0] = [str(app), str(app/'tests'), str(ROOT/'backend')]
        from platform_modules import mount_namespaces
        mount_namespaces()
        from platform_plugins.projects.project_zero import install
        class OfflineProfile:
            @pytest.hookimpl(hookwrapper=True)
            def pytest_fixture_setup(self, fixturedef, request):
                outcome = yield
                if fixturedef.argname == 'app':
                    outcome.get_result()
                    import ai_provider
                    patcher=request.getfixturevalue('monkeypatch')
                    client=ai_provider.httpx.AsyncClient
                    class OfflineClient(client):
                        async def get(self,url,*args,**kwargs):
                            if str(url).startswith('http://127.0.0.1:11434'):
                                raise ai_provider.httpx.ConnectError('Isolated workflow test: no user model')
                            return await super().get(url,*args,**kwargs)
                        async def post(self,url,*args,**kwargs):
                            if str(url).startswith('http://127.0.0.1:11434'):
                                raise RuntimeError('Unmocked user-model invocation blocked')
                            return await super().post(url,*args,**kwargs)
                    patcher.setattr(ai_provider.httpx,'AsyncClient',OfflineClient)
                    install()
        result = pytest.main(['-c',str(config),'-q',str(app/'tests'),str(ROOT/'development/scripts/project_zero_workflow.py'),
                              '--basetemp',str(base/'pytest')],plugins=[OfflineProfile()])
        (verification/'project-zero-workflow.json').write_text(json.dumps({'pytest_exit':int(result),
            'source':str(source),'isolated_data':True,'llm':'mocked; no user model calls','compatibility_profile':True}),encoding='utf8')
        return result


if __name__=='__main__':sys.exit(run())
