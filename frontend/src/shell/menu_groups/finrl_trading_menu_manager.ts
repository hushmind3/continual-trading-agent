import {lazy} from 'react';
import {Workflow} from 'lucide-react';
import type {MenuItem} from './menu_types';
export const menus:MenuItem[]=[
 {hash:'finrl-trading',name:'보조 데이터 · 전략 · 도구',group:'FinRL-Trading · 보조',icon:Workflow,component:lazy(()=>import('../../pages/frameworks/FrameworkWorkspace').then(m=>({default:m.FinrlTradingWorkspace}))),required:['job']},
];
