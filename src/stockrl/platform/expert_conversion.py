"""Create an immutable precision variant; leave the source and live MoE untouched."""
import re
import shutil
import math
import torch
import psutil
from .assets import ExpertPool
from .expert_packages import load_package,digest
from .expert_contracts import descriptor
from .model_composition import atomic_torch_save
from .quantized_linear import linear_layers,pack_weight
from .work_devices import choose_device


PRECISIONS={'fp16':torch.float16,'bf16':torch.bfloat16,'int8':8,'int4':4,'nf4':4}


def cast_tensor(value,dtype,device):
    result=torch.empty(value.shape,dtype=dtype);source=value.reshape(-1);target=result.view(-1)
    chunk=max(1,(32*2**20)//(value.element_size()+result.element_size()+1))
    for offset in range(0,source.numel(),chunk):
        converted=source[offset:offset+chunk].to(device=device,dtype=dtype)
        if not torch.isfinite(converted).all():raise ValueError('정밀도 변환에서 유효하지 않은 값 또는 오버플로가 발생했습니다.')
        target[offset:offset+chunk]=converted.cpu()
    return result


def quality_check(item,comparison,payload):
    error=float(payload.get('max_relative_rmse',.01));agreement=float(payload.get('min_action_agreement',.99))
    if not all(math.isfinite(x) and 0<=x<=1 for x in (error,agreement)):raise ValueError('허용 오차·판단 일치 기준은 0~100%입니다.')
    measured=comparison['relative_rmse'];actions=comparison['action_agreement']
    directions=comparison.get('direction_agreement')
    reference_passed=math.isfinite(measured) and measured<=error and (actions is None or actions>=agreement) and (directions is None or directions>=agreement)
    mode=payload.get('validation_mode','reference')
    if mode not in ('reference','functional'):raise ValueError('기능 검사 또는 원본 근사 검사를 선택하세요.')
    passed=reference_passed if mode=='reference' else math.isfinite(measured) and item['check'].get('status')=='passed'
    item['conversion']['validation']=dict(passed=passed,reference_passed=reference_passed,mode=mode,max_relative_rmse=error,min_action_agreement=agreement,
        relative_rmse=measured,action_agreement=actions,direction_agreement=directions,input_sha256=comparison['input_sha256'])
    item['conversion']['comparison']={k:v for k,v in comparison.items() if k not in ('baseline','variant')}
    for side in ('baseline','variant'):
        item['conversion']['comparison'][side]={k:v for k,v in comparison.get(side,{}).items() if k not in ('packet','outputs','weight_files')}
    reasons=[]
    if not math.isfinite(measured) or measured>error:reasons.append(f'상대 RMSE {measured:.2%} > {error:.2%}')
    if actions is not None and actions<agreement:reasons.append(f'판단 일치 {actions:.2%} < {agreement:.2%}')
    if directions is not None and directions<agreement:reasons.append(f'예측방향 일치 {directions:.2%} < {agreement:.2%}')
    if not passed:item['check'].update(status='quality_warning',detail=' · '.join(reasons)+' · 적용 차단')
    elif mode=='functional':item['check'].update(status='passed',detail='실제 입력·출력·고정 가중치 기능 검사 통과'+(' · 원본 차이: '+' · '.join(reasons) if reasons else ' · 원본 근사 기준도 통과'))
    elif item['check'].get('status')=='quality_warning':item['check'].update(status='passed',detail='실제 추론·설정한 출력 차이 기준 통과')


def convert(settings,catalog,payload,progress):
    key=payload.get('id');precision=payload.get('precision','fp16');slot=payload.get('slot','')
    if key not in catalog['experts']:raise ValueError('변환할 Expert를 선택하세요.')
    if precision not in PRECISIONS:raise ValueError('FP16/BF16/INT8/INT4/NF4 중에서 선택하세요.')
    if not re.fullmatch(r'[a-z][a-z0-9_]{0,79}',slot) or slot in dir(torch.nn.ModuleDict()):raise ValueError('올바른 새 슬롯 이름을 지정하세요.')
    if slot in catalog['experts']:raise ValueError('이미 등록된 슬롯 이름입니다.')
    item=catalog['experts'][key];model=settings.resolve(settings.expert_checkpoint)
    package=load_package(model,item['package'],verify=True)
    if package.get('executor')=='llama_cpp':raise ValueError('GGUF는 원본의 검증된 저비트 파일을 사용합니다. PyTorch 정밀도 변환 대상이 아닙니다.')
    if package.get('quantization'):raise ValueError('재양자화 대신 원본 패키지에서 변환하세요.')
    root=model.parent/'expert-packages';total=sum(v.numel()*v.element_size() for v in package['state_dict'].values())
    if shutil.disk_usage(root).free<total+settings.resources.disk_reserve_gib*2**30:raise ValueError('변환 후보를 저장할 디스크 여유 공간이 부족합니다.')
    if psutil.virtual_memory().available<total+settings.resources.ram_reserve_gib*2**30:raise MemoryError('현재 RAM이 부족합니다. 다른 Expert 실행이 끝난 뒤 변환하세요.')
    weights=package['state_dict'];quantization={};pool=None
    choice=choose_device(settings,payload.get('device','auto'),conversion=True)
    device=choice['device']
    used_cuda=device.startswith('cuda')
    if device.startswith('cuda'):torch.cuda.reset_peak_memory_stats()
    try:
        targets={}
        if precision in ('int8','int4','nf4'):
            progress(stage='conversion_structure',detail='원본 구조에서 지원하는 Linear 계층 확인 중')
            pool=ExpertPool(settings,extra_packages={key:item['package']});expert=pool.get(key,structure_only=True)
            targets=linear_layers(expert)
            if not targets:raise ValueError('양자화 가능한 untied Linear 계층이 없습니다. FP16/BF16 변환을 사용하세요.')
        converted={};cache={};count=len(weights)
        for index,(name,value) in enumerate(weights.items()):
            layer=name.removesuffix('.weight') if name.endswith('.weight') else None
            if layer in targets:
                if precision=='nf4':
                    from .nf4_linear import pack_nf4
                    values=pack_nf4(value,device)
                    converted.update({layer+'.'+k:v for k,v in values.items()})
                    quantization[layer]=dict(bits=4,engine='bitsandbytes',shape=list(value.shape));continue
                bits=PRECISIONS[precision]
                try:q,scales=pack_weight(value,bits,device=device)
                except torch.cuda.OutOfMemoryError:
                    if payload.get('device','auto')!='auto':raise
                    torch.cuda.empty_cache();device='cpu';choice.update(device='cpu',reason='CUDA 작업 여유가 줄어 나머지 변환을 CPU에서 수행')
                    q,scales=pack_weight(value,bits)
                converted[layer+'.qweight']=q;converted[layer+'.scales']=scales
                quantization[layer]=dict(bits=bits,group_size=64,shape=list(value.shape))
            elif value.is_floating_point() and precision in ('fp16','bf16'):
                identity=(value.untyped_storage().data_ptr(),value.storage_offset(),tuple(value.shape),tuple(value.stride()))
                if identity not in cache:
                    try:cache[identity]=cast_tensor(value,PRECISIONS[precision],device)
                    except torch.cuda.OutOfMemoryError:
                        if payload.get('device','auto')!='auto':raise
                        torch.cuda.empty_cache();device='cpu';choice.update(device='cpu',reason='CUDA 작업 여유가 줄어 나머지 변환을 CPU에서 수행')
                        cache[identity]=cast_tensor(value,PRECISIONS[precision],device)
                converted[name]=cache[identity]
            else:converted[name]=value
            if index%10==0 or index+1==count:progress(stage='converting',completed=index+1,total=count,detail=f'{device} · {precision.upper()} 변환 · {index+1}/{count} tensor')
        stored=sum(v.numel()*v.element_size() for v in converted.values())
        candidate={**package,'id':slot,'state_dict':converted,'representation':precision.upper()+(' · Linear 가중치' if quantization else ''),
            'entry':{**package['entry'],'id':slot,'name':item['name']+' · '+precision.upper(),'weight_bytes':stored,'dtype':precision.upper()},
            'conversion':dict(source_id=key,source_sha256=item['package']['sha256'],precision=precision,
                original_tensor_bytes=total,converted_tensor_bytes=stored,layers=len(quantization),
                device_choice=choice,peak_vram_bytes=torch.cuda.max_memory_allocated() if used_cuda else 0,
                execution='bitsandbytes NF4 native kernel' if precision=='nf4' else 'packed weights / bounded floating-point Linear' if quantization else 'native autocast')}
        if quantization:candidate['quantization']=quantization
        progress(stage='conversion_save',detail='변환 후보 저장 · 원본 유지')
        temporary=atomic_torch_save(candidate,root/(slot+'.pt'));checksum=digest(temporary)
        target=root/(slot+'-'+checksum[:16]+'.pt')
        if target.exists():
            if digest(target)!=checksum:raise ValueError('같은 이름의 후보 패키지가 손상됐습니다.')
            temporary.unlink()
        else:temporary.replace(target)
        reference=dict(file=target.relative_to(root.parent).as_posix(),sha256=checksum,bytes=target.stat().st_size)
        return descriptor(slot,candidate,reference)
    finally:
        if pool:pool.close()
