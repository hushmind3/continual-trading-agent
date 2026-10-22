/** Korean display copy for upstream MCP catalog instructions. Never used as configuration. */
const oauthNames: Record<string, string> = {
  airtable: 'Airtable', algolia: 'Algolia', amplitude: 'Amplitude', asana: 'Asana', atlassian: 'Atlassian',
  attio: 'Attio', betterstack: 'Better Stack', buildkite: 'Buildkite', calendly: 'Calendly', canva: 'Canva',
  circleci: 'CircleCI', clickup: 'ClickUp', close: 'Close', cloudinary: 'Cloudinary', 'comfy-cloud': 'Comfy Cloud',
  datadog: 'Datadog', dropbox: 'Dropbox', figma: 'Figma', fireflies: 'Fireflies', gamma: 'Gamma',
  gitlab: 'GitLab', globalping: 'Globalping', grafana: 'Grafana', hugging_face: 'Hugging Face',
  indeed: 'Indeed', intercom: 'Intercom', klaviyo: 'Klaviyo', linear: 'Linear', miro: 'Miro',
  mixpanel: 'Mixpanel', monday: 'Monday.com', motherduck: 'MotherDuck', 'n8n-official': 'n8n', neon: 'Neon',
  netlify: 'Netlify', notion: 'Notion', paypal: 'PayPal', plaid: 'Plaid', postman: 'Postman',
  'prisma-postgres': 'Prisma Postgres', railway: 'Railway', robinhood: 'Robinhood', sentry: 'Sentry',
  square: 'Square', strava: 'Strava', stripe: 'Stripe', supabase: 'Supabase', todoist: 'Todoist',
  'twelve-data': 'Twelve Data', vercel: 'Vercel', webflow: 'Webflow', 'wordpress-com': 'WordPress.com', semgrep: 'Semgrep',
};

const unauthenticated = new Set(['alltrails', 'aws-knowledge', 'deepwiki', 'kiwi', 'microsoft-learn', 'trivago', 'twilio-docs', 'wolfram']);

