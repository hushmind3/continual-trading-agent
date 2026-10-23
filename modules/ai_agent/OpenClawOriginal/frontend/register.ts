import {lazy} from 'react';
import {Bot} from 'lucide-react';
import type {MenuItem} from '@platform/shell/menu_groups/menu_types';

export const menus:MenuItem[]=[{
 hash:'ai_agent/OpenClawOriginal',name:'원본 화면',group:'AI 에이전트',icon:Bot,
 section:{id:'OpenClawOriginal',name:'OpenClaw 원본',icon:Bot},
 component:lazy(()=>import('./Original').then(m=>({default:m.Original}))),
 required:[],mountKey:'ai_agent/OpenClawOriginal',
}];
