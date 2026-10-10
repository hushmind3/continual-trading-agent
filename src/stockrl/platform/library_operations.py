"""Recovered library job interface; delegate to existing modules, not old learners."""
import threading
import time
from pathlib import Path
from ..state_io import atomic_json,read_json
from .operations_settings import settings
from .operations_runtime import runtime

class LibraryOperations:
    def __init__(self):
        self.lock=threading.Lock();self.active=False
        self.cancelled=threading.Event()
        self.status_path=settings().state_dir/'library-job.json'
        self.catalog_path=settings().registry_file

    def snapshot(self):
        return dict(catalog=read_json(self.catalog_path),job={**read_json(self.status_path),'busy':self.active})

    def start(self,kind,payload):
        if kind not in ('inspect','import','probe','probe_all','load','unload','search','acquire','convert','optimize','optimize_all','apply','compare'):
            raise ValueError('지원하는 Expert 작업을 선택하세요.')
        with self.lock:
            if self.active:raise ValueError('진행 중인 Expert 작업이 있습니다.')
            self.cancelled.clear();runtime.cancel_inference.clear()
            self.active=True
            atomic_json(dict(stage='queued',kind=kind,started=time.time()),self.status_path)
            threading.Thread(target=self._run,args=(kind,payload),name='expert-library-operation',daemon=True).start()
        return self.snapshot()

    def _run(self,kind,payload):
        def progress(**values):
            if self.cancelled.is_set():raise InterruptedError('사용자가 모델 작업 중지를 요청했습니다.')
            atomic_json(dict(kind=kind,**values),self.status_path)
        try:
            result=self._execute(kind,payload,progress)
            if self.cancelled.is_set():raise InterruptedError('모델 작업 중지 요청을 반영했습니다. 이미 생성된 결과물은 보존합니다.')
            partial=isinstance(result,dict) and bool(result.get('failed',0))
            atomic_json(dict(stage='partial' if partial else 'complete',kind=kind,result=result,
                error=str(result['failed'])+'개 Expert 작업 실패' if partial else None,finished=time.time()),self.status_path,
                default=lambda x:x.tolist() if hasattr(x,'tolist') else str(x))
        except Exception as exc:
            atomic_json(dict(stage='error',kind=kind,error=str(exc),finished=time.time()),self.status_path)
        finally:self.active=False

    def _execute(self,kind,payload,progress):
        cfg=settings();catalog=read_json(cfg.registry_file)
        if kind in ('probe_all','optimize_all'):
            keys=list(catalog.get('experts',{})) if kind=='probe_all' else list(catalog.get('active',[]))
            if not keys:raise ValueError('검사할 등록 Expert가 없습니다.' if kind=='probe_all' else '사용 중인 Expert가 없습니다.')
            results=[]
            for index,key in enumerate(keys,1):
                if self.cancelled.is_set():raise InterruptedError('Expert 일괄 작업 중지를 요청했습니다.')
                progress(stage=kind,detail=f'{index}/{len(keys)} · {key}')
                item=catalog['experts'][key]
                if kind=='optimize_all' and (item.get('conversion') or item.get('executor')=='llama_cpp' or not item.get('input',{}).get('supported',False)):
                    results.append(dict(id=key,status='skipped',detail='원본 변환 불가 또는 입력 미지원'))
                    continue
                was_loaded=bool(runtime.pool and key in runtime.pool.loaded)
                try:
                    if kind=='probe_all':
                        runtime.infer(key)
                    else:
                        self._execute('optimize',{'id':key,'goal':'memory','device':'auto'},progress)
                    results.append(dict(id=key,status='passed'))
                except InterruptedError:
                    raise
                except Exception as exc:
                    results.append(dict(id=key,status='failed',detail=str(exc)))
                finally:
                    if kind=='probe_all' and not was_loaded:runtime.unload(key)
            return {'total':len(keys),'passed':sum(x['status']=='passed' for x in results),
                'failed':sum(x['status']=='failed' for x in results),
                'skipped':sum(x['status']=='skipped' for x in results),'items':results}
        if kind=='compare':
            from .expert_comparison import comparison_result,measure
            keys=[payload['baseline'],payload['variant']];items={key:catalog['experts'][key] for key in keys}
            if items[keys[0]]['input']!=items[keys[1]]['input'] or items[keys[0]]['feature_size']!=items[keys[1]]['feature_size']:
                raise ValueError('동일한 입력 계약·출력 크기의 모델을 비교하세요.')
            fixture=runtime.fixture(keys[0]);results=[]
            for key in keys:
                progress(stage='comparison',detail=key);results.append(measure(runtime,key,fixture))
            result=comparison_result(items,results,fixture);catalog['comparison']=result
            atomic_json(catalog,cfg.registry_file);return result
        if kind=='apply':
            from ..expert_registry_native import ExpertRegistry
            ExpertRegistry().select(payload['active'])
            return {'active':payload['active']}
        if kind=='load':return runtime.load(payload['id'])
        if kind=='unload':runtime.unload(payload['id']);return {'unloaded':payload['id']}
        if kind=='probe':return runtime.infer(payload['id'])
        if kind=='search':
            from .expert_discovery import search
            result=search(cfg,catalog,payload,progress)
            catalog['discovery']=result;atomic_json(catalog,cfg.registry_file)
            return result
        if kind=='inspect':
            from .library_store import inspect_source
            path=Path(payload['source']).expanduser().resolve()
            return {'source':str(path),'experts':inspect_source(path,cfg,catalog)}
        if kind in ('import','acquire','convert'):
            if kind=='acquire':
                from .expert_acquisition import acquire
                item,_=acquire(cfg,catalog,payload,progress)
            elif kind=='convert':
                from .expert_conversion import convert
                item=convert(cfg,catalog,payload,progress)
            else:
                from .library_store import import_package,fetch_source
                slot=payload['slot']
                if slot in catalog['experts']:raise ValueError('사용 중인 슬롯 이름입니다.')
                path=fetch_source(cfg,payload['source'],progress)
                from .native_upgrade import read_native
                from .expert_packages import PACKAGE_FORMAT,HEADER_FORMAT,digest,package_path,load_package
                saved=read_json(path) if path.suffix.lower()=='.json' else read_native(path) if path.suffix.lower()!='.gguf' else {}
                if path.is_relative_to(cfg.model_dir.resolve()) and saved.get('format')==PACKAGE_FORMAT:
                    from .expert_contracts import descriptor,input_contract
                    contract=input_contract(saved['entry'])
                    if not contract['supported']:raise ValueError(contract['reason'])
                    item=descriptor(slot,saved,{'file':path.relative_to(cfg.model_dir).as_posix(),
                        'sha256':digest(path),'bytes':path.stat().st_size})
                elif saved.get('format')==HEADER_FORMAT and payload.get('expert_id') in saved.get('expert_packages',{}):
                    from .expert_contracts import descriptor
                    reference=saved['expert_packages'][payload['expert_id']]
                    package=load_package(path,reference,verify=True)
                    original=package_path(path,reference)
                    item=descriptor(slot,package,{**reference,'file':original.relative_to(cfg.model_dir).as_posix()})
                else:
                    item=import_package(cfg,path,payload.get('expert_id'),slot,progress,
                        template=catalog['experts'].get(payload.get('template')))
            catalog=read_json(cfg.registry_file)
            catalog.setdefault('experts',{})[item['id']]=item
            if payload.get('activate',kind=='acquire'):
                catalog['active']=sorted(set([*catalog.get('active',[]),item['id']]))
            atomic_json(catalog,cfg.registry_file)
            return item
        if kind=='optimize':
            from .expert_optimizer import best_precision
            from .expert_comparison import comparison_result,measure
            from .expert_conversion import convert,quality_check
            base=payload['id'];fixture=runtime.fixture(base)
            first=measure(runtime,base,fixture)
            rows=[{'id':base,'precision':catalog['experts'][base].get('representation','original'),
                'passed':True,'bytes':catalog['experts'][base]['package']['bytes'],'measurement':first}]
            for precision in payload.get('precisions',['nf4','int4','int8']):
                slot=base+'_'+precision
                if slot not in catalog['experts']:
                    item=convert(cfg,catalog,{'id':base,'precision':precision,'slot':slot,
                        'device':payload.get('device','auto')},progress)
                    catalog['experts'][slot]=item;atomic_json(catalog,cfg.registry_file)
                variant=measure(runtime,slot,fixture)
                compared=comparison_result({base:catalog['experts'][base],slot:catalog['experts'][slot]},[first,variant],fixture)
                item=catalog['experts'][slot]
                item['check']={'status':'passed','detail':'동일 실제 입력의 유한 출력 확인'}
                quality_check(item,compared,payload)
                rows.append({'id':slot,'precision':precision,'passed':item['check']['status']=='passed',
                    'bytes':item['package']['bytes'],'measurement':variant,'detail':item['check']['detail']})
            from .resources import ResourceMonitor
            resources=ResourceMonitor(cfg.state_dir).snapshot({})
            selected=best_precision(rows,base,payload.get('goal','memory'),
                resources['ram_total_bytes'],resources['gpu'].get('total_bytes',1))
            catalog.setdefault('optimizations',{})[base]={'stage':'complete','selected':selected['id'],'reports':rows}
            atomic_json(catalog,cfg.registry_file)
            return catalog['optimizations'][base]

library=LibraryOperations()
