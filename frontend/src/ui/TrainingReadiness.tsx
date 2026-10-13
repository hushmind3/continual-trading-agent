import {useOperations} from '../data/Operations';
import {Status} from './Primitives';
export function TrainingReadiness(){const {state}=useOperations();return <Status tone={state?.job.running?'good':'idle'}>{state?.job.running?'공식 작업 실행 중':'시작 전 데이터·정책 검사 필요'}</Status>}
