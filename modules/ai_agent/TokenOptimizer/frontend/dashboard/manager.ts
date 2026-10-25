import {lazy} from 'react';
import {Gauge} from 'lucide-react';
import type {MenuItem} from '@platform/shell/menu_groups/menu_types';

export const menus:MenuItem[]=[{
 hash:'ai_agent/TokenOptimizer/dashboard',name:'대시보드',group:'AI 에이전트',icon:Gauge,
 section:{id:'TokenOptimizer',name:'토큰 최적화',icon:Gauge},required:[],
 component:lazy(()=>import('./Dashboard').then(module=>({default:module.Dashboard}))),
}];
