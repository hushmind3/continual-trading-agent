import {useState, type FormEvent} from 'react';
import {Button, Drawer, ErrorMessage, Input, Select, Textarea} from '@platform/ui/Primitives';
import {categories, type Adapter, type Category, type Connection, type Definition} from './types';

export function ConnectionForm({item, category, adapters, initialAdapter = 'planned', close, save}: {
  item: Connection | null; category: Category; adapters: Adapter[]; initialAdapter?: Definition['adapter']; close: () => void;
  save: (value: Definition) => Promise<void>;
}) {
  const [value, setValue] = useState<Definition>(item ? {
    id: item.id, name: item.name, category: item.category, adapter: item.adapter, target: item.target, notes: item.notes,
  } : {name: '', category, adapter: initialAdapter, target: '', notes: ''});
  const [error, setError] = useState(''), [busy, setBusy] = useState(false);
  const targets = adapters.find(adapter => adapter.id === 'platform_module')?.targets ?? [];
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError('');
    try {await save(value); close()} catch (failure) {setError(String(failure))} finally {setBusy(false)}
  }
  return <Drawer title={item ? '연결 대상 수정' : '연결 대상 추가'} open onClose={() => {if (!busy) close()}}>
    <form onSubmit={event => void submit(event)} className="mt-5 space-y-5">
      <p className="text-sm leading-6 text-slate-500">어디에 무엇을 붙일지 등록합니다. 외부 서비스는 연결부를 구현하기 전까지 연결 예정으로 남습니다.</p>
      <label className="block space-y-2 text-sm font-medium">대상 이름<Input required maxLength={80} autoFocus value={value.name} placeholder="연결할 기능이나 서비스 이름" onChange={event => setValue({...value, name: event.target.value})}/></label>
      <label className="block space-y-2 text-sm font-medium">연결 영역<Select aria-label="연결 영역" value={value.category} onChange={event => setValue({...value, category: event.target.value as Category})}>{categories.map(option => <option key={option.id} value={option.id}>{option.name}</option>)}</Select></label>
      <label className="block space-y-2 text-sm font-medium">연결 방식<Select aria-label="연결 방식" value={value.adapter} onChange={event => setValue({...value, adapter: event.target.value as Definition['adapter'], target: ''})}><option value="planned">외부 서비스 · 연결 예정</option><option value="platform_module">기존 플랫폼 기능 · 등록 확인 가능</option></Select></label>
      {value.adapter === 'platform_module' && <label className="block space-y-2 text-sm font-medium">플랫폼 기능<Select aria-label="플랫폼 기능" required value={value.target} onChange={event => setValue({...value, target: event.target.value, name: value.name || targets.find(target => target.id === event.target.value)?.name || ''})}><option value="">기능 선택</option>{targets.map(target => <option key={target.id} value={target.id}>{target.name} · {target.id}{target.available ? '' : ' (등록 오류)'}</option>)}</Select></label>}
      <label className="block space-y-2 text-sm font-medium">용도 메모<Textarea rows={4} maxLength={1000} value={value.notes} placeholder="이 연결을 어떤 용도로 사용할지 적어주세요." onChange={event => setValue({...value, notes: event.target.value})}/></label>
      <ErrorMessage message={error}/>
      <div className="flex justify-end gap-2 border-t border-slate-200 pt-5"><Button disabled={busy} onClick={close}>취소</Button><Button type="submit" tone="primary" busy={busy}>대상 저장</Button></div>
    </form>
  </Drawer>;
}
