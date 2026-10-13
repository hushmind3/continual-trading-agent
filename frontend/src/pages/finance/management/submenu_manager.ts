import {lazy} from 'react';
import {SlidersHorizontal,Stethoscope,Workflow} from 'lucide-react';
import type {MenuItem} from '../../../shell/menu_groups/menu_types';
export const menus:MenuItem[]=[
 {hash:'finance/connection_settings',name:'연결 · 설정',group:'연결 · 관리',icon:SlidersHorizontal,component:lazy(()=>import('./connection_settings/ConnectionSettings').then(m=>({default:m.ConnectionSettings}))),required:['settings','data','experts','model']},
 {hash:'finance/diagnostics_logs_code_apply',name:'진단 · 로그 · 코드 적용',group:'연결 · 관리',icon:Stethoscope,component:lazy(()=>import('./diagnostics_logs_code_apply/DiagnosticsLogsCodeApply').then(m=>({default:m.DiagnosticsLogsCodeApply}))),required:['settings','resources','job']},
 {hash:'finance/all_backend_features',name:'백엔드 기능 전체',group:'연결 · 관리',icon:Workflow,component:lazy(()=>import('./all_backend_features/AllBackendFeatures').then(m=>({default:m.AllBackendFeatures}))),required:['job']}
];
