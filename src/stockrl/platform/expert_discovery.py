"""Public model discovery: inspect tensor headers before downloading frozen weights."""
import json
import re
import struct
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote
import requests
from huggingface_hub import HfApi
from .expert_packages import load_package
from .native_upgrade import weight_signature,match_signature
from .expert_search_metadata import annotate

FINANCE_QUERIES=('FinText','FinRL','finance','financial','MarketGPT','Chronos','TimesFM','Kronos','FinCast','Time-MoE')


def discover_repositories(api,payload,progress):
    query=str(payload.get('query') or '').strip()[:100]
    queries=[query] if query else list(FINANCE_QUERIES)
    errors=[];repos={}
    def fetch(term):
        try:
            popular=list(api.list_models(search=term,sort='downloads',direction=-1,limit=12 if query else 2,full=True))
            recent=[] if query else list(api.list_models(search=term,sort='lastModified',direction=-1,limit=1,full=True))
            return popular+recent,None
        except Exception as exc:return [],dict(query=term,detail=str(exc)[:300])
    with ThreadPoolExecutor(max_workers=3) as executor:
        for index,(values,error) in enumerate(executor.map(fetch,queries)):
            for repo in values:repos.setdefault(repo.id,repo)
            if error:errors.append(error)
            progress(stage='searching',completed=index+1,total=len(queries),detail=f'금융·시장 시계열 검색 {index+1}/{len(queries)}')
    if not repos and errors:raise ValueError('공개 검색 서버 연결 실패: '+errors[0]['detail'])
    return query or '금융 Expert 자동 검색',queries,list(repos.values()),errors


def tensor_header(url):
    with requests.get(url,headers={'Range':'bytes=0-1048575'},stream=True,timeout=(10,20)) as response:
        response.raise_for_status();raw=response.raw
        length=struct.unpack('<Q',raw.read(8))[0]
        if not 2<=length<=1048568:raise ValueError('지원 범위를 벗어난 tensor header 크기')
        body=raw.read(length)
        if len(body)!=length:raise ValueError('tensor header가 완전히 수신되지 않았습니다.')
    header=json.loads(body)
    return {k:v['shape'] for k,v in header.items() if k!='__metadata__'}


def templates(settings,catalog):
    result={}
    for key,item in catalog['experts'].items():
        if item['role']!='market' or item.get('conversion') or not item['input']['supported']:continue
        package=load_package(settings.resolve(settings.expert_checkpoint),item['package'])
        signature=weight_signature(package)
        if signature:result[key]=dict(item=item,signature=signature,entry=package['entry'],active=key in catalog.get('active',[]))
    return result


