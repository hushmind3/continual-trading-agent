import {Suspense, useState} from 'react';
import {Bot, Database, Globe, KeyRound, Settings2, Users} from 'lucide-react';
import {Empty} from '../ui/Primitives';
import {SettingsWorkspace} from '../ui/SettingsWorkspace';
import {sharedSettings} from './module_loader';

const icons = {settings: Settings2, users: Users, globe: Globe, bot: Bot, key: KeyRound, database: Database};
export function SharedSettings() {
  const [selected, setSelected] = useState(sharedSettings[0]?.id ?? '');
  const active = sharedSettings.find(item => item.id === selected) ?? sharedSettings[0];
  if (!active) return <Empty title="등록된 공용 설정이 없습니다"/>;
  const Component = active.component;
  return <SettingsWorkspace items={sharedSettings.map(item => ({...item, icon: icons[item.icon as keyof typeof icons] ?? Settings2}))} value={active.id} onChange={setSelected}>
    <Suspense fallback={<p className="text-sm text-slate-500">설정을 불러오는 중입니다.</p>}><Component page={active.page} navigate={page => {
      const target = active.scope + '/' + page;
      if (sharedSettings.some(item => item.id === target)) setSelected(target);
    }}/></Suspense>
  </SettingsWorkspace>;
}
