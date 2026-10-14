import {lazy} from 'react';
import {SlidersHorizontal} from 'lucide-react';
import type {MenuItem} from '../../../shell/menu_groups/menu_types';
export const menus:MenuItem[]=[
 {hash:'finance/connection_settings',name:'연결 · 설정',group:'연결 · 관리',icon:SlidersHorizontal,component:lazy(()=>import('./connection_settings/ConnectionSettings').then(m=>({default:m.ConnectionSettings}))),required:['settings','data','experts','model']}
];
