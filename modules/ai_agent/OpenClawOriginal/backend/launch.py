"""Start the official OpenClaw CLI with a private state directory."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
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
    control_ui = gateway.setdefault('controlUi', {})
    if not isinstance(control_ui, dict):
        raise RuntimeError('OpenClaw Control UI 설정 형식이 올바르지 않습니다.')
    allowed_origins = control_ui.setdefault('allowedOrigins', [])
    if not isinstance(allowed_origins, list):
        raise RuntimeError('OpenClaw 허용 출처 설정 형식이 올바르지 않습니다.')
    embedded_origins = ['http://127.0.0.1:19021']
    tailscale = shutil.which('tailscale')
    if tailscale:
        try:
            command = [tailscale]
            socket_path = os.environ.get('TAILSCALE_SOCKET')
            if socket_path and not Path(socket_path).exists():
                socket_path = str(Path.home() / '.tailscale-projectplatform.sock')
            if socket_path:
                command.extend(['--socket', socket_path])
            result = subprocess.run([*command, 'status', '--json'], capture_output=True,
                                    text=True, timeout=3, check=False)
            status = json.loads(result.stdout) if result.returncode == 0 else {}
            dns_name = status.get('Self', {}).get('DNSName', '').rstrip('.')
            if dns_name.endswith('.ts.net'):
                embedded_origins.append(f'https://{dns_name}:8443')
                os.environ['PLATFORM_EMBED_ORIGINS'] = f'http://127.0.0.1:8766,https://{dns_name}'
        except (OSError, subprocess.SubprocessError, ValueError, AttributeError):
            pass
    for origin in embedded_origins:
        if origin not in allowed_origins:
            allowed_origins.append(origin)
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
        'PLATFORM_REMOTE_ACCESS_FILE': str(ROOT / 'runtime/platform/remote_access.json'),
    })
    if arguments[:2] == ['gateway', 'run']:
        _prepare_embedded_gateway()
        if os.environ.get('PLATFORM_EMBED_ORIGINS'):
            env['PLATFORM_EMBED_ORIGINS'] = os.environ['PLATFORM_EMBED_ORIGINS']
        policy = Path(__file__).resolve().with_name('frame_policy.mjs')
        existing = env.get('NODE_OPTIONS', '').strip()
        env['NODE_OPTIONS'] = f'{existing} --import={policy}'.strip()
    os.chdir(SOURCE)
    os.execve(NODE, [str(NODE), str(SOURCE / 'scripts/run-node.mjs'),
                     '--dev', *arguments], env)


if __name__ == '__main__':
    launch(sys.argv[1:])
