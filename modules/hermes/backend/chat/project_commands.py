"""Shell-free npm commands in a connected organization's owned workspace."""
import json
import os
from pathlib import Path
import re
import subprocess
import time
from platform_native import npm_command


def run(worker, args):
    try:
        root = Path(worker.company_link['workspace']).resolve()
        folder = Path(args['workspace']).resolve()
        if not folder.is_relative_to(root) or not folder.is_dir(): raise ValueError('회사 작업 폴더 안에서만 실행할 수 있습니다.')
        action = args['action']
        if action != 'versions' and not (folder / 'package.json').is_file(): raise ValueError('선택 폴더에 package.json이 없습니다.')
        packages = args.get('packages', [])
        if not isinstance(packages, list) or len(packages)>20 or any(not isinstance(p,str) or not re.fullmatch(r'(@[a-z0-9][a-z0-9._-]*/)?[a-z0-9][a-z0-9._-]*(@[a-zA-Z0-9.*^~+_-]+)?',p) for p in packages):
            raise ValueError('npm 패키지 이름과 버전을 확인하세요.')
        commands = {'versions': ['--version'], 'install': ['install', *(['--save-dev'] if args.get('development') else []), *packages],
                    'test': ['test', '--', '--run'], 'build': ['run', 'build'], 'package_info': ['view', *packages, 'version']}
        if action not in commands or action == 'package_info' and len(packages)!=1: raise ValueError('지원하지 않는 npm 요청입니다.')
        command = [*npm_command(), *commands[action]]
        process = subprocess.Popen(command, cwd=folder, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding='utf-8', errors='replace', creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        start=time.monotonic(); failure=None
        try:
            while True:
                try: output,_=process.communicate(timeout=.4);break
                except subprocess.TimeoutExpired:
                    if worker.stopping: raise InterruptedError('소유자가 npm 실행을 중지했습니다.')
                    if time.monotonic()-start>240: raise TimeoutError('npm 실행이 240초를 초과했습니다. 실제 출력으로 원인을 확인하세요.')
        except BaseException as exc:
            import psutil
            try:
                for child in psutil.Process(process.pid).children(recursive=True):
                    try:child.kill()
                    except psutil.NoSuchProcess:pass
            except psutil.NoSuchProcess:pass
            process.kill();output,_=process.communicate()
            if not isinstance(exc,(TimeoutError,InterruptedError)):raise
            failure=str(exc)
        result={'workspace':str(folder),'action':action,'command':command,'exit_code':process.returncode,
                'seconds':round(time.monotonic()-start,2),'output':output[-12000:]}
        if failure:result['error']=failure
        if action in ('test','build'):
            receipt=folder/'verification'/('npm-'+action+'.json');receipt.parent.mkdir(exist_ok=True)
            receipt.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');result['receipt']=str(receipt)
        return json.dumps(result,ensure_ascii=False)
    except Exception as exc:return json.dumps({'error':str(exc)},ensure_ascii=False)


SCHEMA={'name':'project_npm','description':'Run actual npm commands in a connected company workspace WITHOUT shell quoting or cd. Prefer this for Node install/test/build. Pass the exact workspace returned by company_records begin. Returns actual exit code/output; test/build also save receipts. This is one tool action, not an AI engine.',
 'parameters':{'type':'object','properties':{'workspace':{'type':'string'},'action':{'type':'string','enum':['versions','package_info','install','test','build']},'packages':{'type':'array','items':{'type':'string'}},'development':{'type':'boolean'}},'required':['workspace','action'],'additionalProperties':False}}
