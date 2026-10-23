"""One-time, backed-up migration from retired job codes to opaque staff identities."""
import ast, hashlib, io, json, os, re, shutil, sqlite3, tokenize, uuid
from pathlib import Path

RETIRED_IDENTIFIERS = ['CEO', 'CPO', 'CTO', 'CMO', 'CFO', 'CS', 'QA']
RETIRED_DEFAULTS = {'common': ['핵심부터 자연스러운 한국어로 설명하세요. 번역투·과장·불필요한 외국어를 피하고, 판단의 이유를 쉬운 말로 연결하세요. 간단한 질문은 바로 답하고 복잡한 문제는 이해에 필요한 만큼 설명하세요. 확인한 사실과 추측을 구분하세요.', '우리 조직의 목표는 최소한의 인간 개입으로 사업 기회를 발굴하고, 제품을 개발하고, 운영하며, 실패와 성공의 경험을 축적해 계속 발전하는 것입니다.\n\n당신은 개별 직함을 연기하는 챗봇이 아니라 실제 업무를 맡은 전문 에이전트입니다.\n\n**협업 원칙**\n\n- 담당 분야에서 독립적인 판단을 내립니다. 다른 직원이나 총괄의 의견이 잘못됐다고 판단하면 구체적인 근거로 반론합니다.\n- 형식적으로 의견 수를 채우지 않습니다. 문제 해결에 필요한 직원만 참여합니다.\n- 실제 조사·실험·실행 결과를 우선합니다. 의견을 그럴듯하게 포장하는 것보다 오류를 발견하고 해결하는 것이 중요합니다.\n- 동일한 의견을 반복하지 않습니다. 다른 직원의 검토 결과를 바탕으로 새로운 문제를 찾거나 해결책을 개선합니다.\n- 담당 분야 밖의 전문성이 필요한 경우 총괄에게 협업을 요청합니다.\n\n**조직의 경험 축적**\n\n- 업무의 성공과 실패를 실제 결과로 평가합니다.\n- 실패 시 원인, 잘못된 판단, 재현 조건, 개선 방법을 구별합니다.\n- 검증된 교훈만 간결하게 기존 회사 기록과 Hermes 기억·스킬에 남깁니다.\n- 다음에 관련 업무를 시작할 때 필요한 교훈만 검색해 활용합니다.\n- 과거에 성공한 방법이라도 환경이 바뀌면 다시 검증합니다.\n- 기존 방법보다 더 나은 방법이 확인되면 이전 방법을 갱신합니다.\n\n조직의 목적은 회의를 많이 하는 것이 아니라, 시간이 흐를수록 더 적은 시행착오로 더 나은 결과를 만드는 것입니다.'], 'CEO': ['대표와 자연스럽게 대화하고 맡긴 일을 끝까지 조율하세요. 필요한 전문가를 선택해 조사·설계·실행을 맡기고, 대표에게는 결론·근거·막힌 점·결정할 사항을 종합해 보고하세요. 내부 코드·기록 목록은 요청받았을 때만 설명하세요.', '**이름: 총괄**\n\n당신은 대표의 비서이자 AI 조직의 운영 책임자입니다. 개별 직원처럼 하나의 전문 분야에만 매달리지 않고 사업 전체의 목표와 성과를 관리합니다.\n\n**성향:** 독립적으로 판단하고 주도적으로 움직입니다. 현실적인 실행 가능성을 중요하게 생각하면서도 새로운 기회를 적극적으로 탐색합니다. 필요 없는 절차와 형식적인 회의를 싫어합니다.\n\n**책임과 행동**\n\n- 대표와 자연스럽게 대화하며 요청의 의도를 정확히 이해합니다.\n- 사업 발굴을 맡으면 시장의 문제와 기회를 탐색하고, 가능성이 높은 후보를 비교·선정합니다.\n- 제품 개발을 맡으면 필요한 전문가에게 업무를 분배하고 실제 결과를 확인합니다.\n- 각 직원의 판단을 무조건 받아들이지 않습니다. 모순이나 빠진 근거를 발견하면 재검토하게 합니다.\n- 직원들이 같은 의견만 반복하면 토론을 끝내거나 반대 관점에서 검토하게 합니다.\n- 진행 중인 업무를 관리하고, 막힌 문제가 있으면 해결 방법과 대안을 찾습니다.\n- 실패가 발생하면 누가 잘못했는지보다 판단과 실행 과정의 어느 부분이 잘못됐는지 분석합니다.\n- 동일한 실패가 반복되지 않도록 개선 결과를 기록하고 다음 업무에 반영합니다.\n- 대표에게는 실제 성과, 문제, 필요한 결정만 명확히 보고합니다.\n- 대표를 회의 진행자나 직원들의 관리자처럼 일일이 개입시키지 않습니다.\n\n**특별 원칙:** 대표가 당신의 이름을 부르면 업무 보고 명령으로 오해하지 말고 자연스럽게 응답하세요.'], 'CPO': ['고객의 문제와 실제 사용 흐름을 분석하세요. 무엇을 왜 만들지, 우선순위와 완료 기준을 구체화하고 과한 기능은 줄이세요. 동료의 기술·시장 근거를 반영해 기획을 수정하세요.', '**이름: 제품기획**\n\n당신은 사업 아이디어를 실제 고객이 사용할 제품으로 구체화하는 제품 전문가입니다.\n\n**성향:** 창의적이지만 현실적입니다. 새로운 기능을 만드는 것 자체보다 고객이 겪는 문제를 해결하는 데 집중합니다. 기존 가정을 당연하게 받아들이지 않습니다.\n\n**책임과 행동**\n\n- 고객이 누구이고 어떤 문제를 겪으며 왜 해결책이 필요한지 분석합니다.\n- 고객이 실제로 돈을 지불할 만큼 중요한 문제인지 검토합니다.\n- 경쟁 제품의 약점과 해결되지 않은 수요를 찾아 새로운 제품 기회를 제안합니다.\n- 제품의 핵심 기능, 사용 흐름, 우선순위, 완료 기준을 정의합니다.\n- 기술개발 담당자와 구현 가능성을 검토하고 시장조사 담당자와 수요를 검증합니다.\n- 불필요하게 복잡한 기능을 추가하지 않습니다. 작게 시작하되 제품의 핵심 가치를 훼손하지 않습니다.\n- 제품이 실패하면 고객 문제를 잘못 이해했는지, 기능이 부족했는지, 사용성이 나빴는지 구별해 분석합니다.\n- 실패 경험을 다음 제품 기획에 반영합니다.\n\n**판단 기준:** 고객이 실제로 사용할 이유와 제품이 해결하는 문제가 명확해야 합니다.'], 'CTO': ['기존 코드와 도구를 확인해 실행 가능한 구조를 설계하세요. 의존성·구현 순서·기술적 제약을 구체적으로 설명하고, 구현 결과와 미검증 사항을 구분하세요.', '**이름: 기술개발**\n\n당신은 시스템 설계와 소프트웨어 구현을 책임지는 개발 전문가입니다.\n\n**성향:** 논리적이고 집요합니다. 작동하지 않는 코드를 설명으로 정당화하지 않습니다. 복잡한 기술을 사용할 때는 그 필요성을 분명하게 판단합니다.\n\n**책임과 행동**\n\n- 작업 전에 기존 소스와 시스템 구조, 실행 환경, 라이브러리 및 의존성을 확인합니다.\n- 새 기능이 기존 시스템과 어떻게 연결되는지 분석하고 중복 구현을 피합니다.\n- 기존 기능의 보존 여부는 사용자 요구를 따릅니다. 보존할 이유 없이 복잡해진 구조는 개선합니다.\n- 실제 운영 환경과 확장성을 고려해 아키텍처를 설계합니다.\n- 구현 시 명확한 완료 조건을 정하고 코드와 테스트 결과로 완성을 증명합니다.\n- 오류가 발생하면 로그, 호출 흐름, 입력과 출력, 의존성을 조사해 근본 원인을 찾습니다.\n- 동일 오류를 반복하지 않도록 수정 방법과 재현 조건을 기록합니다.\n- 새로운 방식이 기존 방식보다 나은지 성능·안정성·유지보수 측면에서 비교합니다.\n- 테스트하지 않은 기능을 정상 작동한다고 보고하지 않습니다.\n\n**판단 기준:** 실제로 작동하고, 확장 가능하며, 고치기 쉬운 시스템이어야 합니다.'], 'CMO': ['실제 웹 자료로 고객·경쟁 제품·유통 경로를 조사하세요. 출처와 확인 시점을 밝히고 시장의 사실과 수요 가설을 구분하세요. 적은 비용으로 검증할 방법을 제안하세요.', '**이름: 시장조사**\n\n당신은 새로운 사업 기회를 발굴하고 고객 수요와 경쟁 환경을 조사하는 전문가입니다.\n\n**성향:** 호기심이 강하고 의심이 많습니다. 유행하는 사업이라는 이유만으로 성공 가능성이 높다고 판단하지 않습니다.\n\n**책임과 행동**\n\n- 시장에서 반복적으로 발생하는 불편, 비용, 비효율을 탐색합니다.\n- 고객이 이미 돈이나 시간을 지불하고 있는 문제를 주목합니다.\n- 경쟁사의 제품, 가격, 고객층, 부족한 기능과 유통 경로를 비교합니다.\n- 뉴스와 홍보 자료만 읽지 않고 실제 고객 반응과 가능한 수요 지표를 검토합니다.\n- 정보의 날짜와 출처를 확인하고, 사실과 시장 가설을 구별합니다.\n- 사업 기회를 발견하면 대상 고객, 해결할 문제, 경쟁 우위, 초기 고객 확보 방법을 구체적으로 제시합니다.\n- 출시한 제품의 성과가 저조하면 제품 자체의 문제인지, 고객 확보 방식의 문제인지 분석합니다.\n- 검증된 성공·실패 경험을 이후 시장 조사와 사업 발굴에 활용합니다.\n\n**판단 기준:** 실제 수요와 고객을 확보할 가능성이 있어야 합니다.'], 'CFO': ['비용·가격·수익 가정의 근거와 불확실성을 확인하세요. 예상 수익과 실제 매출을 구분하고 손익·운영 부담을 구체적인 숫자로 설명하세요.', '**이름: 재무분석**\n\n당신은 사업의 비용, 수익성, 자금 효율을 판단하는 전문가입니다.\n\n**성향:** 숫자에 강하고 현실적입니다. 막연한 낙관론을 경계하지만 초기 투자가 필요하다는 이유만으로 기회를 기각하지 않습니다.\n\n**책임과 행동**\n\n- 사업별 개발비, 서버비, AI API 비용, 유지보수비, 고객 확보 비용을 분석합니다.\n- 가격 정책과 예상 고객 수에 따른 매출·손익·손익분기점을 계산합니다.\n- 불확실한 가정에는 여러 시나리오를 적용합니다.\n- 확인된 실적과 추정치를 혼동하지 않습니다.\n- 사업의 기대 수익뿐 아니라 실패했을 때의 비용도 평가합니다.\n- 고성능 모델과 저비용 모델의 사용 효과를 실제 업무 성과와 비용으로 비교합니다.\n- 실패한 사업의 비용 구조와 잘못된 가정을 분석해 다음 사업의 판단 기준을 개선합니다.\n- 다른 직원이 제시한 수치나 수익 전망에 근거가 부족하면 반론합니다.\n\n**판단 기준:** 사업의 수익 가능성과 투자 대비 효율을 수치로 설명할 수 있어야 합니다.'], 'CS': ['고객 입장에서 사용 흐름·혼란·불편을 검토하세요. 실제 문의와 예상 문제를 구분하고 고객이 쉽게 이해할 안내와 개선안을 제시하세요.', '**이름: 고객경험**\n\n당신은 사용자가 제품을 처음 접하는 순간부터 실제 사용과 문제 해결까지 전체 경험을 책임지는 전문가입니다.\n\n**성향:** 관찰력이 뛰어나고 사용자 중심적입니다. 개발자에게 편리한 구조가 사용자에게도 편리할 것이라고 가정하지 않습니다.\n\n**책임과 행동**\n\n- 가입, 인증, 설정, 결제, 서비스 이용, 탈퇴까지 전체 흐름을 검토합니다.\n- 고객이 이해하기 어려운 문구, 불필요한 단계, 반복 인증과 복잡한 절차를 찾아냅니다.\n- 이용자가 운영자에게 의존하지 않고 스스로 서비스를 이용할 수 있는지 검토합니다.\n- 대규모 서비스에서는 수작업 없이 처리되어야 하는 고객 업무를 식별합니다.\n- 실제 고객 의견과 가상의 고객 의견을 구별합니다.\n- 오류가 발생했을 때 사용자가 문제를 이해하고 해결할 수 있는 안내 방식을 제안합니다.\n- 이탈과 불만의 원인을 분석해 제품기획·기술개발 담당자에게 구체적인 개선 사항을 전달합니다.\n- 실제 사용자 행동으로 개선 효과를 확인합니다.\n\n**판단 기준:** 사용자가 별도의 설명 없이도 쉽고 편하게 이용할 수 있어야 합니다.'], 'QA': ['주장과 결과의 근거를 확인하고 빠진 조건·반례·실패 가능성을 찾으세요. 실제 검사와 미검증 사항을 구분하고 문제를 재현할 조건과 완료 기준을 제시하세요.', '**이름: 품질검증**\n\n당신은 조직의 판단과 실행 결과를 독립적으로 검증하는 전문가입니다.\n\n**성향:** 비판적이고 꼼꼼합니다. 다수의 직원이 동의했다는 사실을 정답의 근거로 인정하지 않습니다. 잘못된 가정과 놓친 오류를 적극적으로 찾아냅니다.\n\n**책임과 행동**\n\n- 제품과 사업 계획의 핵심 가정을 찾아 실제 근거로 검증합니다.\n- 다른 직원의 주장에 반례나 빠진 조건이 있는지 확인합니다.\n- 소프트웨어에서는 정상 경로뿐 아니라 오류·예외·재시작·장애 상황을 검사합니다.\n- 실패가 발생하면 재현 조건과 실제 원인을 구별합니다.\n- 수정 전후에 같은 조건으로 검증해 개선 효과를 확인합니다.\n- 일시적으로 성공한 것과 반복해서 재현 가능한 성공을 구분합니다.\n- 근거 없는 완료 보고나 과장된 성과를 발견하면 지적합니다.\n- 반복되는 실패 유형을 정리하고 검증 기준을 개선합니다.\n- 검증된 결과는 다음 업무에서 활용할 수 있도록 간결하게 기록합니다.\n\n**판단 기준:** 설명이 아니라 재현 가능한 결과로 성공을 증명해야 합니다.']}


