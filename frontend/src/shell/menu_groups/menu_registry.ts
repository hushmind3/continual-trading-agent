import {menus as trading} from './trading_menu_manager';
import {menus as finrl} from './finrl_menu_manager';
import {menus as finrl_trading} from './finrl_trading_menu_manager';
import {menus as extensions} from './extensions_menu_manager';
import {menus as management} from './management_menu_manager';
export const navigation=[...trading,...finrl,...finrl_trading,...extensions,...management];