def search(settings,catalog,payload,progress):
    api=HfApi(token=False);known=templates(settings,catalog)
    stored={};installed={}
    for key,item in catalog['experts'].items():
        if item.get('conversion'):continue
        try:origin=load_package(settings.resolve(settings.expert_checkpoint),item['package'])['entry'].get('origin')
        except (OSError,ValueError):continue
        if origin:
            stored[(origin.get('repository'),origin.get('revision'))]=key
            installed.setdefault(origin.get('repository'),[]).append(dict(id=key,name=item['name'],revision=origin.get('revision'),active=key in catalog.get('active',[])))
    query,keywords,repos,errors=discover_repositories(api,payload,progress)
    import psutil
    available_ram=max(0,psutil.virtual_memory().available-settings.resources.ram_reserve_gib*2**30)
    def inspect(repo):
        row=dict(id=repo.id+'@'+repo.sha,repository=repo.id,revision=repo.sha,
            updated=repo.last_modified.isoformat() if repo.last_modified else None,
            downloads=repo.downloads or 0,url='https://huggingface.co/'+repo.id,compatible=False)
        try:
            info=api.model_info(repo.id,revision=repo.sha,files_metadata=True,timeout=20)
            if info.gated or info.private:raise ValueError('공개 접근 가능한 가중치가 아닙니다.')
            files=[]
            for sibling in info.siblings:
                name=sibling.rfilename
                if name.endswith(('.safetensors','.pt','.pth','.ckpt','.bin','.gguf','.zip','.tflite')) and not any(w in name.lower() for w in ('optimizer','training_args','scheduler')):
                    lfs=getattr(sibling,'lfs',None)
                    files.append(dict(name=name,bytes=sibling.size or 0,sha256=getattr(lfs,'sha256',None),
                        url='https://huggingface.co/'+repo.id+'/resolve/'+repo.sha+'/'+quote(name,safe='/')))
            safe=[f for f in files if f['name'].endswith('.safetensors')]
            selected=safe or files[:1]
            row.update(files=selected,bytes=sum(f['bytes'] for f in selected) or None,
                same_weights=(repo.id,repo.sha) in stored)
            if not selected:raise ValueError('지원하는 고정 가중치 파일이 없습니다.')
            if any(f['name'].endswith(('.gguf','.tflite')) for f in selected):
                raise ValueError('파일 크기는 확인했지만 이 형식의 추론 실행기는 아직 등록돼 있지 않습니다.')
            matches=[]
            if safe:
                shapes={}
                for file in safe:
                    values=tensor_header(file['url'])
                    if set(shapes).intersection(values):raise ValueError('중복 가중치 변형이 있습니다. 원본 파일을 직접 선택하세요.')
                    shapes.update(values)
                for key,value in known.items():
                    family=re.sub('[^a-z]','',value['item']['backend'].lower())
                    identity=re.sub('[^a-z]','',repo.id.lower())
                    if family in identity and match_signature(shapes,value['signature']):matches.append(key)
                if 'chronos' in repo.id.lower():
                    from .hf_forecast import definition
                    response=requests.get('https://huggingface.co/'+repo.id+'/resolve/'+repo.sha+'/config.json',timeout=(10,20))
                    response.raise_for_status();config=response.json();native=definition(config)
                    if native:
                        kind,model=native
                        signature=weight_signature(dict(module_count=1,state_dict={'models.0.'+k:v for k,v in model.state_dict().items()}))
                        if match_signature(shapes,signature):
                            row.update(compatible=True,executor='hf_forecast',backend=kind,model_config=config,
                                parameters=sum(p.numel() for p in model.parameters()),files=selected,bytes=sum(f['bytes'] for f in selected),
                                template_name='설치된 공식 '+kind+' 추론 API',detail='공식 실행기·입력·tensor 구조 호환 · 실제 추론 검사 필요',same_weights=(repo.id,repo.sha) in stored)
                            if row['same_weights']:row['detail']='이 revision은 이미 라이브러리에 보관되어 있습니다.'
                            if matches:row['template']=matches[0]
                            return annotate(row,info,known,installed,available_ram)
            else:
                # Non-safetensors have no bounded readable shape header. Confirm after download.
                matches=[key for key,v in known.items() if v['item']['backend'].lower() in repo.id.lower()]
            if not matches:raise ValueError('현재 등록된 시장 입력·모델 구조와 호환되는 실행기가 없습니다.')
            key=matches[0];value=known[key]
            originals={f.get('sha256') for f in value['entry'].get('files',[]) if f.get('sha256')}
            checksum=value['entry'].get('checkpoint_sha256')
            if checksum:originals.add(checksum)
            same=(repo.id,repo.sha) in stored or all(f.get('sha256') in originals for f in selected)
            row.update(compatible=True,template=key,template_name=value['item']['name'],files=selected,
                bytes=sum(f['bytes'] for f in selected),same_weights=same,input=value['item']['input'],
                detail='현재 원본과 동일한 가중치' if same else '입력 템플릿·tensor 구조 호환 · 실제 추론 검사 필요' if safe else '입력 계열 지원 · 다운로드 후 tensor 구조 검사 필요')
        except Exception as exc:row['detail']=str(exc)
        return annotate(row,info,known,installed,available_ram) if 'info' in locals() else row
    models=[]
    with ThreadPoolExecutor(max_workers=3) as executor:
        for index,row in enumerate(executor.map(inspect,repos)):
            models.append(row);progress(stage='searching',completed=index+1,total=len(repos),detail=f'공개 모델 입력·가중치 구조 검사 · {index+1}/{len(repos)}')
    if not payload.get('query'):
        models=[m for m in models if m.get('financial_relevance',False) or m.get('compatible',False)]
    models.sort(key=lambda r:(not r['compatible'],r.get('same_weights',False),-r['downloads']))
    return dict(query=query,keywords=keywords,errors=errors,models=models,source='Hugging Face 공개 API',
        scope='입력·구조 호환성을 확인한 후보입니다. 실제 추론·자원 검사를 통과한 뒤 사용할 수 있으며 수익 성능을 보장하지 않습니다.')


def candidate(catalog,payload):
    values=catalog.get('discovery',{}).get('models',[])
    item=next((m for m in values if m['id']==payload.get('id')),None)
    if not item or not item['compatible']:raise ValueError('검색에서 입력 호환성을 확인한 후보를 선택하세요.')
    if item.get('same_weights'):raise ValueError('이미 보유한 원본과 동일한 가중치입니다.')
    return item


def slot_name(item,catalog):
    stem=re.sub('[^a-z0-9_]','_',item['repository'].lower())[:58]
    if not stem or not stem[0].isalpha():stem='expert_'+stem
    value=stem+'_'+item['revision'][:8];index=2
    while value in catalog['experts']:value=stem+'_'+item['revision'][:8]+'_'+str(index);index+=1
    return value[:80]
