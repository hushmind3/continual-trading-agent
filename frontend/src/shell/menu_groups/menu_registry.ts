import {menus as rea} from './rea_menu_manager';
import {menus as trading} from './trading_menu_manager';
import {menus as finrl,registeredMenus as finrlMenus} from './finrl_menu_manager';
import {menus as extensions,registeredMenus as extensionMenus} from './extensions_menu_manager';
import {menus as management} from './management_menu_manager';
export const navigation=[...trading,...finrl,...rea,...extensions,...management];
export function registeredNavigation(actions:Parameters<typeof finrlMenus>[0]){return [...trading,...finrlMenus(actions),...rea,...extensionMenus(actions),...management];}
