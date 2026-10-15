import {menus as finance,registeredMenus as financeMenus} from '../../pages/finance/finance_menu_manager';
import {menus as rea} from '../../pages/rea/rea_menu_manager';
import {menus as aiAgent} from '../../pages/ai_agent/ai_agent_menu_manager';
export const navigation=[...finance,...rea,...aiAgent];
export function registeredNavigation(actions:Parameters<typeof financeMenus>[0]){return [...financeMenus(actions),...rea,...aiAgent];}
