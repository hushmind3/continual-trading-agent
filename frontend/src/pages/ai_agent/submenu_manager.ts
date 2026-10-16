import {lazy} from 'react';
import {Bot} from 'lucide-react';
import type {MenuItem} from '../../shell/menu_groups/menu_types';
import {agentPages,agentHref,hermesRoute} from './agent_navigation';
const workspace=lazy(()=>import('./Hermes/Hermes').then(module=>({default:module.Hermes})));
// Reuse one mounted engine workspace so changing menus preserves the conversation.
export const menus:MenuItem[]=agentPages.map(page=>({
 hash:agentHref(page.id).slice(1),name:page.name,group:'AI 에이전트',icon:page.icon,section:{id:'Hermes',name:'헤르메스',icon:Bot},
 component:workspace,required:[],mountKey:hermesRoute,
}));
