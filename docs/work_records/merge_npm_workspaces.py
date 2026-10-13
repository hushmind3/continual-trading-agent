from pathlib import Path
import json,copy,os
R=Path(r'C:\Users\hushm\Desktop\금융매매모델')
ws=['frontend','backend/rea'];locks={name:json.loads((R/name/'package-lock.json').read_text(encoding='utf8')) for name in ws}
root={'name':'project-platform','version':'1.0.0','private':True,'workspaces':ws,'engines':locks['backend/rea']['packages'][''].get('engines',{'node':'^22.19.0 || ^24.11.0 || >=26.0.0'}),'scripts':{'dev':'npm run dev --workspace frontend','build':'npm run build --workspace frontend','typecheck':'npm run typecheck --workspace frontend','test:api':'npm run test:api --workspace frontend','test:browser':'npm run test:browser --workspace frontend'}}
packages={'':{'name':root['name'],'version':root['version'],'workspaces':ws,'engines':root['engines']}}
for name,lock in locks.items():
 metadata=copy.deepcopy(lock['packages']['']);packages[name]=metadata;packages['node_modules/'+metadata['name']]={'resolved':name,'link':True}
for k,v in locks['frontend']['packages'].items():
 if k:packages[k]=copy.deepcopy(v)
for k,v in locks['backend/rea']['packages'].items():
 if k and k not in packages:packages[k]=copy.deepcopy(v)
def resolve(entries,parent,dep):
 current=parent
 while True:
  candidate=(current+'/' if current else '')+'node_modules/'+dep
  if candidate in entries:return candidate
  if not current:return None
  current=current.rpartition('/')[0]
seen=set()
def wire(old_key,new_key):
 pair=(old_key,new_key)
 if pair in seen:return
 seen.add(pair);data=locks['backend/rea']['packages'][old_key]
 deps={**data.get('dependencies',{}),**data.get('optionalDependencies',{})}
 for dep in deps:
  old_child=resolve(locks['backend/rea']['packages'],old_key,dep)
  if not old_child:continue
  expected=locks['backend/rea']['packages'][old_child];current=resolve(packages,new_key,dep)
  if current and packages[current].get('version')==expected.get('version'):target=current
  else:
   target=new_key+'/node_modules/'+dep;packages[target]=copy.deepcopy(expected)
  if not expected.get('dev'):packages[target].pop('dev',None)
  wire(old_child,target)
for dep in locks['backend/rea']['packages'][''].get('dependencies',{}):
 key='node_modules/'+dep;wire(key,key);packages[key].pop('dev',None)
(R/'package.json').write_text(json.dumps(root,indent=2)+'\n',encoding='utf8')
(R/'package-lock.json').write_text(json.dumps({'name':root['name'],'version':root['version'],'lockfileVersion':3,'requires':True,'packages':packages},indent=2)+'\n',encoding='utf8')
before={(k.split('node_modules/')[-1],v.get('version')) for lock in locks.values() for k,v in lock['packages'].items() if k and v.get('version')}
(Path(os.environ['TEMP'])/'npm_original_versions.json').write_text(json.dumps(sorted(before)),encoding='utf8')
print(json.dumps({'root_lock_packages':len(packages),'workspace_local_node_modules':sum(k.startswith(('frontend/node_modules','backend/rea/node_modules')) for k in packages),'retained_package_versions':len(before)}))
