"""Evidence for discovery results; dates and input requirements are not guessed."""
from datetime import datetime
import re
import requests


def iso(value):return value.isoformat() if hasattr(value,'isoformat') else value or None


def annotate(row,info,known,stored,available_ram):
    card=getattr(info,'card_data',None) or {}
    if hasattr(card,'to_dict'):card=card.to_dict()
    row.update(created=iso(getattr(info,'created_at',None)),updated=iso(getattr(info,'last_modified',None)) or row.get('updated'),
        pipeline=getattr(info,'pipeline_tag',None),installed_versions=stored.get(row['repository'],[]))
    release=str(card.get('release_date') or '')
    try:row['release_date']=datetime.fromisoformat(release.replace('Z','+00:00')).date().isoformat()
    except ValueError:row['release_date']=None
    row['release_source']=row['url']+'/blob/'+row['revision']+'/README.md' if row['release_date'] else None
    template=known.get(row.get('template'),{}).get('item')
    if row.get('same_weights') and template and not row['installed_versions']:
        row['installed_versions']=[dict(id=template['id'],name=template['name'],revision=None,active=known[row['template']].get('active',False))]
    if template:row['input']=template['input']
    elif row.get('executor')=='hf_forecast':
        from .expert_contracts import input_contract
        row['input']=input_contract(dict(backend=row['backend']))
    if row.get('input'):
        contract=row['input'];row['input_summary']=' · '.join(contract.get('requires',[]))
        row['api_requirement']='추가 추론 API 없음 · 현재 시세/일봉 파이프라인 사용'
        row['requirements_verified']=True
        row['overlap']=[v['item']['name'] for v in known.values() if v['item']['input'].get('pipeline')==contract.get('pipeline')]
        row['overlap_basis']='같은 입력 역할 · 성능/출력 동일 여부는 실제 비교 필요'
    else:
        row.update(input_summary='원본 모델 입력 계약 확인 필요',api_requirement='미확인 · 외부 API 없이 실행 가능한지는 아직 검증되지 않음',requirements_verified=False,overlap=[])
    row['domain']='금융 특화 검색 결과' if re.search(r'fintext|finrl|finance|financial|finbert|stock',row['repository'],re.I) else '시장 시계열 활용 후보 · 금융 특화 학습 여부 미확인'
    row['financial_relevance']=bool(re.search(r'fintext|finrl|finance|financial|finbert|stock|marketgpt',row['repository'],re.I)) or row.get('compatible',False)
    size=row.get('bytes')
    row['resource_note']='가중치 크기만으로 peak RAM/VRAM을 판단할 수 없음 · 실제 검사 필요'
    if size and size>available_ram:row['resource_note']='현재 여유 RAM보다 파일이 큼 · 경량 버전/변환 검토 필요'
    # Read bounded public documentation as data. Never load remote Python/model code.
    try:
        url=row['url']+'/resolve/'+row['revision']+'/README.md'
        with requests.get(url,stream=True,timeout=(5,10)) as response:
            response.raise_for_status();body=bytearray()
            for chunk in response.iter_content(8192):
                body.extend(chunk)
                if len(body)>=65536:break
        lines=body[:65536].decode('utf-8',errors='replace').splitlines()
        if not row['financial_relevance']:
            row['financial_relevance']=bool(re.search(r'time.series|financial|OHLCV',body.decode('utf-8',errors='replace'),re.I))
        pattern=r'\b(?:ITCH|OHLCV|order.book|news|sentiment|api.key|API endpoint|data provider|input data)\b'
        evidence=[re.sub(r'\s+',' ',line).strip()[:240] for line in lines if re.search(pattern,line,re.I)]
        row['input_evidence']=dict(source=row['url']+'/blob/'+row['revision']+'/README.md',snippets=evidence[:3])
        if not row['requirements_verified']:
            documented=' '.join(evidence)
            hints=[label for expression,label in ((r'\bITCH\b','Nasdaq ITCH 메시지'),(r'order.book','주문장'),
                (r'\bOHLCV\b','OHLCV'),(r'\bnews\b','뉴스 텍스트'),(r'\bsentiment\b','감성 분석')) if re.search(expression,documented,re.I)]
            if hints:row['input_summary']='문서 단서: '+' · '.join(hints)+' · 정확한 입력 규격 미검증'
    except requests.RequestException:row['input_evidence']=dict(source=row['url'],snippets=[],unavailable=True)
    return row
