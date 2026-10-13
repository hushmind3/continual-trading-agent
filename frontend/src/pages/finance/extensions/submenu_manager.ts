import {lazy} from 'react';
import {Boxes,Workflow} from 'lucide-react';
import {actionMenus,type MenuItem} from '../../../shell/menu_groups/menu_types';
import type {BackendAction} from '../../../data/menu_types';
const feature=lazy(()=>import('../management/backend_browser/FeatureWorkspace').then(m=>({default:m.FeatureWorkspace})));
export const menus:MenuItem[]=[
 {hash:'moe',name:'MoE',group:'프로젝트 확장',icon:Boxes,component:lazy(()=>import('./moe/ModelWorkspace').then(m=>({default:m.ModelWorkspace}))),required:['experts','job','library']},
 {hash:'project-modules',name:'프로젝트 모듈',group:'프로젝트 확장',icon:Workflow,component:lazy(()=>import('./project_modules/ProjectModulesWorkspace').then(m=>({default:m.ProjectModulesWorkspace}))),required:['job']},
];
export function registeredMenus(actions:BackendAction[]){return [...menus,...actionMenus(actions,'extensions','프로젝트 확장',feature,Workflow)];}
