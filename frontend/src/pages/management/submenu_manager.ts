import {lazy} from 'react';
import {SlidersHorizontal,Stethoscope,Workflow} from 'lucide-react';
import type {MenuItem} from '../../shell/menu_groups/menu_types';
export const menus:MenuItem[]=[
 {hash:'connection',name:'연결 · 설정',group:'연결 · 관리',icon:SlidersHorizontal,component:lazy(()=>import('./connection_settings/ConnectionSettings').then(m=>({default:m.ConnectionSettings}))),required:['settings','data','experts','model']},
 {hash:'system',name:'진단 · 로그 · 코드 적용',group:'연결 · 관리',icon:Stethoscope,component:lazy(()=>import('./diagnostics/Diagnostics').then(m=>({default:m.Diagnostics}))),required:['settings','resources','job']},
 {hash:'backend-browser',name:'백엔드 기능 전체',group:'연결 · 관리',icon:Workflow,component:lazy(()=>import('./backend_browser/FeatureWorkspace').then(m=>({default:m.FeatureWorkspace}))),required:['job']}
];
