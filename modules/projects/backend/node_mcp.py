"""Use a repository's published, version-pinned stdio MCP package."""
import json
from pathlib import Path
import re
import shutil
from urllib.parse import quote
from urllib.request import urlopen
from .github import repository
from .store import owned


def detect(source):
    manifest, package = source / 'server.json', source / 'package.json'
    if not manifest.is_file() or not package.is_file(): return None
    data = json.loads(manifest.read_text(encoding='utf8'))
    npm = json.loads(package.read_text(encoding='utf8'))
    for entry in data.get('packages', []):
        if entry.get('registryType') != 'npm' or entry.get('transport', {}).get('type') != 'stdio': continue
        if entry.get('identifier') != npm.get('name') or entry.get('version') != npm.get('version'): continue
        arguments = entry.get('packageArguments', [])
        if any(arg.get('type') != 'positional' or not isinstance(arg.get('value'), str) for arg in arguments): continue
        bins = npm.get('bin', {})
        script = next(iter(bins.values()), None) if isinstance(bins, dict) else bins
        if not script: continue
        return validate(source, {'kind': 'node-mcp', 'directory': '.', 'package': npm['name'],
            'version': npm['version'], 'script': script, 'arguments': [arg['value'] for arg in arguments],
            'repository': data.get('repository', {}).get('url', '')})


def validate(source, spec):
    if not re.fullmatch(r'(?:@[a-z0-9_.-]+/)?[a-z0-9_.-]+', spec.get('package', '')):
        raise ValueError('MCP npm 패키지 이름이 올바르지 않습니다.')
    if not re.fullmatch(r'\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?', spec.get('version', '')):
        raise ValueError('MCP 패키지의 정확한 버전이 필요합니다.')
    owned(source, spec.get('script', ''))
    repository(spec.get('repository', ''))
    if not isinstance(spec.get('arguments'), list) or not all(isinstance(arg, str) for arg in spec['arguments']):
        raise ValueError('MCP 실행 인수가 올바르지 않습니다.')
    return spec


def command(source, spec):
    package = owned(source / '.platform-runtime/node_modules', spec['package'])
    script = owned(package, spec['script'])
    if not script.is_file(): raise ValueError('설치된 MCP 실행 파일이 없습니다.')
    node = shutil.which('node')
    if not node: raise ValueError('Node.js 실행기를 찾지 못했습니다.')
    return [node, str(script), *spec['arguments']]


def prepare(source, spec, run):
    node = shutil.which('node'); npm = Path(node or '').parent / 'node_modules/npm/bin/npm-cli.js'
    if not node or not npm.is_file(): raise ValueError('Node.js/npm 실행기를 찾지 못했습니다.')
    with urlopen('https://registry.npmjs.org/' + quote(spec['package'], safe='') + '/' + spec['version'], timeout=25) as response:
        metadata = json.load(response)
    origin = metadata.get('repository', {})
    origin = origin.get('url', '') if isinstance(origin, dict) else origin
    origin = origin.removeprefix('git+')
    if repository(origin).lower() != repository(spec['repository']).lower():
        raise ValueError('npm 배포본의 원본 저장소가 GitHub 등록 정보와 다릅니다.')
    target = source / '.platform-runtime'; target.mkdir(exist_ok=True)
    run([node, str(npm), 'install', '--prefix', str(target), '--no-audit', '--no-fund', '--save-exact',
         spec['package'] + '@' + spec['version']], source, 900)
    command(source, spec)
