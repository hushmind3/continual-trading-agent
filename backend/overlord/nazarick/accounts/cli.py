"""Local agent entry points; stdio MCP and secret-to-environment runner, no extra HTTP server."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'backend'))
from overlord.nazarick.accounts import state, vault, browser


def update(key, status, notes):
    if status not in {'pending', 'working', 'waiting_user', 'registered', 'key_ready', 'failed'}:
        raise ValueError('허용하지 않는 진행 상태입니다.')
    item = state.find(key)
    return state.save({**item, 'status': status, 'notes': notes[:1000]})


def mcp():
    tools = [
        {'name': 'shared_accounts', 'description': '공용 업체 목록과 실제 가입 진행 기록 조회. 브라우저 로그인 상태를 증명하지 않습니다.',
         'inputSchema': {'type': 'object', 'properties': {}, 'additionalProperties': False}},
        {'name': 'shared_account_update', 'description': '실제 가입 결과를 진행표에 기록. CAPTCHA/추가 인증은 waiting_user. 키·비밀번호를 notes에 넣지 마세요.',
         'inputSchema': {'type': 'object', 'properties': {'id': {'type': 'string'}, 'status': {'type': 'string', 'enum': ['pending','working','waiting_user','registered','key_ready','failed']}, 'notes': {'type': 'string', 'maxLength': 1000}}, 'required': ['id','status','notes'], 'additionalProperties': False}},
    ]
    for line in sys.stdin:
        request = {}
        try:
            request = json.loads(line)
            if 'id' not in request:
                continue
            method = request.get('method')
            if method == 'initialize':
                result = {'protocolVersion': '2024-11-05', 'capabilities': {'tools': {}}, 'serverInfo': {'name': 'platform-shared-accounts', 'version': '1.0.0'},
                          'instructions': '공용 브라우저는 platform_browser MCP로 백그라운드에서 사용합니다. 이미 승인된 가입·약관 동의·키 발급을 반복 승인받지 마세요. 추가 본인 인증·CAPTCHA는 우회하지 말고 기록 후 다른 업체를 진행하세요. 같은 업체 가입을 동시에 실행하지 마세요. 키·비밀번호는 결과에 반환하지 마세요.'}
            elif method == 'tools/list':
                result = {'tools': tools}
            elif method == 'ping':
                result = {}
            elif method == 'tools/call':
                params = request.get('params', {})
                if params.get('name') == 'shared_accounts':
                    value = {'services': state.listing(), 'browser': browser.status()}
                elif params.get('name') == 'shared_account_update':
                    args = params.get('arguments', {})
                    value = update(args['id'], args['status'], args['notes'])
                else:
                    raise ValueError('알 수 없는 공용 도구입니다.')
                result = {'content': [{'type': 'text', 'text': json.dumps(value, ensure_ascii=False)}]}
            else:
                print(json.dumps({'jsonrpc': '2.0', 'id': request['id'], 'error': {'code': -32601, 'message': 'Unknown method'}}), flush=True)
                continue
            response = {'jsonrpc': '2.0', 'id': request['id'], 'result': result}
        except Exception as error:
            response = {'jsonrpc': '2.0', 'id': request.get('id'), 'error': {'code': -32602, 'message': str(error)}}
        print(json.dumps(response, ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='action', required=True)
    for name in ('list', 'mcp-accounts', 'mcp-browser'):
        sub.add_parser(name)
    change = sub.add_parser('update')
    change.add_argument('id'); change.add_argument('status'); change.add_argument('--notes', default='')
    run = sub.add_parser('run')
    run.add_argument('--service', required=True); run.add_argument('--env', required=True)
    run.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.action == 'mcp-accounts':
        return mcp()
    if args.action == 'mcp-browser':
        endpoint = browser.start('automation')['endpoint']
        entry = ROOT / 'runtime/ai_agent/OpenClawOriginal/source/node_modules/chrome-devtools-mcp/build/src/bin/chrome-devtools-mcp.js'
        node = shutil.which('node')
        if not node or not entry.is_file():
            raise ValueError('기존 Chrome DevTools MCP/Node 설치본이 필요합니다. 자동 다운로드하지 않습니다.')
        os.environ['CHROME_DEVTOOLS_MCP_NO_USAGE_STATISTICS'] = '1'
        os.execv(node, [node, str(entry), '--browser-url=' + endpoint,
                       '--no-usage-statistics', '--no-performance-crux', '--no-category-performance', '--no-category-network'])
    if args.action == 'run':
        state.find(args.service)
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', args.env):
            raise ValueError('유효한 환경변수 이름을 입력하세요.')
        command = args.command[1:] if args.command[:1] == ['--'] else args.command
        if not command:
            raise ValueError('실행할 명령이 필요합니다.')
        env = {**os.environ, args.env: vault.read(args.service)}
        # Child inherits terminal output: callers must not print their environment/secrets.
        raise SystemExit(subprocess.call(command, env=env))
    print(json.dumps(state.listing() if args.action == 'list' else update(args.id, args.status, args.notes), ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
