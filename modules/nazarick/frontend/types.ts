export const categories = [
  {id: 'execution', name: '실행·에이전트', detail: '작업을 수행하는 엔진과 담당 조직'},
  {id: 'data', name: '데이터·저장소', detail: '서비스가 사용할 데이터와 파일'},
  {id: 'identity', name: '계정·권한', detail: '이용자와 접근 권한을 연결할 자리'},
  {id: 'payment', name: '결제·과금', detail: '정해진 결제사와 과금 방식을 연결'},
  {id: 'distribution', name: '유통·마케팅', detail: '외부 판매 채널과 마케팅 조직'},
  {id: 'custom', name: '새로운 확장', detail: '아직 정하지 않은 다음 기능'},
] as const;
export type Category = typeof categories[number]['id'];
export interface Connection {
  id: string; name: string; category: Category; adapter: 'planned' | 'platform_module';
  target: string; notes: string; status: string; checked_at: string | null;
  created_at: string; updated_at: string;
}
export interface Activity {
  id: string; connection_id: string; name: string; action: string; status: string;
  detail: {message: string; scope?: string; menus?: string[]; operations?: string[]}; created_at: string;
}
export interface Adapter {
  id: string; name: string; targets: {id: string; name: string; available: boolean; error: string | null}[];
}
export interface Overview {name: string; schema: number; connections: Connection[]; activity: Activity[]; adapters: Adapter[]}
export type Definition = Pick<Connection, 'name' | 'category' | 'adapter' | 'target' | 'notes'> & {id?: string};
export const stateLabel: Record<string, string> = {
  planned: '연결 예정', unchecked: '확인 전', registered: '등록 확인됨', failed: '확인 실패', saved: '저장됨', removed: '제거됨',
};
export function categoryName(id: string) {return categories.find(item => item.id === id)?.name ?? id}
export function timeLabel(value: string) {
  return new Intl.DateTimeFormat('ko-KR', {month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit'}).format(new Date(value));
}
