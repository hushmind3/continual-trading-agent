"""Existing 8766 launcher: incremental apply/check, then the shared start API."""
from __future__ import annotations
from contextlib import contextmanager
import argparse,hashlib,json,os,shutil,subprocess,sys,time,uuid
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import psutil
ROOT=Path(__file__).resolve().parents[1]
FRONTEND=ROOT/'frontend';RUNTIME=ROOT/'runtime/official';PORT=8766
sys.path.insert(0,str(ROOT/'src'))
from stockrl.state_io import read_json,atomic_json
APPLY=RUNTIME/'apply.json';APPLIED=RUNTIME/'applied-sources.json'


def same_path(left,right):
    return os.path.normcase(str(Path(left).resolve()))==os.path.normcase(str(Path(right).resolve()))


def classify(process):
    command=process.cmdline()
    if same_path(process.cwd(),ROOT) and 'stockrl.web_api:app' in command and 'uvicorn' in command:return 'api'
    return None


def listeners(port):
    records=[]
    for connection in psutil.net_connections(kind='tcp'):
        if connection.status!=psutil.CONN_LISTEN or connection.laddr.port!=port:continue
        if connection.pid is None:raise RuntimeError(f'{port} 포트 소유권 확인 실패')
        process=psutil.Process(connection.pid);kind=classify(process)
        if kind is None:raise RuntimeError(f'{port} 포트는 이 프로젝트 서버가 아닙니다. PID {process.pid}; 종료하지 않았습니다.')
        records.append((process.pid,process.create_time(),kind))
    return list(dict.fromkeys(records))


def stop_verified(record):
    pid,created,kind=record
    try:
        process=psutil.Process(pid)
        if abs(process.create_time()-created)>.01 or classify(process)!=kind:raise RuntimeError(f'PID {pid} 소유권 변경; 종료하지 않았습니다.')
        # No active inference reaches this point. Reap only this API's verified idle GGUF children.
        for child in process.children(recursive=True):
            try:
                command=child.cmdline();executable=Path(command[0]).resolve() if command else None
                if executable and executable.name.lower()=='llama-server.exe' and executable.is_relative_to((ROOT/'runtime').resolve()):
                    child_created=child.create_time()
                    if child.ppid()==pid and abs(psutil.Process(child.pid).create_time()-child_created)<.01:
                        child.terminate();child.wait(timeout=5)
            except psutil.NoSuchProcess:pass
        process.terminate()
        try:process.wait(timeout=5)
        except psutil.TimeoutExpired:
            if abs(process.create_time()-created)>.01 or classify(process)!=kind:raise RuntimeError(f'PID {pid} 재확인 실패')
            process.kill();process.wait(timeout=3)
    except psutil.NoSuchProcess:pass


def api(path,body=None,timeout=30):
    request=Request(f'http://127.0.0.1:{PORT}/api/'+path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={'Content-Type':'application/json'})
    with urlopen(request,timeout=timeout) as response:return json.load(response)


def ready():
    try:
        value=api('health',timeout=2)
        return value.get('service')=='finrlx-react-sac' and same_path(value.get('project',''),ROOT)
    except (OSError,ValueError):return False


@contextmanager
def startup_lock():
    import msvcrt
    RUNTIME.mkdir(parents=True,exist_ok=True)
    with (RUNTIME/'server-start.lock').open('a+b') as handle:
        if handle.tell()==0:handle.write(b'.');handle.flush()
        deadline=time.monotonic()+60
        while True:
            try:handle.seek(0);msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1);break
            except OSError:
                if time.monotonic()>=deadline:raise RuntimeError('다른 변경 적용 작업이 진행 중입니다.')
                time.sleep(.1)
        try:yield
        finally:handle.seek(0);msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)


