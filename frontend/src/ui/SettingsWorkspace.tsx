import {useId, useRef, type ReactNode} from 'react';
import type {LucideIcon} from 'lucide-react';
import {Button} from './Primitives';

export interface SettingsCategory {id: string; label: string; description: string; icon: LucideIcon}

export function SettingsWorkspace({items, value, onChange, children, actions}: {
  items: SettingsCategory[]; value: string; onChange: (id: string) => void; children: ReactNode; actions?: ReactNode;
}) {
  const id = useId(), navigation = useRef<HTMLElement>(null), active = items.find(item => item.id === value) ?? items[0];
  return <div className="ui-settings-workspace">
    <nav ref={navigation} className="ui-settings-navigation" role="tablist" aria-label="공용 설정 항목" aria-orientation="vertical">
      {items.map((item, index) => <Button key={item.id} role="tab" variant="ghost" id={id + '-' + item.id} aria-controls={id + '-panel'} aria-selected={item.id === value} tabIndex={item.id === value ? 0 : -1} className="ui-settings-category" onClick={() => onChange(item.id)} onKeyDown={event => {
        const offset = event.key === 'ArrowDown' || event.key === 'ArrowRight' ? 1 : event.key === 'ArrowUp' || event.key === 'ArrowLeft' ? -1 : 0;
        if (!offset && event.key !== 'Home' && event.key !== 'End') return;
        event.preventDefault(); const next = event.key === 'Home' ? 0 : event.key === 'End' ? items.length - 1 : (index + offset + items.length) % items.length;
        onChange(items[next].id); navigation.current?.querySelectorAll<HTMLButtonElement>('[role="tab"]')[next]?.focus();
      }}><item.icon size={17}/><span>{item.label}</span></Button>)}
      <p className="ui-settings-navigation-note">프로젝트 플랫폼<br/>모든 에이전트의 공용 설정</p>
    </nav>
    <section id={id + '-panel'} role="tabpanel" aria-labelledby={id + '-' + active.id} tabIndex={0} className="ui-settings-content">
      <header className="ui-settings-content-heading"><div><h3>{active.label}</h3><p>{active.description}</p></div>{actions}</header>
      {children}
    </section>
  </div>;
}
