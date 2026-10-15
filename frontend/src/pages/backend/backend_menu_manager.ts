import {lazy} from 'react';
import {Braces} from 'lucide-react';
import type {MenuItem} from '../../shell/menu_groups/menu_types';

export const menus:MenuItem[]=[{
  hash:'backend/api', name:'백엔드 API', group:'백엔드 API', icon:Braces,
  component:lazy(()=>import('./BackendApiPage').then(m=>({default:m.BackendApiPage}))),
  required:[], standalone:true,
}];
