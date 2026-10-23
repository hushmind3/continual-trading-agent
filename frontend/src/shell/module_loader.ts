import type {MenuItem} from './menu_groups/menu_types';
import type {BackendAction} from '../data/menu_types';
import type {ComponentType, LazyExoticComponent} from 'react';
import {installedNavigation,type InstalledManifest} from './installed_navigation';
export interface SharedSettingsProps {page: string; navigate: (page: string) => void}
interface SettingDefinition {id: string; label: string; description: string; icon?: string}
interface Manifest extends InstalledManifest {schema:number;enabled?:boolean;order?:number;frontend:{entry:string};shared_settings?:SettingDefinition[]}
interface Registration {menus:MenuItem[];registeredMenus?:(actions:BackendAction[])=>MenuItem[];settingsPage?:LazyExoticComponent<ComponentType<SharedSettingsProps>>}
const manifests=import.meta.glob<Manifest>(['../../../modules/*/module.json','../../../modules/*/*/module.json'],{eager:true,import:'default'});
const entries=import.meta.glob<Registration>(['../../../modules/*/frontend/register.ts','../../../modules/*/*/frontend/register.ts'],{eager:true});
const enabled=Object.entries(manifests).filter(([,manifest])=>manifest.enabled!==false)
 .sort(([,a],[,b])=>(a.order??100)-(b.order??100)||a.id.localeCompare(b.id))
 .map(([path,manifest])=>{
  if(manifest.schema!==1)throw new Error('지원하지 않는 모듈 규격: '+manifest.id);
  const entry=entries[path.replace('module.json',manifest.frontend.entry)];
  if(!entry)throw new Error('모듈 화면 등록 파일이 없습니다: '+manifest.id);
  if(manifest.shared_settings?.length&&!entry.settingsPage)throw new Error('설정 화면 등록이 없습니다: '+manifest.id);
  if(manifest.workspace_host==='hermes/chat'){
   const redirect=()=>{if(entry.menus.some(menu=>location.hash==='#'+menu.hash))location.replace('#ai_agent/Hermes')};
   redirect();window.addEventListener('hashchange',redirect);
  }
  return {...entry,menus:installedNavigation(manifest,entry.menus),
   settings:(manifest.shared_settings??[]).map(item=>({...item,id:manifest.id+'/'+item.id,page:item.id,scope:manifest.id,component:entry.settingsPage!})),
   registeredMenus:entry.registeredMenus
    ?(actions:BackendAction[])=>installedNavigation(manifest,entry.registeredMenus!(actions)):undefined};
 });
export function registeredNavigation(actions:BackendAction[]){return enabled.flatMap(entry=>entry.registeredMenus?entry.registeredMenus(actions):entry.menus)}
export const navigation=registeredNavigation([]);
export const sharedSettings=enabled.flatMap(entry=>entry.settings);
if(new Set(sharedSettings.map(item=>item.id)).size!==sharedSettings.length)throw new Error('공용 설정 ID가 중복됐습니다.');
