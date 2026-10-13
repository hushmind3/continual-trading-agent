from pathlib import Path
import re
import subprocess

root = Path(r'C:\Users\hushm\Desktop\금융매매모델')
git = r'C:\Program Files\Git\cmd\git.exe'
# backend folder, frontend folder, old hash, canonical leaf, old/new component
menus = [
 ('trading/control','trading/operation_control','control','operation_control','OperationsBoard','OperationControl'),
 ('trading/paper_account','trading/virtual_account_orders','paper','virtual_account_orders','PaperWorkspace','VirtualAccountOrders'),
 ('finrl/policy_learning','finrl/policy_learning','learning','policy_learning','TrainingWorkspace','PolicyLearning'),
 ('finrl/tools','finrl/finrl_modules_tools','frameworks','finrl_modules_tools','FinrlToolsWorkspace','FinrlModulesTools'),
 ('extensions/moe','extensions/moe','moe','moe','ModelWorkspace','Moe'),
 ('extensions/project_modules','extensions/project_modules','project-modules','project_modules','ProjectModulesWorkspace','ProjectModules'),
 ('management/connection_settings','management/connection_settings','connection','connection_settings','ConnectionSettings','ConnectionSettings'),
 ('management/diagnostics','management/diagnostics_logs_code_apply','system','diagnostics_logs_code_apply','Diagnostics','DiagnosticsLogsCodeApply'),
 ('management/backend_browser','management/all_backend_features','backend-browser','all_backend_features','FeatureWorkspace','AllBackendFeatures'),
]
base = root / 'frontend/src/pages/finance'
for old, new, _, _, component, renamed in menus:
    if old != new:
        source, target = base / old, base / new
        assert source.is_dir() and not target.exists()
        assert source.resolve().is_relative_to(root) and target.resolve().is_relative_to(root)
        assert not source.is_symlink()
        subprocess.run([git, 'mv', str(source), str(target)], cwd=root, check=True)
    if component != renamed:
        subprocess.run([git, 'mv', str(base/new/(component+'.tsx')), str(base/new/(renamed+'.tsx'))], cwd=root, check=True)

hashes = {old: 'finance/'+leaf for _, _, old, leaf, _, _ in menus}
source_files = list((root/'frontend/src').rglob('*.ts')) + list((root/'frontend/src').rglob('*.tsx')) + list((root/'frontend/src/pages/finance').rglob('README.md')) + list((root/'frontend/tests').glob('*.ts'))
for p in source_files:
    original = text = p.read_text(encoding='utf-8')
    for old, new, oldhash, leaf, component, renamed in menus:
        # Folder paths in imports and README links; API operation strings stay intact.
        text = text.replace('pages/finance/'+old+'/', 'pages/finance/'+new+'/')
        if old != new:
            oldleaf, newleaf = old.split('/')[-1], new.split('/')[-1]
            text = text.replace('/'+oldleaf+'/', '/'+newleaf+'/')
            text = text.replace('('+oldleaf+'/', '('+newleaf+'/')
        if component != renamed:
            text = re.sub(r'\b'+re.escape(component)+r'\b', renamed, text)
        text = re.sub(r'#'+re.escape(oldhash)+r'(?=[?\'"`\s]|$)', '#'+hashes[oldhash], text)
        text = text.replace("hash:'"+oldhash+"'", "hash:'"+hashes[oldhash]+"'")
    if p.name == 'Shell.tsx':
        start = text.index('function destination(')
        end = text.index('function errorSection(', start)
        text = text[:start] + '''function destination(hash:string,items=navigation){
 const name=hash.replace(/^#/,'').split('?')[0];
 return items.find(item=>item.hash===name)||items[0];
}
export function route(hash:string){const name=hash.replace(/^#/,'').split('?')[0];return name.startsWith('finance/')&&name.split('/').length>2?name:destination(hash).hash;}
''' + text[end:]
        for oldhash, canonical in hashes.items():
            text = text.replace("target:'"+oldhash+"'", "target:'"+canonical+"'")
            text = text.replace("active==='"+oldhash+"'", "active==='"+canonical+"'")
            text = text.replace("active!=='"+oldhash+"'", "active!=='"+canonical+"'")
    if p.name == 'menu_types.ts' and p.parent.name == 'menu_groups':
        text = text.replace("hash:'feature-'+action.id", "hash:action.menu_id+'/'+action.id")
    if p.name == 'AllBackendFeatures.tsx':
        text = text.replace("'#feature-'+item.id", "'#'+item.menu_id+'/'+item.id")
    if text != original:
        p.write_text(text, encoding='utf-8', newline='\n')

for old, new, oldhash, leaf, component, renamed in menus:
    p = root/'backend/stockrl'/old/'menu.py'
    text = p.read_text(encoding='utf-8')
    text, count = re.subn(r"('id'\s*:\s*)'"+re.escape(oldhash)+"'", r"\1'finance/"+leaf+"'", text, count=1)
    assert count == 1, p
    text = text.replace('pages/finance/'+old+'/'+component+'.tsx', 'pages/finance/'+new+'/'+renamed+'.tsx')
    p.write_text(text, encoding='utf-8', newline='\n')
    readme = base/new/'README.md'
    text = readme.read_text(encoding='utf-8').rstrip()
    text += '\n\n- 주소: `#finance/'+leaf+'`. 메뉴 등록 ID와 프론트 폴더 이름을 일치시킵니다.\n'
    readme.write_text(text, encoding='utf-8', newline='\n')
    backend_readme = root/'backend/stockrl'/old/'README.md'
    text = backend_readme.read_text(encoding='utf-8')
    text = text.replace('pages/finance/'+old+'/'+component+'.tsx', 'pages/finance/'+new+'/'+renamed+'.tsx')
    text = text.rstrip()+'\n\n프론트 메뉴 주소: `#finance/'+leaf+'`; 화면: `frontend/src/pages/finance/'+new+'/'+renamed+'.tsx`. 백엔드 실행 모듈·API 작업명은 유지합니다.\n'
    backend_readme.write_text(text, encoding='utf-8', newline='\n')

p = root/'frontend/src/pages/finance/README.md'
text = p.read_text(encoding='utf-8').replace('기존 기능·해시·API 작업명은 유지합니다.', '기능·API 작업명은 유지하며 메뉴 주소는 #finance/<영문 작은 메뉴 이름>으로 통일합니다.')
text += '\n| 메뉴 | 주소·폴더 이름 |\n| --- | --- |\n'
titles = ['운영 제어','가상계좌 · 주문','정책 학습','FinRL 모듈 · 도구','MoE','프로젝트 모듈','연결 · 설정','진단 · 로그 · 코드 적용','백엔드 기능 전체']
for title, (_, new, _, leaf, _, _) in zip(titles, menus):
    text += '| '+title+' | #finance/'+leaf+' · '+new+'/ |\n'
p.write_text(text, encoding='utf-8', newline='\n')
p = root/'frontend/src/App.tsx'
text = p.read_text(encoding='utf-8')
needle = '  return <Shell'
assert needle in text
text = text.replace(needle, "  useEffect(()=>{if(hash.replace(/^#/,'').split('?')[0]!==active)location.replace('#'+active)},[hash,active]);\n"+needle)
p.write_text(text, encoding='utf-8', newline='\n')
print('Renamed nine financial menu routes and screen entrypoints, five frontend folders, navigation links and backend menu metadata.')
