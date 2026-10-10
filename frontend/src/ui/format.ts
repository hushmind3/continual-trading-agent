import type { Currency, Worker } from "../data/types";
export const accountNames:Record<Currency,string>={KRW:'국내주식 · 원화 가상계좌',USD:'미국주식 · 달러 가상계좌'};
export const number = (value: number | undefined | null, digits = 1) =>
  value == null || !Number.isFinite(value)
    ? "미수신"
    : new Intl.NumberFormat("ko-KR", { maximumFractionDigits: digits }).format(
        value,
      );
export const money = (value: number, currency: Currency) =>
  new Intl.NumberFormat(currency === "KRW" ? "ko-KR" : "en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: currency === "KRW" ? 0 : 2,
  }).format(value);
export const percent = (value: number, digits = 2) => `${number(value * 100, digits)}%`;
export function inferenceChange(ratio:number|undefined){
  if(ratio==null||!Number.isFinite(ratio)||ratio<=0)return '추론 시간 미측정';
  const delta=(1/ratio-1)*100;
  return Math.abs(delta)<.5?'추론 시간 거의 동일':`추론 시간 ${number(Math.abs(delta),1)}% ${delta>0?'증가 · 느림':'감소 · 빠름'}`;
}
export function calendarDate(value:string|undefined|null){
  if(!value)return '공개 정보 없음';
  const d=new Date(value);return Number.isNaN(d.valueOf())?'공개 정보 없음':new Intl.DateTimeFormat('ko-KR',{year:'numeric',month:'2-digit',day:'2-digit'}).format(d);
}
export function inspectionDetail(value:string){
  if(value.includes('expert returned nonfinite values'))return '추론 출력에 NaN/Inf 발생 · 이 정밀도 버전은 사용 차단';
  return value.includes('Traceback')?value.trim().split('\n').at(-1)??value:value;
}
export const bytes = (value: number | undefined) =>
  value == null
    ? "미측정"
    : value >= 2 ** 30
      ? `${number(value / 2 ** 30)} GiB`
      : value >= 2 ** 20
        ? `${number(value / 2 ** 20)} MiB`
        : `${number(value / 1024)} KiB`;
export const date = (value: string | number | undefined | null) => {
  if (value == null) return "대기";
  const d = new Date(
    typeof value === "number"
      ? value * 1000
      : /[zZ]|[+-]\d\d:\d\d$/.test(value)
        ? value
        : value + "Z",
  );
  return Number.isNaN(d.valueOf())
    ? "대기"
    : new Intl.DateTimeFormat("ko-KR", {
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      }).format(d);
};
const phases: Record<string, string> = {
  starting:'시작 준비',
  polling:'시세 갱신 중',
  loading: "불러오는 중",
  waiting: "입력 대기",
  waiting_batch: "다음 학습 배치 수집",
  waiting_policy: "정책 복원 대기",
  running: "실행 중",
  ready: "준비됨",
  inference: "분석 중",
  training: "학습 중",
  updated: "업데이트 완료",
  stopped: "정지",
  error: "오류",
  needs_input: "입력 필요",
  connection_required: "연결 필요",
  waiting_resources: "자원 대기",
};
export function workerState(worker: Worker | undefined) {
  if (worker?.alive && worker.requested === false)
    return {label: "정지 중", tone: "warn"};
  if (!worker?.alive)
    return worker?.requested
      ? {
          label: worker.error ? "시작 실패" : "시작 준비",
          tone: worker.error ? "bad" : "warn",
        }
      : { label: "정지", tone: "idle" };
  return {
    label: phases[worker.status ?? "running"] ?? "실행 중",
    tone:
      worker.status === "error"
        ? "bad"
        : ['waiting','waiting_batch','waiting_policy','loading','starting','waiting_resources'].includes(worker.status??'')
          ? "warn"
          : "good",
  };
}
export function marketName(value: string) {
  return (
    (
      {
        KRX: "한국 주식",
        KOSDAQ: "코스닥",
        US: "미국 주식",
        NASDAQ: "나스닥",
        NYSE: "뉴욕",
        US_Treasury: "미국 국채",
        HongKong: "홍콩",
        Japan: "일본",
        Germany: "독일",
        UK: "영국",
        FX: "외환",
        BINANCE_USDT: "암호자산",
        CRYPTO: "암호자산",
      } as Record<string, string>
    )[value] ?? value
  );
}
