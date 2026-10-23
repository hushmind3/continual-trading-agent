"""Start the official OpenClaw CLI with a private state directory."""
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'runtime/ai_agent/OpenClawOriginal'
SOURCE = BASE / 'source'
HOME = BASE / 'home'
NODE = BASE / 'tools/node/bin/node'


def _prepare_embedded_gateway():
    """Use passwordless auth only for this loopback-only embedded Gateway."""
    config_path = HOME / 'openclaw.json'
    try:
        config = json.loads(config_path.read_text()) if config_path.is_file() else {}
    except (OSError, ValueError) as error:
        raise RuntimeError('OpenClaw 설정을 읽지 못했습니다.') from error
    if not isinstance(config, dict):
        raise RuntimeError('OpenClaw 설정 형식이 올바르지 않습니다.')
    gateway = config.setdefault('gateway', {})
    if not isinstance(gateway, dict):
        raise RuntimeError('OpenClaw Gateway 설정 형식이 올바르지 않습니다.')
    tailscale = gateway.get('tailscale')
    if (gateway.get('mode', 'local') != 'local' or
            isinstance(tailscale, dict) and tailscale.get('mode') == 'serve'):
        raise RuntimeError('8766 내장 화면은 로컬 전용 Gateway 설정에서만 실행할 수 있습니다.')
    gateway['mode'] = 'local'
    gateway['bind'] = 'loopback'
    auth = gateway.setdefault('auth', {})
    if not isinstance(auth, dict):
        raise RuntimeError('OpenClaw Gateway 인증 설정 형식이 올바르지 않습니다.')
    # The wrapper and Gateway share this machine. Do not make the Gateway
    # reachable from the network just to avoid asking the user for its token.
    auth['mode'] = 'none'
    temporary = config_path.with_name('.openclaw.json.platform-tmp')
    temporary.write_text(json.dumps(config, ensure_ascii=False, indent=2) + '\n')
    os.chmod(temporary, 0o600)
    os.replace(temporary, config_path)


def launch(arguments):
    if not (SOURCE / 'package.json').is_file():
        raise RuntimeError('OpenClaw 공식 원본이 설치되지 않았습니다.')
    if not NODE.is_file():
        raise RuntimeError('OpenClaw에 필요한 Node.js 실행 파일이 없습니다.')
    env = {key: value for key, value in os.environ.items()
           if not key.startswith(('OPENCLAW_', 'HERMES_'))}
    env['PATH'] = os.pathsep.join((str(NODE.parent), str(SOURCE / 'node_modules/.bin'),
                                   env.get('PATH', os.defpath)))
    env.update({
        'OPENCLAW_STATE_DIR': str(HOME),
        'OPENCLAW_CONFIG_PATH': str(HOME / 'openclaw.json'),
        'OPENCLAW_SKIP_CHANNELS': '1',
        'OPENCLAW_GATEWAY_PORT': '19021',
        'OPENCLAW_DISABLE_BONJOUR': '1',
    })
    if arguments[:2] == ['gateway', 'run']:
        _prepare_embedded_gateway()
        policy = Path(__file__).resolve().with_name('frame_policy.mjs')
        existing = env.get('NODE_OPTIONS', '').strip()
        env['NODE_OPTIONS'] = f'{existing} --import={policy}'.strip()
    os.chdir(SOURCE)
    os.execve(NODE, [str(NODE), str(SOURCE / 'scripts/run-node.mjs'),
                     '--dev', *arguments], env)


if __name__ == '__main__':
    launch(sys.argv[1:])
