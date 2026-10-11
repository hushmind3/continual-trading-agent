"""Recent public model implementations and explicit weight releases on GitHub."""
from datetime import datetime,timedelta,timezone
import requests


def search_github(days,progress,query=None):
    since=(datetime.now(timezone.utc)-timedelta(days=days)).date().isoformat()
    terms=[query] if query else ['financial model','time series forecasting','trading model GGUF']
    rows={};errors=[];session=requests.Session();session.headers.update({'Accept':'application/vnd.github+json','User-Agent':'FinRLX-Expert-Discovery'})
    for index,term in enumerate(terms):
        try:
            response=session.get('https://api.github.com/search/repositories',params={'q':f'{term} pushed:>={since} archived:false','sort':'updated','order':'desc','per_page':3},timeout=15)
            response.raise_for_status()
            for repo in response.json().get('items',[]):
                name=repo['full_name']
                if name in rows:continue
                release=session.get(f'https://api.github.com/repos/{name}/releases/latest',timeout=10)
                data=release.json() if release.ok else {};assets=[a for a in data.get('assets',[]) if a['name'].lower().endswith(('.gguf','.safetensors','.pt','.pth'))]
                gguf=next((a for a in assets if a['name'].lower().endswith('.gguf') and any(q in a['name'].lower() for q in ('q4','q5','iq4'))),None)
                revision=data.get('tag_name') or repo['default_branch']
                files=[dict(name=gguf['name'],bytes=gguf['size'],url=gguf['browser_download_url'],sha256=(gguf.get('digest') or '').removeprefix('sha256:') or None)] if gguf else []
                rows[name]=dict(id='github:'+name+'@'+revision,source='GitHub',repository=name,revision=revision,url=repo['html_url'],
                    created=repo['created_at'],updated=repo['pushed_at'],release_date=data.get('published_at'),release_source=data.get('html_url'),downloads=0,
                    compatible=bool(gguf),executor='llama_cpp' if gguf else None,bytes=gguf['size'] if gguf else sum(a['size'] for a in assets) or None,files=files,
                    domain='최근 공개 금융·시장 모델 구현',input_summary='완료 가격 시계열 → 로컬 구조화 의견' if gguf else '원본 입력·실행기 연결 확인 필요',
                    api_requirement='추가 추론 API 없음 · llama.cpp 로컬 실행' if gguf else '미확인 · 원본 코드/모델 문서 확인 필요',requirements_verified=bool(gguf),
                    detail='GGUF 4/5비트 배포 파일 · 원본 적재/입력/출력 검사 필요' if gguf else '소스 저장소 · 확인된 실행 가능한 GGUF 파일 없음',
                    installed_versions=[],overlap=[],input_evidence={'source':repo['html_url'],'snippets':[repo['description']] if repo.get('description') else []})
        except requests.RequestException as exc:errors.append(dict(query='GitHub '+term,detail=str(exc)[:250]))
        progress(stage='searching',detail=f'GitHub 최근 모델·배포 파일 확인 {index+1}/{len(terms)}')
    return list(rows.values()),errors
