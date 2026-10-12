import {lazy} from 'react';
import {SlidersHorizontal,Stethoscope} from 'lucide-react';
import type {MenuItem} from './menu_types';
export const menus:MenuItem[]=[
 {hash:'connection',name:'연결 · 설정',group:'연결 · 관리',icon:SlidersHorizontal,component:lazy(()=>import('../../pages/settings/ConnectionSettings').then(m=>({default:m.ConnectionSettings}))),required:['settings','data','experts','model']},
 {hash:'system',name:'진단 · 로그 · 코드 적용',group:'연결 · 관리',icon:Stethoscope,component:lazy(()=>import('../../pages/system/Diagnostics').then(m=>({default:m.Diagnostics}))),required:['settings','resources','job']}
];
