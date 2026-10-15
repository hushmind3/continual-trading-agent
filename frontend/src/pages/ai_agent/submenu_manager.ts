import {lazy} from 'react';
import {Bot} from 'lucide-react';
import type {MenuItem} from '../../shell/menu_groups/menu_types';

export const menus:MenuItem[]=[{
 hash:'ai_agent/Hermes',name:'Hermes',group:'AI Agent',icon:Bot,
 component:lazy(()=>import('./Hermes/Hermes').then(m=>({default:m.Hermes}))),required:[],
}];
