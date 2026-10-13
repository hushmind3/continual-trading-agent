import {lazy} from 'react';
import {ScanSearch,FolderTree} from 'lucide-react';
import type {MenuItem} from '../../shell/menu_groups/menu_types';
export const menus:MenuItem[]=[
 {hash:'rea/program_analysis',name:'프로그램 분석',group:'REA 역공학',icon:ScanSearch,component:lazy(()=>import('./program_analysis/ProgramAnalysis').then(m=>({default:m.ProgramAnalysis}))),required:['job']},
 {hash:'rea/project_explorer',name:'프로젝트 탐색',group:'REA 역공학',icon:FolderTree,component:lazy(()=>import('./project_explorer/ProjectExplorer').then(m=>({default:m.ProjectExplorer}))),required:['job']},
];
