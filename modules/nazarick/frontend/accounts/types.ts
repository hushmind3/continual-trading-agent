export type Progress = 'pending' | 'working' | 'waiting_user' | 'registered' | 'key_ready' | 'failed';
export interface Service {id: string; name: string; url: string; login: string; status: Progress; notes: string; credential_saved: number; updated_at: string}
export interface SharedState {
  browser: {state: string; endpoint: string; profile: string; browser: string};
  services: Service[]; vault: {available: boolean; name: string};
  agents: {configured: boolean; message: string; hermes_profiles?: string[]; codex?: boolean; openclaw?: boolean};
}
export const progress: Record<Progress, string> = {pending: '가입 대기', working: '작업 중', waiting_user: '내 인증 필요', registered: '가입 기록됨', key_ready: '키 발급 기록됨', failed: '실패'};
export const operation = 'overlord/nazarick/accounts/';