const descriptions: Record<string, string> = {
  alltrails: '계정이나 인증 정보 없이 사용할 수 있습니다. 세션을 다시 시작하면 도구를 불러옵니다. 제공 도구는 5개지만 설명이 매우 길어 문맥을 많이 차지합니다(약 2만 4천 토큰). 가끔만 이용한다면 평소에는 연결을 꺼 두고 필요할 때 켜거나 `hermes mcp configure alltrails`에서 도구를 줄이세요.',
  amplitude: '유럽 리전에 있는 조직은 `~/.hermes/config.yaml`의 `mcp_servers.amplitude.url`을 `https://mcp.eu.amplitude.com/mcp`로 바꾸세요.',
  asana: 'Asana의 MCP 앱은 자동 등록을 지원하지 않습니다. 개발자 콘솔(https://app.asana.com/0/my-apps)에서 MCP 앱을 만들고 리디렉션 주소 `http://localhost:27890/callback`을 등록하세요. 사용할 워크스페이스에 앱 배포도 허용해야 합니다.\n\n앱의 클라이언트 ID와 보안 키를 입력하세요. 보안 키는 `.env`에, ID는 `~/.hermes/config.yaml`에 저장됩니다.\n\n`hermes mcp login asana` 또는 대시보드의 인증 버튼으로 로그인하세요. 인증을 시작한 브라우저와 Hermes는 같은 기기에서 실행되어야 합니다. 완료 후 세션을 다시 시작하거나 `/reload-mcp`를 실행하세요.',
  betterstack: '로그인 후 세션을 다시 시작하면 도구를 불러옵니다.\n\n기본 설정은 문서 검색·안내용 도구·직접 SQL 실행·클라우드 자격 증명 발급·팀원 관리 도구를 제외합니다. `hermes mcp configure betterstack`으로 사용 범위를 조정할 수 있습니다.',
  cloudflare: '브라우저에서 Cloudflare 계정에 로그인하고, 에이전트에 허용할 권한 범위만 선택하세요. 승인이 끝나면 세션을 다시 시작합니다.\n\nAPI 기능이 각각 별도 도구로 제공됩니다. 기본 설정은 기업 계약·조직 전체 관리·읽기 전용 분석 등 약 1,400개 도구를 제외하고, DNS·Workers·R2·KV·D1·Queues·Pages·WAF·규칙·터널·Access·Stream·Images·AI·Vectorize 등 약 1,900개를 남깁니다. 도구 설명은 필요할 때 검색해 불러오므로 대화 문맥을 한꺼번에 차지하지 않습니다. Zero Trust·Radar·Magic·API Shield 기능을 포함하려면 `~/.hermes/config.yaml`의 `mcp_servers.cloudflare.tools.exclude`에서 해당 제외 규칙을 지우세요.\n\n브라우저를 쓸 수 없는 환경에서는 https://dash.cloudflare.com/profile/api-tokens 에서 API 토큰을 만든 뒤 `~/.hermes/config.yaml`에 `CLOUDFLARE_API_TOKEN` Bearer 헤더를 설정할 수 있습니다.\n\n기본 서버 주소에는 `?codemode=false`가 붙습니다. 이를 제거하면 JavaScript 샌드박스에서 API를 조합하는 검색·실행 도구 두 개(Code Mode)를 사용합니다. Hermes 도구 검색과 함께 쓰면 검색 단계가 겹쳐 권장하지 않습니다. 특정 기능만 연결하려면 `hermes mcp add <이름> --url <주소>` 명령을 사용하세요.\n\n전용 주소: 문서 검색 `https://docs.mcp.cloudflare.com/mcp`(인증 불필요), Workers 관측 `https://observability.mcp.cloudflare.com/mcp`, 브라우저 렌더링 `https://browser.mcp.cloudflare.com/mcp`, Radar `https://radar.mcp.cloudflare.com/mcp`, GraphQL 분석 `https://graphql.mcp.cloudflare.com/mcp`, 감사 로그 `https://auditlogs.mcp.cloudflare.com/mcp`. 도구 선택은 `hermes mcp configure cloudflare`에서 다시 확인할 수 있습니다.',
  'comfy-cloud': '브라우저에서 Comfy 계정으로 인증하고 세션을 다시 시작하세요. 템플릿·모델·노드 검색은 계정으로 사용할 수 있습니다.\n\n이미지·영상·음성·3D 생성은 Comfy Cloud에서 처리되며 구독이나 크레딧 잔액이 필요합니다(요금제: https://www.comfy.org/cloud). 검색·생성·작업 상태·결제 관련 20개 도구를 기본으로 켭니다. 일괄 작업, 저장·공유 워크플로 관리, App Mode 도구는 꺼져 있으며 `hermes mcp configure comfy-cloud`에서 켤 수 있습니다.',
  context7: '문서 검색은 인증 없이 쓸 수 있지만 요청량 제한이 있습니다.\n\n더 높은 한도가 필요하면 context7.com/dashboard에서 API 키를 만든 뒤 `~/.hermes/config.yaml`의 `mcp_servers.context7.headers`에 Bearer 인증으로 설정하세요.',
  figma: '브라우저에서 로그인하고 권한을 승인한 뒤 세션을 다시 시작하세요. Hermes는 Figma에 `Claude Code`라는 이름으로 앱을 등록해 연결하므로 클라이언트 ID를 따로 입력할 필요가 없습니다.\n\n디자인 구현을 요청할 때는 Figma 파일 링크를 함께 보내세요(예: `implement this design: https://www.figma.com/design/<fileKey>/...`). 로컬 데스크톱 앱에만 연결하려면 Figma 앱에서 Dev Mode를 열고(Shift+D) 검사 패널에서 데스크톱 MCP 서버를 켠 뒤 주소 `http://127.0.0.1:3845/mcp`를 설정하세요. 이 방식은 OAuth 로그인이 필요하지 않습니다.',
  gitlab: 'GitLab.com은 브라우저 로그인으로 연결합니다. 자체 호스팅 GitLab은 18.6 이상에서 MCP를 지원해야 합니다. `~/.hermes/config.yaml`의 `mcp_servers.gitlab.url`을 `https://<호스트>/api/v4/mcp`로 지정하세요.',
  grafana: '`hermes mcp login grafana`를 실행해 Grafana 스택 주소를 입력하고 읽기 전용 또는 읽기·쓰기 권한을 선택하세요.\n\nGrafana Cloud 호스팅 스택과 `Assistant Cloud MCP User` 역할이 필요합니다(기본 Editor 이상 역할에 포함). 자체 호스팅 Grafana는 이 주소에서 지원하지 않으므로 OSS용 `mcp-grafana` 서버를 사용하세요. 요금제에 따라 MCP 연결 사용자마다 Grafana Assistant 사용 요금이 발생할 수 있습니다.',
  kiwi: '인증 없이 항공편을 검색할 수 있습니다. 예약은 대화 안에서 진행하지 않으며 Kiwi.com의 결과 링크로 이동합니다.',
  klaviyo: 'Klaviyo의 Owner·Admin·Manager 역할 계정으로 브라우저 로그인을 마친 뒤 세션을 다시 시작하세요.\n\n기본 구성은 URL 매개변수 기반의 프롬프트 삽입 방어를 유지하면서 핵심 도구 약 40개만 제공합니다. 전체 262개 도구가 필요하면 `~/.hermes/config.yaml`의 `mcp_servers.klaviyo.url`에서 기본 쿼리 매개변수를 제거하세요.',
  linear: '브라우저 로그인으로 권한을 승인한 뒤 세션을 다시 시작하세요. 연결할 도구는 `hermes mcp configure linear`에서 선택할 수 있습니다.',
  'n8n-official': 'n8n 설정에서 인스턴스 수준 MCP를 켜세요(소유자 또는 관리자 권한 필요). Connect에서 복사한 전체 서버 주소를 입력해야 합니다. 주소는 `/mcp-server/http`로 끝나야 하며 편집기 주소는 사용할 수 없습니다.\n\n`hermes mcp login n8n-official` 또는 대시보드 인증 버튼으로 연결하세요. API 키는 필요하지 않습니다. OAuth 콜백 주소를 제한한 인스턴스는 Hermes 콜백 주소를 허용 목록에 추가해야 할 수 있습니다.\n\nn8n 계정 권한과 MCP 설정이 접근 범위를 결정합니다. 검색 결과에는 볼 권한이 있는 워크플로의 미리보기가 표시될 수 있습니다. 전체 내용을 확인하거나 실행·수정하려면 워크플로에서 Available in MCP를 켜세요. 도구는 n8n 버전과 권한에 따라 다르고 일부는 워크플로를 실행하거나 변경합니다. `hermes mcp configure n8n-official`에서 도구를 확인하세요.\n\n기존 n8n 브리지 연결은 그대로 유지되며 자동으로 옮겨지지 않습니다. 설정 후 새 세션을 시작하거나 `/reload-mcp`를 실행하세요.',
  robinhood: '계정 연결 후 포트폴리오·잔고 조회와 주식·옵션·가상자산 주문 기능을 사용할 수 있습니다.\n\n전용 Robinhood 에이전트 계정에서 실제 거래를 실행할 수 있습니다. Hermes의 일반 도구 승인 절차가 적용되지만, 승인 전에 주문 내용을 직접 꼼꼼히 확인하세요.',
  strava: '브라우저에서 계정을 연결하고 권한을 승인한 뒤 세션을 다시 시작하세요. 일부 기능은 Strava 구독이 필요합니다.',
  trivago: '인증 없이 숙박 시설을 검색하고 가격을 비교할 수 있습니다. 예약은 대화 안에서 진행하지 않으며 예약 사이트로 이동합니다.',
  'unreal-engine': 'Unreal Engine 5.8 이상 프로젝트를 에디터에서 여세요. Edit > Plugins에서 Unreal MCP 플러그인을 찾아 켠 뒤 에디터를 다시 시작합니다(Toolset Registry 의존 기능은 자동으로 켜집니다).\n\nEdit > Editor Preferences > General > Model Context Protocol에서 Auto Start Server를 켜거나, 에디터 콘솔에서 `ModelContextProtocol.StartServer`를 실행하세요. 기본 주소는 `http://127.0.0.1:8000/mcp`입니다. 에디터 MCP 서버가 실행된 다음 Hermes를 시작하세요. 주소나 포트가 다르면 Hermes 연결 설정도 같은 값으로 맞추세요.\n\nEpic의 이 기능은 실험 단계입니다. 도구는 에디터 게임 스레드에서 하나씩 처리되므로 동시에 여러 호출을 보내지 마세요. `hermes mcp configure unreal-engine`에서 도구 구성을 확인할 수 있습니다.',
};