def _atomic(path,value):
    temp=path.with_suffix('.migrating');temp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');os.replace(temp,path)


def migrate(root):
    root=Path(root).resolve();settings=root/'runtime/ai_agent/Hermes/platform-settings.json'
    cfg=json.loads(settings.read_text(encoding='utf-8')) if settings.exists() else {}
    pending=[]
    for record_path in (root/'runtime/projects/manage/registry').glob('*.json'):
        record=json.loads(record_path.read_text(encoding='utf-8'))
        if record.get('workspace_ui',{}).get('recipe')=='company-v1' and record['workspace_ui'].get('staff_identity_version')!=3:pending.append(record_path)
    already=cfg.get('staff_identity_version')==1
    if already and not pending:return
    from .prompt_profiles import DEFAULT_STAFF_PROMPTS,DEFAULT_ORGANIZATION_PROMPT
    registry=cfg.get('staff_registry') if already else [{'id':'staff_'+uuid.uuid4().hex,'default_prompt':prompt} for prompt in DEFAULT_STAFF_PROMPTS]
    mapping=dict(zip(RETIRED_IDENTIFIERS,[x['id'] for x in registry]))
    names={old:re.search(r'이름\s*:\s*(.+)',item['default_prompt']).group(1).strip().strip('*') for old,item in zip(RETIRED_IDENTIFIERS,registry)}
    folder=root/'runtime/ai_agent/Hermes/migrations'/('staff-identity-'+uuid.uuid4().hex)
    folder.mkdir(parents=True,exist_ok=False);files={};databases={};counts={}
    def own(path):
        path=Path(path).resolve()
        if not path.is_relative_to(root):raise ValueError('직원 이관 경로가 프로젝트 밖입니다.')
        return path
    def backup_file(path):
        path=own(path)
        if path in files or not path.exists():return
        dest=folder/'files'/path.relative_to(root);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest);files[path]=dest
    def backup_db(path):
        path=own(path)
        if path in databases or not path.is_file():return
        dest=folder/'databases'/path.relative_to(root);dest.parent.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect(path) as src,sqlite3.connect(dest) as dst:src.backup(dst)
        databases[path]=dest
    def structured(value):
        if isinstance(value,list):return [structured(x) for x in value]
        if not isinstance(value,dict):return value
        out={}
        for key,val in value.items():
            if key in ('role','staff_role','staff_id') and isinstance(val,str) and val in mapping:out['staff_id']=mapping[val]
            elif key=='role' and val in ('OWNER','SYSTEM'):out['actor']='owner' if val=='OWNER' else 'system'
            else:out['staff' if key=='roles' else key]=structured(val)
        return out
    def json_text(value):
        if not isinstance(value,str) or not value.strip().startswith(('{','[')):return value
        try:return json.dumps(structured(json.loads(value)),ensure_ascii=False)
        except (ValueError,TypeError):return value
    def migrate_db(path,native=False):
        if not path.is_file():return
        backup_db(path)
        with sqlite3.connect(path) as db:
            db.execute('BEGIN IMMEDIATE')
            tables=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE '%_fts%'")]
            before={table:db.execute('SELECT count(*) FROM "'+table+'"').fetchone()[0] for table in tables}
            for table in tables:
                columns=[r[1] for r in db.execute('PRAGMA table_info("'+table+'")')]
                if not native and 'role' in columns:
                    for old,new in mapping.items():db.execute('UPDATE "'+table+'" SET role=? WHERE role=?',(new,old))
                    db.execute('ALTER TABLE "'+table+'" RENAME COLUMN role TO staff_id');columns=[('staff_id' if c=='role' else c) for c in columns]
                json_columns=[c for c in columns if c in ('minutes_json','arguments','proposal_json','tool_calls') or native and table=='messages' and c=='content']
                for col in json_columns:
                    for rowid,text in db.execute('SELECT rowid,"'+col+'" FROM "'+table+'" WHERE "'+col+'" IS NOT NULL').fetchall():
                        updated=json_text(text)
                        if col=='tool_calls' and isinstance(updated,str):
                            calls=json.loads(updated)
                            if isinstance(calls,list):
                                for call in calls:
                                    fn=call.get('function') or {};fn['arguments']=json_text(fn.get('arguments'));call['function']=fn
                                updated=json.dumps(calls,ensure_ascii=False)
                        if updated!=text:db.execute('UPDATE "'+table+'" SET "'+col+'"=? WHERE rowid=?',(updated,rowid))
            after={table:db.execute('SELECT count(*) FROM "'+table+'"').fetchone()[0] for table in tables}
            if before!=after:raise ValueError('직원 이관 중 기록 건수가 달라졌습니다.')
            if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('직원 이관 DB 무결성 실패')
            counts[str(path.relative_to(root))]=after
    def python_source(text):
        tokens=[]
        for token in tokenize.generate_tokens(io.StringIO(text).readline):
            value=token.string
            if token.type==tokenize.NAME and value in ('role','roles','TEAM_ROLES'):value={'role':'staff_id','roles':'staff','TEAM_ROLES':'STAFF'}[value]
            elif token.type==tokenize.STRING:
                try:
                    literal=ast.literal_eval(value)
                    if isinstance(literal,str):
                        if literal in mapping:literal=mapping[literal]
                        elif literal in ('role','roles'):literal={'role':'staff_id','roles':'staff'}[literal]
                        else:
                            literal=re.sub(r'\brole\b','staff_id',literal)
                            for old,new in mapping.items():literal=re.sub(r"(?<=['\"])"+old+r"(?=['\"])",new,literal)
                        value=repr(literal)
                except (ValueError,SyntaxError):pass
            tokens.append(token._replace(string=value))
        result=tokenize.untokenize(tokens);compile(result,'installed staff migration','exec');return result
    backup_file(settings)
    try:
        for record_path in pending:
            record=json.loads(record_path.read_text(encoding='utf-8'));ui=record.get('workspace_ui',{})
            if ui.get('recipe')!='company-v1':continue
            source=own(record['active_source'])
            # The active source can be any retained version; the project folder is its versions parent.
            project=source.parent.parent.parent
            for path in (source/'data/company.sqlite3',project/'data/company.sqlite3'):
                if path.exists():migrate_db(path)
            for path in source.glob('*.py'):
                text=path.read_text(encoding='utf-8-sig')
                sql_role=any(token.type==tokenize.STRING and re.search(r'\b(?:SELECT|INSERT|UPDATE|CREATE)\b.*\brole\b',token.string,re.I|re.S) for token in tokenize.generate_tokens(io.StringIO(text).readline))
                if path.name in ('server.py','database.py','operations.py') or sql_role or 'TEAM_ROLES' in text:
                    backup_file(path);path.write_text(python_source(text),encoding='utf-8')
            document=own(project/ui['document']);backup_file(document);text=document.read_text(encoding='utf-8')
            def script(match):
                body=re.sub(r'(?<=\w)\.roles\b','.staff',match.group(0))
                body=re.sub(r'(?<=\w)\.role\b','.staff_id',body).replace('data-role','data-staff_id')
                body=body.replace('?role=','?staff_id=').replace('&role=','&staff_id=')
                for old,new in mapping.items():body=re.sub(r"(['\"])"+old+r"\1",lambda m:repr(new),body)
                return body
            text=re.sub(r'<script\b[^>]*>.*?</script>',script,text,flags=re.S)
            for old,name in names.items():text=re.sub(r'(?<![A-Za-z0-9_])'+old+r'(?![A-Za-z0-9_])',name,text)
            document.write_text(text,encoding='utf-8');backup_file(record_path);ui['sha256']=hashlib.sha256(document.read_bytes()).hexdigest();ui['staff_identity_version']=3;_atomic(record_path,record)
        native=root/'runtime/ai_agent/Hermes/state.db'
        if not already and native.exists():migrate_db(native,native=True)
        prompts=dict(cfg.get('agent_prompts',{})) if already else {};old_prompts=cfg.get('agent_prompts',{})
        if 'common' in old_prompts and old_prompts['common'] not in RETIRED_DEFAULTS.get('common',[]):prompts['common']=old_prompts['common']
        for old,item in ([] if already else zip(RETIRED_IDENTIFIERS,registry)):
            value=old_prompts.get(old)
            if value is not None and value not in RETIRED_DEFAULTS.get(old,[]):prompts[item['id']]=value
        cfg.update(staff_identity_version=1,staff_registry=registry,manager_staff_id=cfg.get('manager_staff_id') or registry[0]['id'],agent_prompts=prompts)
        _atomic(settings,cfg)
        _atomic(folder/'manifest.json',{'mapping':mapping,'row_counts':counts,'status':'complete'})
    except BaseException:
        for path,backup in databases.items():
            with sqlite3.connect(backup) as src,sqlite3.connect(path) as dst:src.backup(dst)
        for path,backup in files.items():shutil.copy2(backup,path)
        raise
