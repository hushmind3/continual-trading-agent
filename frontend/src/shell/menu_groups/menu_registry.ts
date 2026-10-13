import {menus as rea} from '../../pages/rea/rea_menu_manager';
import {menus as trading} from '../../pages/trading/trading_menu_manager';
import {menus as finrl,registeredMenus as finrlMenus} from '../../pages/finrl/finrl_menu_manager';
import {menus as extensions,registeredMenus as extensionMenus} from '../../pages/extensions/extensions_menu_manager';
import {menus as management} from '../../pages/management/management_menu_manager';
export const navigation=[...trading,...finrl,...rea,...extensions,...management];
export function registeredNavigation(actions:Parameters<typeof finrlMenus>[0]){return [...trading,...finrlMenus(actions),...rea,...extensionMenus(actions),...management];}
