const {chromium}=require('@playwright/test');const fs=require('node:fs/promises');const path=require('node:path');const {spawnSync}=require('node:child_process');
const root=path.resolve(__dirname,'../..'),base=path.join(root,'runtime/projects/manage/verification');
async function api(operation,payload={}){const response=await fetch('http://127.0.0.1:8766/api',{method:'POST',signal:AbortSignal.timeout(20000),headers:{'content-type':'application/json'},body:JSON.stringify({operation,payload})});const value=await response.json();if(!response.ok)throw Error(JSON.stringify(value));return value}
async function until(callback,seconds=240){const end=Date.now()+seconds*1000;while(Date.now()<end){try{const value=await callback();if(value)return value}catch(e){if(e.fatal)throw e}await new Promise(resolve=>setTimeout(resolve,750))}throw Error('automatic UI verification timeout')}
(async()=>{
 await fs.mkdir(base,{recursive:true});const temporary=await fs.mkdtemp(path.join(base,'automatic-ui-'));
 const python=`import ast,hashlib,json,sys,zipfile
from pathlib import Path
root=Path.cwd();sys.path.insert(0,str(root/'backend'))
from platform_modules import mount_namespaces
mount_namespaces()
from platform_plugins.projects import adapters
module=ast.parse((root/'development/tests/test_project_automatic_ui.py').read_text(encoding='utf-8-sig'))
script=next(ast.literal_eval(item.value) for item in module.body if isinstance(item,ast.Assign) and any(isinstance(target,ast.Name) and target.id=='SCRIPT' for target in item.targets))
base=Path(sys.argv[1]);source=base/'source';source.mkdir();(source/'main.py').write_text(script,encoding='utf8')
spec=adapters.detect(source)
files={'source/main.py':script.encode('utf8')}
metadata={'schema':1,'title':'Automatic UI verification','url':'https://github.com/verification/automatic-interface','adapter':spec,'files':{name:hashlib.sha256(data).hexdigest() for name,data in files.items()}}
with zipfile.ZipFile(base/'app.zip','w') as archive:
 for name,data in files.items():archive.writestr(name,data)
 archive.writestr('app-package.json',json.dumps(metadata))
print(json.dumps(spec))`;
 let key,record,browser;try{
 const setup=spawnSync(path.join(root,'.venv/Scripts/python.exe'),['-X','utf8','-B','-c',python,temporary],{cwd:root,encoding:'utf8'});if(setup.status)throw Error(setup.stderr);console.log('Source discovered automatically: '+setup.stdout.trim());
 browser=await chromium.launch({headless:true});
  const initial=await api('projects/import',{archive:(await fs.readFile(path.join(temporary,'app.zip'))).toString('base64')});key=initial.id;
  record=await until(async()=>{const value=(await api('projects/installed')).items.find(item=>item.id===key);if(['failed','needs_adapter'].includes(value?.stage))throw Object.assign(Error(value.error),{fatal:true});return value?.stage==='ready'?value:null});
  const generatedFiles=await fs.readdir(path.join(root,'modules',record.module_id,'frontend'));
  if(JSON.stringify(generatedFiles)!==JSON.stringify(['register.ts']))throw Error('Per-project UI code was generated');
  const schema=await api('projects/interface',{id:key});if(schema.commands.length!==2)throw Error(JSON.stringify(schema));
  const page=await browser.newPage({viewport:{width:1440,height:900}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.addInitScript(()=>localStorage.setItem('projects.korean','false'));
  await page.goto('http://127.0.0.1:8766/#'+record.menu);await page.getByLabel('실행할 기능').waitFor();
  await page.getByLabel('실행할 기능').selectOption(schema.commands.find(item=>item.path[0]==='report').id);
  await page.getByLabel('name',{exact:true}).fill('자동 생성 화면 보고서');await page.getByLabel('count',{exact:true}).fill('4');
  await page.getByLabel('format',{exact:true}).selectOption('json');await page.getByLabel('verbose',{exact:true}).check();await page.getByLabel('tag',{exact:true}).fill('one\ntwo');
  await page.getByRole('button',{name:'실행',exact:true}).click();await page.getByLabel('프로그램 실행 결과').filter({hasText:'자동 생성 화면 보고서'}).waitFor();
  let output=JSON.parse(await fs.readFile(path.join(record.active_source,'generated-result.json'),'utf8'));
  if(output.count!==4||!output.verbose||output.tag.length!==2)throw Error(JSON.stringify(output));
  await page.screenshot({path:path.join(base,'automatic-ui-desktop.png'),fullPage:true});
  await page.getByLabel('실행할 기능').selectOption(schema.commands.find(item=>item.path[0]==='sum').id);
  await page.getByLabel('numbers',{exact:true}).fill('3\n4');await page.getByRole('button',{name:'실행',exact:true}).click();await page.getByLabel('프로그램 실행 결과').filter({hasText:'numbers'}).waitFor();
  output=JSON.parse(await fs.readFile(path.join(record.active_source,'generated-result.json'),'utf8'));if(JSON.stringify(output.numbers)!=='[3,4]')throw Error(JSON.stringify(output));
  await page.setViewportSize({width:390,height:844});if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('horizontal overflow');
  await page.screenshot({path:path.join(base,'automatic-ui-mobile.png'),fullPage:true});if(errors.length)throw Error(JSON.stringify(errors));
  console.log('Generated two command forms; original program execution and file output verified');
  await api('projects/remove',{id:key});await until(async()=>!(await api('projects/installed')).active_module_ids.includes(record.module_id));key=null;
  const report={source_without_ui:true,automatic_detection:true,automatic_install_folder:true,menu_registered:true,generated_commands:2,typed_controls:true,original_program_executed:true,original_result_file:true,per_project_ui_code:false,mobile_overflow:false,javascript_errors:errors,model_used:false,removed:true};
  await fs.writeFile(path.join(base,'automatic-ui.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));
 }finally{if(key)await api('projects/remove',{id:key}).catch(()=>{});if(browser)await browser.close();const relative=path.relative(base,path.resolve(temporary));if(relative.startsWith('..')||path.isAbsolute(relative))throw Error('temporary folder boundary');await fs.rm(temporary,{recursive:true,force:true})}
})().catch(e=>{console.error(e);process.exitCode=1});
