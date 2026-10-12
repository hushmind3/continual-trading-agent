import {lazy} from 'react';
import {Boxes,Workflow} from 'lucide-react';
import type {MenuItem} from './menu_types';
export const menus:MenuItem[]=[
 {hash:'moe',name:'MoE',group:'프로젝트 확장',icon:Boxes,component:lazy(()=>import('../../pages/model/ModelWorkspace').then(m=>({default:m.ModelWorkspace}))),required:['experts','job','library']},
 {hash:'project-modules',name:'프로젝트 모듈',group:'프로젝트 확장',icon:Workflow,component:lazy(()=>import('../../pages/frameworks/FrameworkWorkspace').then(m=>({default:m.ProjectModulesWorkspace}))),required:['job']},
];
