"""Recovered library job interface; delegate to existing modules, not old learners."""
import threading
import time
from pathlib import Path
from ..state_io import atomic_json,read_json
from .operations_settings import settings
from .operations_runtime import runtime
from .observations import InputUnavailable

class LibraryOperations:
    def __init__(self):
        self.lock=threading.Lock();self.active=False
        self.cancelled=threading.Event()
        self.status_path=settings().state_dir/'library-job.json'
        self.catalog_path=settings().registry_file

    def snapshot(self):
        return dict(catalog=read_json(self.catalog_path),job={**read_json(self.status_path),'busy':self.active})

    def start(self,kind,payload):
        if kind not in ('inspect','import','probe','probe_all','load','unload','remove','search','acquire','convert','optimize','optimize_all','apply','compare'):
            raise ValueError('지원하는 Expert 작업을 선택하세요.')
        with self.lock:
            if self.active:raise ValueError('진행 중인 Expert 작업이 있습니다.')
            self.cancelled.clear();runtime.cancel_inference.clear()
            self.active=True
            atomic_json(dict(stage='queued',kind=kind,detail=kind+(' · '+str(payload['id']) if payload.get('id') else ''),started=time.time()),self.status_path)
            threading.Thread(target=self._run,args=(kind,payload),name='expert-library-operation',daemon=True).start()
        return self.snapshot()

    def _run(self,kind,payload):
        started=read_json(self.status_path).get('started',time.time())
        def progress(**values):
            if self.cancelled.is_set():raise InterruptedError('사용자가 모델 작업 중지를 요청했습니다.')
            atomic_json(dict(kind=kind,started=started,**values),self.status_path)
        try:
            result=self._execute(kind,payload,progress)
            if self.cancelled.is_set():raise InterruptedError('모델 작업 중지 요청을 반영했습니다. 이미 생성된 결과물은 보존합니다.')
            partial=isinstance(result,dict) and bool(result.get('failed',0) or result.get('skipped',0))
            atomic_json(dict(stage='partial' if partial else 'complete',kind=kind,result=result,started=started,
                error=(result.get('detail') or str(result['failed'])+'개 모델 작업 실패') if result.get('failed') else None,finished=time.time()),self.status_path,
                default=lambda x:x.tolist() if hasattr(x,'tolist') else str(x))
        except InterruptedError as exc:
            atomic_json(dict(stage='stopped',kind=kind,detail=str(exc),started=started,finished=time.time()),self.status_path)
        except Exception as exc:
            if kind=='convert' and payload.get('id') and payload.get('precision'):
                latest=read_json(self.catalog_path);base=payload['id'];precision=payload['precision']
                if base in latest.get('experts',{}):
                    record=latest.setdefault('optimizations',{}).setdefault(base,{})
                    record.update(stage='partial',finished=time.time())
                    record.setdefault('attempts',{})[precision]={'status':'failed','detail':str(exc)}
                    record['failures']=[row for row in record.get('failures',[]) if row.get('precision')!=precision]+[{'precision':precision,'detail':str(exc)}]
                    atomic_json(latest,self.catalog_path)
            atomic_json(dict(stage='error',kind=kind,error=str(exc),finished=time.time()),self.status_path)
        finally:self.active=False

    def _execute(self,kind,payload,progress):
        cfg=settings();catalog=read_json(cfg.registry_file)
        if kind in ('probe_all','optimize_all'):
            experts=catalog.get('experts',{})
            if kind=='probe_all':keys=list(experts)
            else:
                keys=[]
                for expert_id,item in experts.items():
                    source=item.get('conversion',{}).get('source_id')
                    root=source if source in experts else expert_id
                    if root==expert_id:
                        for precision in ('fp16','bf16','int8','int4','nf4'):
                            suffix='_'+precision
                            if expert_id.lower().endswith(suffix) and expert_id[:-len(suffix)] in experts:
                                root=expert_id[:-len(suffix)];break
                    if root not in keys:keys.append(root)
            if not keys:raise ValueError('검사할 등록 Expert가 없습니다.' if kind=='probe_all' else '사용 중인 Expert가 없습니다.')
            shared_frame=shared_account=None
            if kind=='probe_all':
                from ..framework import prices
                shared_frame=prices('USD')
                book=runtime.ledger().snapshot()['books']['USD']
                shared_account={'currency':'USD','cash':book['cash'],'nav':book['equity'],
                    'positions':{symbol:position['quantity'] for symbol,position in book['positions'].items()}}
            results=[]
            for index,key in enumerate(keys,1):
                if self.cancelled.is_set():raise InterruptedError('Expert 일괄 작업 중지를 요청했습니다.')
                progress(stage=kind,completed=index-1,total=len(keys),detail=f'{index}/{len(keys)} · {key}')
                item=experts[key]
                if kind=='optimize_all' and (item.get('conversion') or item.get('executor')=='llama_cpp' or not item.get('input',{}).get('supported',False)):
                    results.append(dict(id=key,status='skipped',detail='원본 변환 불가 또는 입력 미지원'))
                    continue
                was_loaded=bool(runtime.pool and key in runtime.pool.loaded)
                started=time.perf_counter()
                started_at=time.time()
                if kind=='probe_all' and not item.get('input',{}).get('supported',False):
                    results.append(dict(id=key,status='skipped',detail=item.get('input',{}).get('reason','입력 계약을 지원하지 않습니다.')))
                    continue
                try:
                    if kind=='probe_all':
                        fixture=runtime.fixture(key,frame=shared_frame,account=shared_account,all_batches=True)
                        pool=runtime.expert_pool()
                        preferences=pool.settings.resources.expert_devices
                        pool.settings.resources.expert_devices={**preferences,key:'auto'}
                        try:inference=runtime.infer(key,fixture)
                        finally:pool.settings.resources.expert_devices=preferences
                        result=dict(id=key,status='passed',metrics=inference.get('metrics'),
                            seconds=inference.get('metrics',{}).get('inference_seconds'))
                    else:
                        optimized=self._execute('optimize',{'id':key,'goal':'memory','device':payload.get('device','auto')},progress)
                        result=dict(id=key,status='failed' if optimized.get('failed') else 'skipped' if optimized.get('skipped') else 'passed',
                            detail=optimized.get('detail'))
                    results.append(result)
                except InterruptedError:
                    raise
                except InputUnavailable as exc:
                    result=dict(id=key,status='skipped',detail=str(exc),seconds=time.perf_counter()-started)
                    results.append(result)
                except Exception as exc:
                    pool=runtime.pool
                    current=dict(pool.metrics.get(key,{})) if pool else {}
                    measured=max(current.get('last_completed_at',0),current.get('last_attempted_at',0))>started_at
                    results.append(dict(id=key,status='failed',detail=str(exc),seconds=time.perf_counter()-started,
                        **({'metrics':current} if measured else {})))
                finally:
                    if kind=='probe_all' and not was_loaded:runtime.unload(key)
            if kind=='probe_all':
                latest=read_json(cfg.registry_file)
                for row in results:
                    current=latest.get('experts',{}).get(row['id'])
                    if current is not None and current.get('package')==experts[row['id']].get('package'):
                        current['check']={'status':row['status'],
                            'detail':row.get('detail','실제 입력 전체 묶음 추론·출력 계약 통과'),
                            'tested':time.time(),**({'metrics':row['metrics'],'seconds':row.get('seconds')} if row.get('metrics') else {})}
                atomic_json(latest,cfg.registry_file)
            progress(stage=kind,completed=len(keys),total=len(keys),detail='전체 원본 Expert 처리 완료')
            return {'total':len(keys),'passed':sum(x['status']=='passed' for x in results),
                'failed':sum(x['status']=='failed' for x in results),
                'skipped':sum(x['status']=='skipped' for x in results),'items':results}
        if kind=='compare':
            from .expert_comparison import comparison_result,measure
            keys=[payload['baseline'],payload['variant']];items={key:catalog['experts'][key] for key in keys}
            if items[keys[0]]['input']!=items[keys[1]]['input'] or items[keys[0]]['feature_size']!=items[keys[1]]['feature_size']:
                raise ValueError('동일한 입력 계약·출력 크기의 모델을 비교하세요.')
            fixture=runtime.fixture(keys[0],all_batches=True);results=[]
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
        if kind=='remove':
            ids=sorted(set(payload.get('ids',[])))
            failure_records=payload.get('failures',[])
            experts=catalog.get('experts',{})
            if not (ids or failure_records) or any(key not in experts for key in ids):raise ValueError('등록 모델 또는 실패 기록을 선택하세요.')
            optimizations=catalog.get('optimizations',{})
            for row in failure_records:
                if row.get('source_id') not in optimizations or row.get('precision') not in ('fp16','bf16','int8','int4','nf4'):
                    raise ValueError('현재 목록의 양자화 실패 기록을 선택하세요.')
            removed_precisions={(experts[key].get('conversion',{}).get('source_id'),experts[key].get('conversion',{}).get('precision')) for key in ids}
            removed_precisions.update((row['source_id'],row['precision']) for row in failure_records)
            for key in ids:runtime.unload(key)
            catalog['active']=[key for key in catalog.get('active',[]) if key not in ids]
            for key in ids:experts.pop(key)
            for source,record in list(optimizations.items()):
                precisions={precision for root,precision in removed_precisions if root==source}
                record['reports']=[row for row in record.get('reports',[]) if row.get('id') not in ids and row.get('precision') not in precisions]
                record['failures']=[row for row in record.get('failures',[]) if row.get('precision') not in precisions]
                record['attempts']={precision:value for precision,value in record.get('attempts',{}).items() if precision not in precisions}
                for field in ('selected','previous'):
                    if record.get(field) in ids:record[field]=None
                if not (record['reports'] or record['failures'] or record['attempts']):optimizations.pop(source)
            atomic_json(catalog,cfg.registry_file)
            return {'removed':ids,'removed_failures':failure_records,'model_files_preserved':True}
        if kind=='probe':
            key=payload['id'];started=time.time();metrics={}
            try:
                result=runtime.infer(key)
                result.update(id=key,status='passed')
                metrics=result.get('metrics',{})
            except InputUnavailable as exc:
                result={'id':key,'status':'skipped','skipped':1,'detail':str(exc)}
            except InterruptedError:raise
            except Exception as exc:
                result={'id':key,'status':'failed','failed':1,'detail':str(exc)}
                current=runtime.pool.metrics.get(key,{}) if runtime.pool else {}
                if max(current.get('last_completed_at',0),current.get('last_attempted_at',0))>=started:metrics=dict(current)
            latest=read_json(cfg.registry_file);entry=latest.get('experts',{}).get(key)
            if entry is not None and entry.get('package')==catalog.get('experts',{}).get(key,{}).get('package'):
                entry['check']={'status':result['status'],'detail':result.get('detail','실제 입력 전체 묶음·출력 계약 통과'),
                    'tested':time.time(),'seconds':time.time()-started,**({'metrics':metrics} if metrics else {})}
                atomic_json(latest,cfg.registry_file)
            return result
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
            if kind=='convert' and catalog.get('optimizations',{}).get(payload['id']):
                record=catalog['optimizations'][payload['id']];precision=payload['precision']
                record.setdefault('attempts',{})[precision]={'status':'complete','detail':'변환 완료 · 실제 추론 검사 전'}
                record['failures']=[row for row in record.get('failures',[]) if row.get('precision')!=precision]
            if payload.get('activate',kind=='acquire'):
                catalog['active']=sorted(set([*catalog.get('active',[]),item['id']]))
            atomic_json(catalog,cfg.registry_file)
            return item
        if kind=='optimize':
            from .expert_optimizer import best_precision,measurement_summary
            from .expert_comparison import comparison_result,measure
            from .expert_conversion import convert,quality_check
            base=payload['id'];fixture=first=None;rows=[];input_error=None;baseline_error=None
            record={'stage':'running','goal':payload.get('goal','memory'),'started':time.time(),'reports':rows,'attempts':{},'failures':[]}
            try:
                fixture=runtime.fixture(base,all_batches=True)
                first=measure(runtime,base,fixture)
                rows.append({'id':base,'precision':'original','passed':True,'status':'passed',
                    'bytes':catalog['experts'][base]['package']['bytes'],'measurement':measurement_summary(first)})
            except InputUnavailable as exc:input_error=str(exc)
            except InterruptedError:raise
            except Exception as exc:baseline_error=str(exc)
            for precision in payload.get('precisions',['nf4','int4','int8']):
                slot=base+'_'+precision
                catalog=read_json(cfg.registry_file);item=catalog['experts'].get(slot)
                record['attempts'][precision]={'status':'running','detail':'버전 생성·실제 출력 검사'}
                catalog.setdefault('optimizations',{})[base]=record;atomic_json(catalog,cfg.registry_file)
                try:
                    if item is None:
                        item=convert(cfg,catalog,{'id':base,'precision':precision,'slot':slot,
                            'device':payload.get('device','auto')},progress)
                        catalog=read_json(cfg.registry_file);catalog['experts'][slot]=item
                        catalog.setdefault('optimizations',{})[base]=record;atomic_json(catalog,cfg.registry_file)
                    if first is not None:
                        variant=measure(runtime,slot,fixture)
                        compared=comparison_result({base:catalog['experts'][base],slot:item},[first,variant],fixture)
                        item['check']={'status':'passed','detail':'동일 실제 입력 전체 묶음의 유한 출력 확인',
                            'tested':time.time(),'metrics':variant['metrics'],'seconds':variant['metrics']['inference_seconds']}
                        quality_check(item,compared,payload)
                        row={'id':slot,'precision':precision,'passed':item['check']['status']=='passed',
                            'status':'passed' if item['check']['status']=='passed' else 'failed',
                            'bytes':item['package']['bytes'],'measurement':measurement_summary(variant),'detail':item['check']['detail']}
                    else:
                        reason=input_error or baseline_error
                        item['check']={'status':'skipped','detail':'변환 완료 · 원본 비교 검사 미실행: '+str(reason)}
                        row={'id':slot,'precision':precision,'passed':False,'status':'skipped','bytes':item['package']['bytes'],'detail':item['check']['detail']}
                    rows.append(row)
                    record['attempts'][precision]={'status':'complete' if row['status']=='passed' else row['status'],'detail':row.get('detail')}
                except InterruptedError:raise
                except Exception as exc:
                    detail=str(exc);record['attempts'][precision]={'status':'failed','detail':detail}
                    if item is not None:item['check']={'status':'failed','detail':detail}
                    else:record['failures'].append({'precision':precision,'detail':detail})
                    rows.append({'id':slot,'precision':precision,'passed':False,'status':'failed','detail':detail})
                latest=read_json(cfg.registry_file)
                if item is not None:latest['experts'][slot]=item
                latest.setdefault('optimizations',{})[base]=record;atomic_json(latest,cfg.registry_file)
                catalog=latest
            from .resources import ResourceMonitor
            resources=ResourceMonitor(cfg.state_dir).snapshot({})
            measured=[row for row in rows if row.get('measurement')]
            selected=best_precision(measured,base,payload.get('goal','memory'),resources['ram_total_bytes'],resources['gpu'].get('total_bytes',1)) if first is not None else None
            failed=sum(row['status']=='failed' for row in rows);skipped=sum(row['status']=='skipped' for row in rows)
            record.update(stage='partial' if failed or skipped else 'complete',selected=selected['id'] if selected else None,
                finished=time.time(),total=len(rows),failed=failed,skipped=skipped,passed=sum(row['status']=='passed' for row in rows),
                detail=input_error or baseline_error or (str(failed)+'개 버전 실패' if failed else '버전 생성·검사 완료'))
            latest=read_json(cfg.registry_file);latest.setdefault('optimizations',{})[base]=record;atomic_json(latest,cfg.registry_file)
            return record

library=LibraryOperations()
