import {lazy} from 'react';
import {ScanSearch} from 'lucide-react';
import type {MenuItem} from './menu_types';
export const menus:MenuItem[]=[{hash:'rea',name:'분석 · 진단',group:'REA',icon:ScanSearch,component:lazy(()=>import('../../pages/rea/REAWorkspace').then(m=>({default:m.REAWorkspace}))),required:['job']}];
