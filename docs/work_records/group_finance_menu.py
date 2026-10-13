from pathlib import Path
import ast,json,os,re,subprocess
R=Path(r'C:\Users\hushm\Desktop\금융매매모델');os.chdir(R)
groups=('trading','finrl','extensions','management')
tracked=subprocess.check_output([r'C:\Program Files\Git\cmd\git.exe','ls-files','-z']).decode().split('\0')
dirs={f'frontend/src/pages/{g}':f'frontend/src/pages/finance/{g}' for g in groups}
retired=[f'backend/stockrl/{g}/{g}_menu_manager.py' for g in groups]+[f'frontend/src/pages/{g}/{g}_menu_manager.ts' for g in groups]
def move(name):
 for a,b in dirs.items():
  if name==a or name.startswith(a+'/'):return b+name[len(a):]
 return name
updates={}
known={p for p in tracked if p}
for name in tracked:
 if not name or name in retired:continue
 if any(name.startswith(folder+'/') for folder in dirs):
  p=R/name
  if not p.is_file():continue
  s=p.read_text(encoding='utf-8-sig');new=move(name)
  if p.suffix in ('.ts','.tsx'):
   def spec(m):
    quote,target=m.group(1),m.group(2)
    if not target.startswith('.'):return m.group(0)
    base=Path(os.path.normpath(str(Path(name).parent/target))).as_posix()
    resolved=next((candidate for candidate in (base,base+'.ts',base+'.tsx',base+'.css',base+'/index.ts',base+'/index.tsx') if candidate in known or (R/candidate).is_file()),None)
    if not resolved:return m.group(0)
    target=os.path.relpath(move(resolved),Path(new).parent).replace('\\','/')
    if Path(resolved).suffix in ('.ts','.tsx'):target=target.rsplit('.',1)[0]
    if not target.startswith('.'):target='./'+target
    return quote+target+quote
   s=re.sub(r"(['\"])([^'\"\n]+)\1",spec,s)
  updates[new]=s
updates['backend/stockrl/submenu_manager.py']='''"""Collect all finance submenus without changing their implementations."""
from .trading.submenu_manager import MENUS as TRADING,ROUTERS as TRADING_ROUTERS
from .finrl.submenu_manager import MENUS as FINRL,ROUTERS as FINRL_ROUTERS
from .extensions.submenu_manager import MENUS as EXTENSIONS,ROUTERS as EXTENSIONS_ROUTERS
from .management.submenu_manager import MENUS as MANAGEMENT,ROUTERS as MANAGEMENT_ROUTERS

MENUS=(*TRADING,*FINRL,*EXTENSIONS,*MANAGEMENT)
ROUTERS=(*TRADING_ROUTERS,*FINRL_ROUTERS,*EXTENSIONS_ROUTERS,*MANAGEMENT_ROUTERS)
'''
updates['backend/stockrl/finance_menu_manager.py']='''"""Register the finance project as one large menu."""
from .submenu_manager import MENUS,ROUTERS
GROUP={'id':'finance','title':'금융','menus':MENUS}
'''
p=R/'backend/menu_registry.py';s=p.read_text(encoding='utf8')
start=s.index('from stockrl.trading.');end=s.index('_routes_by_menu={}')
s=s[:start]+'''from stockrl.finance_menu_manager import GROUP as FINANCE,ROUTERS as FINANCE_ROUTERS
from rea.rea_menu_manager import GROUP as REA,ROUTERS as REA_ROUTERS

GROUPS=(FINANCE,REA)
'''+s[end:]
s=s.replace("return 'management','backend-browser'","return 'finance','backend-browser'").replace("return 'management','system'","return 'finance','system'")
s=s.replace('through the five large-menu coordinators','through the finance and REA coordinators').replace('(TRADING_ROUTERS,FINRL_ROUTERS,REA_ROUTERS,EXTENSIONS_ROUTERS,MANAGEMENT_ROUTERS)','(FINANCE_ROUTERS,REA_ROUTERS)')
updates['backend/menu_registry.py']=s
updates['frontend/src/pages/finance/submenu_manager.ts']='''import {lazy} from 'react';
import {Workflow} from 'lucide-react';
import {menus as trading} from './trading/submenu_manager';
import {menus as finrl} from './finrl/submenu_manager';
import {menus as extensions} from './extensions/submenu_manager';
import {menus as management} from './management/submenu_manager';
import {actionMenus,type MenuItem} from '../../shell/menu_groups/menu_types';
import type {BackendAction} from '../../data/menu_types';
const feature=lazy(()=>import('./management/backend_browser/FeatureWorkspace').then(m=>({default:m.FeatureWorkspace})));
export const menus:MenuItem[]=[...trading,...finrl,...extensions,...management].map(menu=>({...menu,group:'금융'}));
export function registeredMenus(actions:BackendAction[]){return [...menus,...actionMenus(actions,'finance','금융',feature,Workflow)];}
'''
updates['frontend/src/pages/finance/finance_menu_manager.ts']="export {menus,registeredMenus} from './submenu_manager';\n"
updates['frontend/src/shell/menu_groups/menu_registry.ts']='''import {menus as finance,registeredMenus as financeMenus} from '../../pages/finance/finance_menu_manager';
import {menus as rea} from '../../pages/rea/rea_menu_manager';
export const navigation=[...finance,...rea];
export function registeredNavigation(actions:Parameters<typeof financeMenus>[0]){return [...financeMenus(actions),...rea];}
'''
p=R/'frontend/src/shell/Shell.tsx';s=p.read_text(encoding='utf8')
start=s.index('function errorSection');end=s.index('export function Page',start)
section=s[start:end]
section=re.sub(r"group:'[^']*'", "group:'금융'",section)
section=section.replace("return {group:'금융',target:'rea'}","return {group:'REA 역공학',target:'rea'}")
s=s[:start]+section+s[end:]
s=s.replace("moduleErrors.filter(([name])=>errorSection(name).group===page?.group)","moduleErrors.filter(([name])=>errorSection(name).target===active)")
updates['frontend/src/shell/Shell.tsx']=s
# Update backend metadata to the relocated frontend source paths only.
for category in groups:
 for p in (R/'backend/stockrl'/category).glob('*/menu.py'):
  old=p.read_text(encoding='utf8');new=old.replace('pages/'+category+'/', 'pages/finance/'+category+'/')
  if old!=new:updates[p.relative_to(R).as_posix()]=new
