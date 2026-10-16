import {Input} from '../../../../ui/Primitives';

interface Props {
  mode: string; pending: boolean; turns: number; setTurns: (value: number) => void;
  interval: number; setIntervalSeconds: (value: number) => void; times: number; setTimes: (value: number) => void;
}
export function RunModeOptions({mode, pending, turns, setTurns, interval, setIntervalSeconds, times, setTimes}: Props) {
  if (mode === 'chat') return null;
  return <div className="hermes-run-options">
    {mode === 'goal' ? <label>최대 대화 <Input aria-label="목표 최대 대화 수" type="number" min={1} max={1000} value={turns} disabled={pending} onChange={e => setTurns(Number(e.target.value))}/></label>
      : <><label>간격(초, 0은 자동) <Input aria-label="반복 간격" type="number" min={0} value={interval} disabled={pending} onChange={e => setIntervalSeconds(Number(e.target.value))}/></label>
        <label>횟수(0은 기본 한도) <Input aria-label="반복 횟수" type="number" min={0} value={times} disabled={pending} onChange={e => setTimes(Number(e.target.value))}/></label></>}
  </div>;
}
