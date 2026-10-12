import type {ComponentType,LazyExoticComponent} from 'react';
import type {LucideIcon} from 'lucide-react';
import type {Snapshot} from '../../data/types';
export interface MenuItem {hash:string;name:string;group:string;icon:LucideIcon;component:LazyExoticComponent<ComponentType>;required:(keyof Snapshot)[]}
