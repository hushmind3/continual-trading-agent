import {lazy} from 'react';
import {Package,Search} from 'lucide-react';
import type {MenuItem} from '@platform/shell/menu_groups/menu_types';
const component=lazy(()=>import('./Projects').then(module=>({default:module.Projects})));
export const menus:MenuItem[]=[
 {hash:'projects/manage/search',name:'GitHub에서 추가',group:'프로젝트',section:{id:'manage',name:'프로젝트 관리',icon:Package},icon:Search,component,required:[],mountKey:'projects/manage'},
 {hash:'projects/manage/installed',name:'설치된 프로젝트',group:'프로젝트',section:{id:'manage',name:'프로젝트 관리',icon:Package},icon:Package,component,required:[],mountKey:'projects/manage'},
];
