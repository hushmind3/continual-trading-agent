import type {MenuItem} from './menu_groups/menu_types';

export interface InstalledManifest {
 id:string;
 install_revision?:string;
 workspace_host?:string;
 app_title?:string;
 group?:{title:string};
}

/** Installed apps share an origin group, but retain their own section and routes. */
export function installedNavigation(manifest:InstalledManifest,menus:MenuItem[]):MenuItem[]{
 if(manifest.workspace_host==='hermes/chat')return [];
 if(!manifest.install_revision)return menus;
 const title=manifest.app_title
  ||(manifest.group?.title!=='GitHub'?manifest.group?.title:undefined)
  ||menus[0]?.section?.name||menus[0]?.name||manifest.id;
 return menus.map(menu=>({...menu,group:'GitHub',
  section:{id:manifest.id,name:title,icon:menu.section?.icon||menu.icon},
  name:menu.section?menu.section.name+' · '+menu.name:menu.name===title?'실행':menu.name,
 }));
}
