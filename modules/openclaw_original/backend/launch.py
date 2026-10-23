"""Start the official OpenClaw CLI with a private state directory."""
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'runtime/ai_agent/OpenClawOriginal'
SOURCE = BASE / 'source'
HOME = BASE / 'home'
NODE = BASE / 'tools/node/bin/node'


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
        policy = Path(__file__).resolve().with_name('frame_policy.mjs')
        existing = env.get('NODE_OPTIONS', '').strip()
        env['NODE_OPTIONS'] = f'{existing} --import={policy}'.strip()
    os.chdir(SOURCE)
    os.execve(NODE, [str(NODE), str(SOURCE / 'scripts/run-node.mjs'),
                     '--dev', *arguments], env)


if __name__ == '__main__':
    launch(sys.argv[1:])
