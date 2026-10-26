"""Add a new major menu/API through one folder; no central registration edits."""
import json
import re
import time
import urllib.request
from verify_module_detach import ROOT, BASE, api, digest


def main():
    identifier = 'registration_probe'
    folder = ROOT / 'modules' / identifier
    staging = ROOT / 'runtime/platform/registration-probe'
    report_path = ROOT / 'runtime/platform/module-registration-verification.json'
    assert not folder.exists() and not staging.exists(), 'Probe folder already exists'
    assert staging.resolve().is_relative_to((ROOT / 'runtime/platform').resolve())
    central = [ROOT / name for name in ('backend/menu_registry.py', 'backend/platform_modules.py',
        'frontend/src/shell/module_loader.ts', 'frontend/src/shell/menu_groups/menu_registry.ts')]
    before = digest(central)
    report = {'status': 'running', 'started_at': time.time(), 'checks': []}
    def record(name, value):
        report['checks'].append({'name': name, 'result': value})
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
        print(name + ': ' + str(value), flush=True)
    def wait(present):
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            try:
                ids = {item['id'] for item in api('platform/modules')['items']}
                assert {'finance', 'hermes'} <= ids
                with urllib.request.urlopen(BASE, timeout=10) as response:
                    html = response.read().decode()
                asset = re.search(r'src="(/assets/index-[^"]+\.js)"', html)
                with urllib.request.urlopen(BASE + asset[1], timeout=10) as response:
                    bundle = response.read().decode()
                if (identifier in ids) == present and ('Probe-' in bundle) == present:
                    return sorted(ids)
            except Exception:
                pass
            time.sleep(2)
        raise TimeoutError('Probe automatic registration timed out')
    try:
        (staging / 'backend').mkdir(parents=True)
        (staging / 'frontend').mkdir()
        manifest = {'schema': 1, 'id': identifier, 'group': {'id': identifier, 'title': '플러그인 확인'},
            'backend': {'namespace': 'platform_plugins.registration_probe', 'entry': 'register'},
            'frontend': {'entry': 'frontend/register.ts'}, 'order': 99}
        (staging / 'module.json').write_text(json.dumps(manifest, ensure_ascii=False), encoding='utf8')
        (staging / 'backend/register.py').write_text(
            "from fastapi import APIRouter\n"
            "MENU={'id':'registration_probe','title':'모듈 연결 확인','operations':['platform/probe/']}\n"
            "router=APIRouter()\n"
            "@router.get('/api/platform/probe/ping')\n"
            "def ping(): return {'module':'registration_probe','connected':True}\n", encoding='utf8')
        (staging / 'frontend/register.ts').write_text(
            "import {lazy} from 'react';\nimport {Blocks} from 'lucide-react';\n"
            "import type {MenuItem} from '@platform/shell/menu_groups/menu_types';\n"
            "export const menus:MenuItem[]=[{hash:'registration_probe',name:'모듈 연결 확인',"
            "group:'플러그인 확인',icon:Blocks,required:[],component:lazy(()=>import('./Probe'))}];\n", encoding='utf8')
        (staging / 'frontend/Probe.tsx').write_text(
            "export default function Probe(){return <main className=\"p-6\">모듈 연결 확인</main>;}\n", encoding='utf8')
        staging.rename(folder)
        record('new_module_and_frontend_auto_registered', wait(True))
        assert api('platform/probe/ping') == {'module': identifier, 'connected': True}
        record('new_api_through_shared_gateway', True)
        folder.rename(staging)
        record('removed_module_and_frontend', wait(False))
        assert digest(central) == before
        record('central_source_edits', 0)
        report['status'] = 'passed'
    except BaseException as exc:
        report.update(status='failed', error=str(exc))
        raise
    finally:
        if folder.exists() and not staging.exists():
            folder.rename(staging)
            try:
                wait(False)
            except Exception as exc:
                report['restore_error'] = str(exc)
        report['finished_at'] = time.time()
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')


if __name__ == '__main__':
    main()
