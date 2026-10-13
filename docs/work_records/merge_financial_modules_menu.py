from pathlib import Path

root = Path(r'C:\Users\hushm\Desktop\금융매매모델')
def update(name, transform):
    p = root/name
    original = p.read_text(encoding='utf-8')
    text = transform(original)
    if text != original:
        p.write_text(text, encoding='utf-8', newline='\n')

for p in (root/'frontend/src').rglob('*'):
    if p.suffix not in ('.ts','.tsx','.md'):continue
    update(p.relative_to(root), lambda text:text.replace('finance/finrl_modules_tools','finance/modules_tools').replace('./finrl_modules_tools/FinrlModulesTools','./modules_tools/ModulesTools').replace('FinrlModulesTools','ModulesTools'))

update('frontend/src/pages/finance/finrl/submenu_manager.ts', lambda text:text.replace("name:'FinRL 모듈 · 도구'", "name:'모듈 · 도구'"))
update('frontend/src/pages/finance/extensions/submenu_manager.ts', lambda text:'\n'.join(line for line in text.splitlines() if "hash:'finance/project_modules'" not in line)+'\n')
update('backend/stockrl/finrl/submenu_manager.py', lambda text:text.replace('stockrl.finrl.tools.menu import MENU as FRAMEWORKS','stockrl.finrl.modules_tools.menu import MENU as MODULES_TOOLS').replace('MENUS=(LEARNING,FRAMEWORKS,)','MENUS=(LEARNING,MODULES_TOOLS,)'))
update('backend/stockrl/extensions/submenu_manager.py', lambda text:'\n'.join(line.replace('MENUS=(MOE,PROJECT_MODULES,)','MENUS=(MOE,)') for line in text.splitlines() if 'from stockrl.extensions.project_modules.menu' not in line)+'\n')

p = root/'frontend/src/pages/finance/finrl/modules_tools/ModulesTools.tsx'
p.write_text('''import {FrameworkWorkspace} from '../../../shared/frameworks/FrameworkWorkspace';
export function ModulesTools(){return <FrameworkWorkspace scopes={['FinRL','stockrl']}/>}
''', encoding='utf-8', newline='\n')
p = root/'backend/stockrl/finrl/modules_tools/menu.py'
p.write_text('''"""FinRL 및 금융 프로젝트 모듈의 통합 목록·도구."""
MENU={'id':'finance/modules_tools','title':'모듈 · 도구','operations':[],
      'views':['framework'],'frontend':'pages/finance/finrl/modules_tools/ModulesTools.tsx',
      'manager':'stockrl.finrl.modules_tools.menu'}
''', encoding='utf-8', newline='\n')
p = root/'backend/stockrl/finrl/modules_tools/__init__.py'
p.write_text('"""금융 모듈 · 도구 통합 메뉴."""\n', encoding='utf-8', newline='\n')

for name in ('frontend/src/pages/finance/extensions/README.md','backend/stockrl/extensions/README.md'):
    update(name, lambda text:'\n'.join(line for line in text.splitlines() if 'project_modules/' not in line)+'\n')
for name in ('frontend/src/pages/finance/finrl/README.md','backend/stockrl/finrl/README.md'):
    update(name, lambda text:text.replace('[FinRL 모듈 · 도구](finrl_modules_tools/README.md): tools/','[모듈 · 도구](modules_tools/README.md): modules_tools/').replace('[FinRL 모듈 · 도구](tools/README.md): tools/','[모듈 · 도구](modules_tools/README.md): modules_tools/'))
update('frontend/src/pages/finance/README.md', lambda text:'\n'.join(line.replace('FinRL 모듈 · 도구','모듈 · 도구').replace('finrl/finrl_modules_tools/','finrl/modules_tools/').replace('정책 학습·FinRL 모듈','정책 학습·통합 모듈 도구').replace('MoE·프로젝트 모듈','MoE') for line in text.splitlines() if '#finance/project_modules' not in line)+'\n')
update('backend/stockrl/MENU_MAP.md', lambda text:text.replace('moe/, project_modules/','moe/').replace('tools/','modules_tools/'))
for name in ('backend/README.md','backend/stockrl/README.md'):
    update(name, lambda text:text.replace('화면 9개','화면 8개').replace('MoE·프로젝트 모듈','MoE').replace('FinRL 모듈 · 도구','모듈 · 도구'))

readme = '''# 모듈 · 도구

- 역할: FinRL 원본과 금융 프로젝트(stockrl) 모듈을 한 목록에서 검색·필터링합니다. 상태·사용 참조·import·실행 기록을 구분합니다.
- 주소: #finance/modules_tools. 프론트·백엔드 작은 메뉴 폴더 이름은 modules_tools입니다.
- 프론트 진입점: ModulesTools.tsx → 공통 FrameworkWorkspace/ModuleCatalog.
- 백엔드 등록: menu.py → finrl/submenu_manager.py → 금융 submenu_manager → finance_menu_manager → 전체 menu_registry → 단일 /api.
- 의존성: 기존 framework 뷰, NativeModuleRunner의 FinRL 원본 실행, 프로젝트 API는 all_backend_features?tab=commands로 연결합니다.
- 정리: 별도 프로젝트 모듈 메뉴·화면·등록 폴더는 의존성을 제거한 뒤 휴지통으로 이동했습니다. 실제 금융 기능·공식 원본·API 작업명·데이터는 변경하지 않았습니다.
- 확인 상태: 이번 통합 후 브라우저·타입·함수 실행 검사는 미실행입니다.
'''
for name in ('frontend/src/pages/finance/finrl/modules_tools/README.md','backend/stockrl/finrl/modules_tools/README.md'):
    (root/name).write_text(readme, encoding='utf-8', newline='\n')

update('frontend/src/pages/shared/frameworks/FrameworkWorkspace.tsx', lambda text:text.replace("['all','FinRL','FinRL-X','stockrl','REA','Platform'].map", "(scopes?['all',...scopes]:['all','FinRL','FinRL-X','stockrl','REA','Platform']).map").replace("v==='all'?'모든 프레임워크':v==='FinRL-X'", "v==='all'?'전체 모듈':v==='stockrl'?'프로젝트':v==='FinRL-X'"))
update('frontend/src/pages/shared/frameworks/README.md', lambda text:text.replace('FinRL 도구 및 프로젝트 모듈 목록.', '모듈 · 도구의 FinRL·프로젝트 통합 목록 및 백엔드 기능 전체의 공통 목록.'))
for p in (root/'frontend/tests').glob('*.ts'):
    update(p.relative_to(root), lambda text:text.replace('#finance/finrl_modules_tools','#finance/modules_tools').replace('FinRL 모듈 · 도구','모듈 · 도구'))
print('Merged module catalogs, submenu registrations, links, filters and folder READMEs.')