def sources():
    names=set(subprocess.check_output(['git','ls-files','-co','--exclude-standard','-z'],cwd=ROOT).decode('utf8').split('\0'))
    groups={name:{} for name in ('frontend','backend','launcher','configuration')}
    for name in sorted(names):
        if name.startswith('frontend/src/') or name in ('frontend/index.html','frontend/package.json','frontend/package-lock.json','frontend/tsconfig.json','frontend/vite.config.ts'):group='frontend'
        elif name.startswith('src/stockrl/') and name.endswith('.py') or name.startswith('requirements/'):group='backend'
        elif name.startswith('scripts/') and name.endswith('.py') or name=='서버켜기.cmd':group='launcher'
        elif name in ('configs/experts.json','configs/instruments.json'):group='configuration'
        else:continue
        path=ROOT/name
        groups[group][name]=hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else 'missing'
    revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    groups['backend']['FinRL-X']=subprocess.check_output(['git','-C','FinRL-X','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    return groups,revision


def blockers():
    try:return api('system/blockers',timeout=5)['items']
    except HTTPError as exc:
        if exc.code!=404:raise
        # Initial installation: reuse the pre-existing state endpoint before new routes exist.
        value=api('state');items=[]
        if value.get('job',{}).get('running'):items.append('실행 중인 SAC/평가/수집 작업')
        if any(value.get('operations',{}).get('controls',{}).values()):items.append('실행 중인 시세/추론/가상매매')
        if value.get('library',{}).get('job',{}).get('busy'):items.append('실행 중인 모델 작업')
        return items


def main(apply_only=False):
    with startup_lock():
        operation={'id':uuid.uuid4().hex,'pid':os.getpid(),'process_created':psutil.Process().create_time(),
            'status':'running','started_at':time.time(),'stages':[]}
        def phase(key,title,status='running',detail='',**values):
            row=next((row for row in operation['stages'] if row['id']==key),None)
            if row is None:row={'id':key,'title':title};operation['stages'].append(row)
            row.update(status=status,detail=detail,**values);atomic_json(operation,APPLY)
        stage='changes'
        try:
            phase(stage,'변경 소스 확인')
            current=listeners(PORT);previous=listeners(8767)
            live=bool(current and ready());before=read_json(APPLIED)
            groups,revision=sources();old=before.get('sources',{})
            changed=sorted({name for group,rows in groups.items() for name in set(rows)|set(old.get(group,{})) if rows.get(name)!=old.get(group,{}).get(name)})
            operation.update(changed_files=changed,revision=revision)
            frontend_changed=groups['frontend']!=old.get('frontend') or not (FRONTEND/'dist/index.html').is_file()
            backend_changed=groups['backend']!=old.get('backend')
            if before.get('dist_sha256') and (FRONTEND/'dist/index.html').is_file():
                frontend_changed|=hashlib.sha256((FRONTEND/'dist/index.html').read_bytes()).hexdigest()!=before['dist_sha256']
            phase(stage,'변경 소스 확인','complete',f'{len(changed)}개 변경; 프론트 빌드 {frontend_changed}, 서버 갱신 {backend_changed or not live}')
            stage='preserve';phase(stage,'실행 중 작업 보존')
            active=blockers() if live else []
            if active and (frontend_changed or backend_changed):
                phase(stage,'실행 중 작업 보존','blocked',' · '.join(active)+'; 변경 적용 보류')
                operation['status']='blocked';atomic_json(operation,APPLY);return
            phase(stage,'실행 중 작업 보존','complete','기존 작업을 종료하지 않았습니다.')
            stage='build';phase(stage,'React 변경 적용')
            if frontend_changed:
                node=shutil.which('node');vite=FRONTEND/'node_modules/vite/bin/vite.js';tsc=FRONTEND/'node_modules/typescript/bin/tsc'
                if not node or not vite.is_file() or not tsc.is_file():raise RuntimeError('설치된 Node/Vite/TypeScript가 필요합니다. 패키지를 자동 설치하지 않습니다.')
                log=RUNTIME/'apply-build.log';operation['build_log']=str(log)
                with log.open('w',encoding='utf8') as output:
                    for script,args in ((tsc,['--noEmit']),(vite,['build','--emptyOutDir','false'])):
                        subprocess.run([node,str(script),*args],cwd=FRONTEND,stdout=output,stderr=subprocess.STDOUT,check=True)
                if not (FRONTEND/'dist/index.html').is_file():raise RuntimeError('React 빌드 산출물이 없습니다.')
                phase(stage,'React 변경 적용','complete','변경된 소스 빌드 완료; 기존 산출물은 영구 삭제하지 않았습니다.')
            else:phase(stage,'React 변경 적용','complete','변경 없음; 빌드 생략')
            stage='server';phase(stage,'8766 서버 갱신')
            restart=backend_changed or not live
            if live and restart:
                active=blockers()
                if active:
                    phase(stage,'8766 서버 갱신','blocked',' · '.join(active)+'; 새 소스는 미적용')
                    operation['status']='blocked';atomic_json(operation,APPLY);return
                if 'src/stockrl/platform/system_operations.py' in old.get('backend',{}):
                    # Persist server approval waiting separately from running application work.
                    operation['status']='pending';phase(stage,'8766 서버 갱신','pending','서버 재시작 준비 승인 대기')
                    api('system/prepare-restart',{})
                    api('operations')  # Await existing account/model locks before terminating the idle API.
                    operation['status']='running';phase(stage,'8766 서버 갱신')
            if restart:
                for record in current:stop_verified(record)
                env=os.environ.copy();env.update(PYTHONPATH=str(ROOT/'src'),PYTHONUTF8='1',STOCKRL_APPLY_ID=operation['id'])
                with (RUNTIME/'server.stdout.log').open('ab') as output,(RUNTIME/'server.stderr.log').open('ab') as errors:
                    child=subprocess.Popen([sys.executable,'-m','uvicorn','stockrl.web_api:app','--host','127.0.0.1','--port',str(PORT)],cwd=ROOT,env=env,stdout=output,stderr=errors,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                for _ in range(100):
                    if child.poll() is not None:raise RuntimeError('서버 시작 실패: runtime/official/server.stderr.log')
                    if ready():break
                    time.sleep(.1)
                else:raise RuntimeError('8766 서버 응답 대기 실패')
                if api('health').get('deployment_id')!=operation['id']:raise RuntimeError('실행 서버가 새 적용 ID와 일치하지 않습니다.')
            actual=listeners(PORT)
            atomic_json({'project':str(ROOT),'port':PORT,'pid':actual[0][0],'process_created':actual[0][1],'service':'finrlx-react-sac'},RUNTIME/'server.json')
            for record in previous:stop_verified(record)
            phase(stage,'8766 서버 갱신','complete','새 코드로 서버 갱신' if restart else '백엔드 변경 없음; 기존 서버 사용')
            stage='react';phase(stage,'React · FastAPI 응답 확인')
            with urlopen(f'http://127.0.0.1:{PORT}/',timeout=10) as response:
                html=response.read().decode('utf8')
            if 'id="root"' not in html or '/assets/' not in html:raise RuntimeError('8766에서 React 정적 페이지를 확인하지 못했습니다.')
            phase(stage,'React · FastAPI 응답 확인','complete','8766 React HTML 및 현재 API 응답 확인; 브라우저 화면 테스트는 수행하지 않았습니다.')
            refreshed,_=sources()
            if refreshed!=groups:raise RuntimeError('적용 도중 소스가 다시 변경됐습니다. 현재 변경은 적용 완료로 기록하지 않습니다.')
            atomic_json({'sources':groups,'revision':revision,'applied_at':time.time(),
                'dist_sha256':hashlib.sha256((FRONTEND/'dist/index.html').read_bytes()).hexdigest()},APPLIED)
            stage='check';phase(stage,'전체 연결 상태 확인')
            checked=api('system/check',timeout=60)
            operation['checks']=checked['items']
            issues=[row for row in checked['items'] if row['status'] in ('failed','blocked')]
            phase(stage,'전체 연결 상태 확인','blocked' if issues else 'complete',f'{len(issues)}개 준비 부족/오류' if issues else '요청한 상태 항목 확인')
            operation.update(status='blocked' if issues else 'complete',applied=True,finished_at=time.time())
            atomic_json(operation,APPLY)
            print('변경 적용 완료; '+('준비 부족 항목 있음' if issues else '상태 조회 완료'),flush=True)
        except Exception as exc:
            detail=str(exc);log=RUNTIME/'apply-build.log' if stage=='build' else RUNTIME/'server.stderr.log'
            if isinstance(exc,HTTPError):detail+='\n'+exc.read().decode('utf8',errors='replace')[:1200]
            if log.exists():
                with log.open('rb') as stream:
                    stream.seek(max(0,log.stat().st_size-6000));detail+='\n'+stream.read().decode('utf8',errors='replace')
            phase(stage, next((row['title'] for row in operation['stages'] if row['id']==stage),stage),'failed',detail,log_path=str(log))
            operation.update(status='failed',finished_at=time.time());atomic_json(operation,APPLY)
            raise
    if not apply_only:
        result=api('system/start',{})
        print('전체 시스템 시작 요청: '+result.get('status',''),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--apply-only',action='store_true')
    args=parser.parse_args()
    try:main(args.apply_only)
    except (OSError,RuntimeError,ValueError,subprocess.SubprocessError,psutil.Error) as exc:
        print(str(exc),file=sys.stderr);raise SystemExit(1)
