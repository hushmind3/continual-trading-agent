import {lazy} from 'react';
import {Box, History, LayoutDashboard, Plug, Settings} from 'lucide-react';
import type {MenuItem} from '@platform/shell/menu_groups/menu_types';
const component = lazy(() => import('./Nazarick').then(module => ({default: module.Nazarick})));
const section = {id: 'nazarick', name: '나자릭', icon: Box};
export const settingsPage = lazy(() => import('./accounts/Accounts').then(module => ({default: module.Accounts})));
export const menus: MenuItem[] = [
  {hash: 'overlord/nazarick/accounts', name: '공용 설정', group: '오버로드', section, icon: Settings, component: lazy(() => import('@platform/shell/SharedSettings').then(module => ({default: module.SharedSettings}))), required: [], sidebar: false},
  {hash: 'overlord/nazarick/overview', name: '기반 개요', group: '오버로드', section, icon: LayoutDashboard, component, required: [], mountKey: 'overlord/nazarick'},
  {hash: 'overlord/nazarick/connections', name: '연결 대상', group: '오버로드', section, icon: Plug, component, required: [], mountKey: 'overlord/nazarick'},
  {hash: 'overlord/nazarick/activity', name: '작업 기록', group: '오버로드', section, icon: History, component, required: [], mountKey: 'overlord/nazarick'},
];
