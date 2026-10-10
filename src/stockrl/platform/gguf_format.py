"""Read GGUF weight type before deciding whether quantization is necessary."""
import struct
import subprocess
from functools import lru_cache
from pathlib import Path
from .llama_engine import ensure_engine

SIZES={0:1,1:1,2:2,3:2,4:4,5:4,6:4,7:1,10:8,11:8,12:8}
FILE_TYPES={0:'FP32',1:'FP16',2:'Q4_0',3:'Q4_1',7:'Q8_0',8:'Q5_0',9:'Q5_1',10:'Q2_K',
    11:'Q3_K_S',12:'Q3_K_M',13:'Q3_K_L',14:'Q4_K_S',15:'Q4_K_M',16:'Q5_K_S',17:'Q5_K_M',
    18:'Q6_K',19:'IQ2_XXS',20:'IQ2_XS',21:'Q2_K_S',22:'IQ3_XS',23:'IQ3_XXS',24:'IQ1_S',
    25:'IQ4_NL',26:'IQ3_S',27:'IQ3_M',28:'IQ2_S',29:'IQ2_M',30:'IQ4_XS',31:'IQ1_M',32:'BF16'}


def precision_label(kind):
    name=FILE_TYPES.get(kind)
    if name is None:return 'GGUF · 가중치 형식 '+str(kind)
    import re
    bits=re.search(r'(?:I?Q)(\d+)',name)
    return 'GGUF '+name+(' · '+bits.group(1)+'비트 혼합 가중치' if bits else '')


@lru_cache(maxsize=128)
def stored_precision(path,modified,size):
    return precision_label(file_type(Path(path)))


def describe(path):
    with path.open('rb') as stream:
        def read(fmt):return struct.unpack(fmt,stream.read(struct.calcsize(fmt)))[0]
        def string():
            size=read('<Q')
            if size>16*2**20:raise ValueError('GGUF metadata 문자열이 너무 큽니다.')
            return stream.read(size).decode('utf8',errors='replace')
        def skip(kind):
            if kind in SIZES:stream.seek(SIZES[kind],1)
            elif kind==8:string()
            elif kind==9:
                inner=read('<I');count=read('<Q')
                if count>2**20:raise ValueError('GGUF metadata 배열이 너무 큽니다.')
                if inner in SIZES:stream.seek(count*SIZES[inner],1)
                else:
                    for _ in range(count):skip(inner)
            else:raise ValueError('알 수 없는 GGUF metadata 형식')
        if stream.read(4)!=b'GGUF':raise ValueError('GGUF 파일 magic이 다릅니다.')
        if read('<I') not in (2,3):raise ValueError('지원하지 않는 GGUF 버전')
        tensors=read('<Q');count=read('<Q');file_kind=None
        if count>10000:raise ValueError('GGUF metadata 개수가 너무 큽니다.')
        for _ in range(count):
            key=string();kind=read('<I')
            if key=='general.file_type' and kind==4:file_kind=read('<I')
            else:skip(kind)
        if file_kind is None:raise ValueError('GGUF에 가중치 형식 정보가 없습니다.')
        if tensors>100000:raise ValueError('GGUF tensor 개수가 너무 큽니다.')
        parameters=0
        import math
        for _ in range(tensors):
            string();dimensions=read('<I')
            if not 1<=dimensions<=8:raise ValueError('GGUF tensor 차원이 유효하지 않습니다.')
            sizes=[read('<Q') for _ in range(dimensions)];read('<I');read('<Q')
            parameters+=math.prod(sizes)
        return dict(file_type=file_kind,parameters=parameters)


def file_type(path):return describe(path)['file_type']


def quantize_if_needed(settings,path,progress):
    kind=file_type(path)
    if kind not in (0,1,32):return path,kind
    engine=ensure_engine(settings,progress);target=settings.resolve(settings.expert_checkpoint).parent/'expert-packages'/(path.stem+'-q4_k_m.gguf')
    if target.exists():
        existing=file_type(target)
        if existing in (0,1,32):raise ValueError('기존 변환 파일을 덮어쓰지 않습니다. 다른 출력 이름이 필요합니다.')
        return target,existing
    progress(stage='gguf_quantization',detail='GGUF 부동소수점 원본 → Q4_K_M 압축')
    result=subprocess.run([str(engine.with_name('llama-quantize.exe')),str(path),str(target),'Q4_K_M'],capture_output=True,text=True,encoding='utf8',timeout=1800,
        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if result.returncode:
        target.unlink(missing_ok=True);raise ValueError('GGUF 양자화 실패: '+result.stderr[-500:])
    return target,file_type(target)
