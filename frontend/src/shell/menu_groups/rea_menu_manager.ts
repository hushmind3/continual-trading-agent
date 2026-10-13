import {lazy} from 'react';
import {ScanSearch,FolderTree} from 'lucide-react';
import type {MenuItem} from './menu_types';
export const menus:MenuItem[]=[
 {hash:'rea',name:'프로그램 분석',group:'REA 역공학',icon:ScanSearch,component:lazy(()=>import('../../pages/rea/REAWorkspace').then(m=>({default:m.REAWorkspace}))),required:['job']},
 {hash:'rea-projects',name:'프로젝트 탐색',group:'REA 역공학',icon:FolderTree,component:lazy(()=>import('../../pages/rea/REAWorkspace').then(m=>({default:m.REAProjects}))),required:['job']},
];
