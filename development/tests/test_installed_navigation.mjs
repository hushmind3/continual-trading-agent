import assert from 'node:assert/strict';
import test from 'node:test';
import {installedNavigation} from '../../frontend/src/shell/installed_navigation.ts';

const icon=()=>null;
const component=()=>null;
const menu=(name,hash)=>({name,hash,group:name,icon,component,required:[]});

test('built-in engine menus retain their original ownership and identity',()=>{
 const entries=[{...menu('MCP','ai_agent/Hermes/mcp'),group:'AI 에이전트',section:{id:'Hermes',name:'헤르메스',icon}}];
 assert.equal(installedNavigation({id:'hermes'},entries),entries);
 assert.equal(entries[0].group,'AI 에이전트');
});

test('existing installed apps share GitHub but retain independent app sections and routes',()=>{
 const entries=['rea','editor'].map(name=>{
  const original=menu(name,'projects/app/'+name);
  const [result]=installedNavigation({id:'external_'+name,install_revision:'v1',group:{title:name}},[original]);
  assert.equal(result.hash,original.hash);
  assert.equal(result.component,component);
  assert.equal(result.name,'실행');
  assert.equal(result.group,'GitHub');
  assert.equal(result.section.name,name);
  assert.equal(original.group,name);
  return result;
 });
 assert.notEqual(entries[0].section.id,entries[1].section.id);
});

test('native apps preserve feature labels beneath their own app title',()=>{
 const [result]=installedNavigation({id:'external_native',install_revision:'v2',app_title:'Native app',group:{title:'GitHub'}},[
  {...menu('설정','native/settings'),section:{id:'tools',name:'도구',icon}},
 ]);
 assert.equal(result.section.name,'Native app');
 assert.equal(result.name,'도구 · 설정');
 assert.equal(result.hash,'native/settings');
});
