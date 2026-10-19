"""Original installed company API/DB with isolated files and real Node checks."""
import asyncio
from contextvars import ContextVar
import importlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
import base64
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
RECORDS = list((ROOT / 'runtime/projects/manage/registry').glob('*project-zero*.json'))


@unittest.skipUnless(RECORDS, 'Company contract fixture app is not installed')
class CompanyTests(unittest.TestCase):
    def setUp(self):
        source = Path(json.loads(RECORDS[0].read_text(encoding='utf-8'))['active_source'])
        checks = ROOT / 'runtime/projects/manage/verification'; checks.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="company-workflow-",dir=checks); self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name); copied = self.base / 'source'; copied.mkdir()
        names = []
        for file in source.glob('*.py'):
            shutil.copyfile(file, copied / file.name); names.append(file.stem)
        self.modules = {name: sys.modules.pop(name, None) for name in names}
        self.addCleanup(self.restore, names)
        self.env = patch.dict(os.environ, {'PROJECT_ZERO_DATA_DIR': str(self.base / 'data')}); self.env.start(); self.addCleanup(self.env.stop)
        self.path = patch.object(sys, 'path', [str(copied), str(source / '.platform-runtime/python'), *sys.path]); self.path.start(); self.addCleanup(self.path.stop)
        self.db = importlib.import_module('database')
        spec = importlib.util.spec_from_file_location('company_fixture_adapter', ROOT / 'modules/projects/backend/integrations/company.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        module.close_connections(self.db); self.db.initialize()
        self.ops = importlib.import_module('operations'); self.ventures = importlib.import_module('venture_engine')
        self.ai = importlib.import_module('ai_provider'); self.ai.platform_request_options = ContextVar('test_application_options', default={})
        server = importlib.import_module('server')
        self.activity=[]
        module.install(server.app, self.base,self.activity.append)
        self.id = 'venture_fixture'
        with self.db.connect() as c:
            c.execute('INSERT INTO ventures(id,created_at,name,proposal_json,status,mode) VALUES(?,?,?,?,?,?)',
                      (self.id, self.db.now(), 'Fixture Quote', json.dumps({'name': 'Fixture Quote', 'product': '견적 계산기'}), 'pending', 'fixture'))

    def restore(self, names):
        for name in names:
            sys.modules.pop(name, None)
            if self.modules[name] is not None: sys.modules[name] = self.modules[name]

    def jobs(self): return self.db.many("SELECT * FROM jobs WHERE type='agent_task' ORDER BY rowid")

    def test_approval_queues_three_sequential_actual_jobs_without_releasing(self):
        result = self.ventures.decide(self.id, True)
        self.assertEqual([j['role'] for j in self.jobs()], ['CPO', 'CTO', 'QA'])
        self.assertFalse(result['released']); self.assertNotIn('도구가 없', result['reply'])
        with self.assertRaises(ValueError): self.ventures.decide(self.id, True)
        self.assertEqual(len(self.jobs()), 3)
        args = [json.loads(j['arguments']) for j in self.jobs()]
        self.assertEqual(args[1]['depends_on'], result['jobs'][0])

    def test_prose_without_a_file_is_failure_and_stops_later_roles(self):
        self.ventures.decide(self.id, True)
        async def compose(*args, **kwargs): return '모든 요구사항을 작성했습니다. 검증 완료입니다.'
        self.ai.compose = compose
        asyncio.run(self.ops.process_one())
        self.assertEqual([j['status'] for j in self.jobs()], ['failed'] * 3)
        self.assertIn('실제로 작성하지', self.jobs()[0]['error'])
        self.assertEqual([j['mode'] for j in self.jobs()], ['incomplete', 'blocked', 'blocked'])

    def prepare(self, fail_test=False):
        async def compose(system, user, **kwargs):
            data = json.loads(user); target = Path(self.ai.platform_request_options.get()['workspace'])
            self.assertTrue(target.is_relative_to(self.base / 'workspaces'))
            if 'CPO' in system: (target / 'requirements.md').write_text('# 실제 요구사항\n' + '수량과 단가로 견적 합계를 계산하고 음수를 거부합니다.\n' * 4, encoding='utf-8')
            if 'CTO' in system:
                (target / 'src').mkdir(exist_ok=True)
                (target / 'src/App.tsx').write_text('export default function App(){return <main>Quote</main>}', encoding='utf-8')
                (target / 'src/tailwind.css').write_text('@import "tailwindcss";', encoding='utf-8')
                (target / 'package.json').write_text(json.dumps({'scripts': {'test': 'node --test quote.test.mjs', 'build': 'node build.mjs'}}), encoding='utf-8')
                (target / 'quote.test.mjs').write_text("import assert from 'node:assert/strict';assert.equal(2*3000," + ('1' if fail_test else '6000') + ');', encoding='utf-8')
                (target / 'build.mjs').write_text("import fs from 'node:fs';fs.mkdirSync('dist',{recursive:true});fs.writeFileSync('dist/index.html','<main>Quote prototype</main>');", encoding='utf-8')
            return '실제 파일을 작성하고 작업 결과를 보고합니다.'
        self.ai.compose = compose; self.ventures.decide(self.id, True)

    def test_original_queue_runs_real_node_checks_and_writes_verification_receipt(self):
        self.prepare()
        for _ in range(3): asyncio.run(self.ops.process_one())
        self.assertEqual([j['status'] for j in self.jobs()], ['completed'] * 3, [j['error'] for j in self.jobs()])
        receipt = json.loads((self.base / 'workspaces' / self.id / 'verification.json').read_text(encoding='utf-8'))
        self.assertEqual([r['exit_code'] for r in receipt], [0, 0])
        self.assertEqual(self.activity,[1,-1]*3)

    def test_real_child_approval_provider_ipc_busy_guard_and_node_verification(self):
        from platform_modules import mount_namespaces
        mount_namespaces()
        from platform_plugins.projects import runtime,python_packages,harness
        self.prepare()
        # Keep the actual approved jobs; the isolated child consumes the original DB queue.
        key='p_company_fixture'
        integration=ROOT/'modules/projects/backend/integrations/company.py'
        source=self.base/'source'
        actual=Path(json.loads(RECORDS[0].read_text(encoding='utf-8'))['active_source'])
        worker=None
        def execute(project,payload,cancelled):
            if payload.get('operation')=='settings':return {'mode':'hermes','name':'fixture','endpoint':'http://127.0.0.1:1'}
            time.sleep(.25)
            token=self.ai.platform_request_options.set({'workspace':payload['workspace']})
            try:return asyncio.run(self.ai.compose(payload['system'],payload['user']))
            finally:self.ai.platform_request_options.reset(token)
        with patch.object(python_packages,'folder',return_value=actual/'.platform-runtime/python'),patch.object(harness,'execute',side_effect=execute):
            try:
                worker=runtime.AppWorker(source,{'kind':'fastapi','app':'server:app'}, {'PROJECT_ZERO_DATA_DIR':str(self.base/'data')}, {'enabled':True,'entry':'ai_provider:compose'},key,integration,self.base)
                with patch.dict(runtime.WORKERS,{key:worker}):
                    deadline=time.monotonic()+20;protected=False
                    while time.monotonic()<deadline:
                        reply=worker.call({'path':'/healthz'})
                        self.assertEqual(reply['status'],200)
                        protected=protected or '제작·검증' in runtime.busy_reason()
                        rows=self.jobs()
                        if all(j['status'] in ('completed','failed') for j in rows):break
                        time.sleep(.05)
                    self.assertEqual([j['status'] for j in rows],['completed']*3,[j['error'] for j in rows])
                    self.assertTrue(protected)
            finally:
                if worker:worker.close()

    def test_actual_test_failure_cannot_be_reported_as_qa_complete(self):
        self.prepare(fail_test=True)
        for _ in range(3): asyncio.run(self.ops.process_one())
        self.assertEqual(self.jobs()[-1]['status'], 'failed')
        self.assertIn('실제 검증 실패', self.jobs()[-1]['error'])
        self.assertFalse((self.base / 'workspaces' / self.id / 'verification.json').exists())


if __name__ == '__main__': unittest.main()