export function localizedPostInstall(name: string, original: string): string {
  if (descriptions[name]) return descriptions[name];
  if (!original) return '설치한 연결은 내 연결 탭에서 관리할 수 있습니다.';
  if (unauthenticated.has(name) || /No account or credentials needed/i.test(original)) {
    return '계정이나 인증 정보 없이 사용할 수 있습니다. 설치한 뒤 세션을 다시 시작하면 도구를 불러옵니다.';
  }
  const service = oauthNames[name];
  if (service && /first connection|opens a browser|authorize with/i.test(original)) {
    return `처음 연결할 때 ${service} 인증을 위해 브라우저가 열립니다. 브라우저에서 접근을 승인한 뒤 세션을 다시 시작하면 도구를 불러옵니다. 터미널에서는 \`hermes mcp login ${name}\`을 실행해도 됩니다.`;
  }
  if (/No account or credentials needed/i.test(original)) return '계정이나 인증 정보 없이 사용할 수 있습니다. 세션을 다시 시작하면 도구를 불러옵니다.';
  return original;
}

export function localizedPrompt(name: string, prompt: string): string {
  const exact: Record<string, string> = {
    'ASANA_CLIENT_ID': 'Asana 개발자 콘솔에서 만든 MCP 앱의 클라이언트 ID를 입력하세요.',
    'ASANA_CLIENT_SECRET': 'Asana 개발자 콘솔에서 만든 MCP 앱의 보안 키를 입력하세요.',
  };
  if (exact[name]) return exact[name];
  if (/^MCP Server URL$/i.test(name) || /MCP Server URL/i.test(prompt)) return 'n8n 설정의 인스턴스 수준 MCP에서 복사한 서버 주소를 입력하세요. 주소는 /mcp-server/http로 끝나야 합니다.';
  return prompt;
}
