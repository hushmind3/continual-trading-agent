import {lazy} from 'react';
import {Bot} from 'lucide-react';
import type {MenuItem} from '@platform/shell/menu_groups/menu_types';
import {agentPages,agentHref,hermesRoute} from './agent_navigation';
const workspace=lazy(()=>import('./Hermes').then(module=>({default:module.Hermes})));
// Reuse one mounted engine workspace so changing menus preserves the conversation.
export const menus:MenuItem[]=agentPages.map(page=>({
 hash:agentHref(page.id).slice(1),name:page.id==='chat'?'헤르메스':page.name,group:'AI 에이전트',icon:page.id==='chat'?Bot:page.icon,sidebar:page.id==='chat',
 component:workspace,required:[],mountKey:hermesRoute,
}));