# Local category managers are folder organization under finance, not platform large menus.
for g in groups:
 for base in ('backend/stockrl','frontend/src/pages/finance'):
  ext='py' if base.startswith('backend') else 'ts'
  directory=R/base/g if base.startswith('backend') else R/'frontend/src/pages'/g
  for p in directory.glob('**/README.md'):
   oldname=p.relative_to(R).as_posix();newname=move(oldname);s=updates.get(newname,p.read_text(encoding='utf8'))
   s=s.replace(g+'_menu_manager.'+ext,'finance_menu_manager.'+ext)
   s+='\n所属大菜单：금융. 이 폴더는 금융 내부 기능 분류이며 독립 대메뉴로 등록하지 않습니다. 하위 기능 → 분류 submenu_manager → 금융 submenu_manager → finance_menu_manager → 전체 menu_registry → /api.\n'.replace('所属大菜单','소속 대메뉴')
   updates[newname]=s
updates['frontend/src/pages/README.md']='''# Platform menus

- [금융](finance/README.md): 거래 운영·FinRL·MoE·모듈·연결·진단 화면 전체.
- [REA 역공학](rea/README.md): 프로그램 분석·프로젝트 탐색.

shared/는 재사용 UI입니다. 전체 총괄은 shell/menu_groups/menu_registry.ts이며 금융과 REA 매니저만 import합니다.
'''
updates['frontend/src/pages/finance/README.md']='''# 금융

취합: submenu_manager.ts → finance_menu_manager.ts → 전체 메뉴 매니저.

- [trading/](trading/README.md): 운영 제어·가상계좌.
- [finrl/](finrl/README.md): 정책 학습·FinRL 모듈.
- [extensions/](extensions/README.md): MoE·프로젝트 모듈.
- [management/](management/README.md): 연결·설정·진단·백엔드 기능.

대메뉴 표시는 금융 하나입니다. 기존 기능·해시·API 작업명은 유지합니다. 이번 변경 후 브라우저·타입·기능 검사는 미실행입니다.
'''
updates['backend/stockrl/README.md']='''# Finance project

금융 대메뉴 하나로 등록합니다: submenu_manager.py → finance_menu_manager.py → ../menu_registry.py → ../web_api.py.

- [trading/](trading/README.md): 운영 제어·가상계좌.
- [finrl/](finrl/README.md): 정책 학습·FinRL 도구.
- [extensions/](extensions/README.md): MoE·모듈.
- [management/](management/README.md): 연결·설정·진단·기능 조회.

이 네 폴더는 금융 내부 분류입니다. REA는 독립 ../rea/에 있으며 금융 대메뉴에 포함하지 않습니다.
platform/과 루트 모델 모듈은 공유 금융 실행 계약입니다. 모델·계좌·가격·설정·공식 라이브러리·알고리즘 기본값은 변경하지 않습니다.
'''
p=R/'frontend/tests/local-browser.spec.ts';s=p.read_text(encoding='utf8');s=s.replace("  const links = await page.locator('aside a')", "  expect(await page.locator('aside details > summary').allTextContents()).toEqual(['금융','REA 역공학']);\n  const links = await page.locator('aside a')");updates[p.relative_to(R).as_posix()]=s
p=R/'tests/test_state_integrity.py';s=p.read_text(encoding='utf8');s=s.replace("self.assertNotIn('finrl_trading',{group['id'] for group in GROUPS})","self.assertEqual([group['id'] for group in GROUPS],['finance','rea'])");updates[p.relative_to(R).as_posix()]=s
temp=Path(os.environ['TEMP']);(temp/'finance_menu_moves.json').write_text(json.dumps(dirs),encoding='utf8');(temp/'finance_menu_retired.json').write_text(json.dumps(retired),encoding='utf8');(temp/'finance_menu_updates.json').write_text(json.dumps(updates,ensure_ascii=False),encoding='utf8')
print({'large_menus':['finance','rea'],'frontend_directory_moves':len(dirs),'retired_coordinators':len(retired),'updates':len(updates)})
