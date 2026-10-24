import {lazy} from 'react';
import {MousePointer2} from 'lucide-react';
import type {MenuItem} from '@platform/shell/menu_groups/menu_types';

export const menus:MenuItem[]=[{
 hash:'ai_agent/HermesOperator',name:'조종기',group:'AI 에이전트',icon:MousePointer2,
 section:{id:'HermesOperator',name:'Hermes 조종기',icon:MousePointer2},
 component:lazy(()=>import('./HermesOperator').then(m=>({default:m.HermesOperator}))),
 required:[],mountKey:'ai_agent/HermesOperator',
}];
