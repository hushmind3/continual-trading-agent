import {lazy} from 'react';
import {GraduationCap,Workflow} from 'lucide-react';
import {actionMenus,type MenuItem} from '../../../shell/menu_groups/menu_types';
import type {BackendAction} from '../../../data/menu_types';
const feature=lazy(()=>import('../management/all_backend_features/AllBackendFeatures').then(m=>({default:m.AllBackendFeatures})));
export const menus:MenuItem[]=[
 {hash:'finance/policy_learning',name:'정책 학습',group:'FinRL · 메인',icon:GraduationCap,component:lazy(()=>import('./policy_learning/PolicyLearning').then(m=>({default:m.PolicyLearning}))),required:['settings','model','data','experts','job','checkpoints','resources']},
 {hash:'finance/finrl_modules_tools',name:'FinRL 모듈 · 도구',group:'FinRL · 메인',icon:Workflow,component:lazy(()=>import('./finrl_modules_tools/FinrlModulesTools').then(m=>({default:m.FinrlModulesTools}))),required:['job']},
];
export function registeredMenus(actions:BackendAction[]){return [...menus,...actionMenus(actions,'finrl','FinRL · 메인',feature,Workflow)];}
