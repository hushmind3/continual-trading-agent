import {menus as trading} from './trading_menu_manager';
import {menus as finrl,registeredMenus as finrlMenus} from './finrl_menu_manager';
import {menus as finrl_trading,registeredMenus as tradingMenus} from './finrl_trading_menu_manager';
import {menus as extensions,registeredMenus as extensionMenus} from './extensions_menu_manager';
import {menus as management} from './management_menu_manager';
export const navigation=[...trading,...finrl,...finrl_trading,...extensions,...management];
export function registeredNavigation(actions:Parameters<typeof finrlMenus>[0]){return [...trading,...finrlMenus(actions),...tradingMenus(actions),...extensionMenus(actions),...management];}
