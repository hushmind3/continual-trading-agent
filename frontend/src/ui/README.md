# 공통 UI

- AppWorkspace.tsx: 설치된 앱의 공통 제목·액션과 원본 UI 프레임입니다. 중복 페이지 제목을 숨기고 화면 높이를 사용하며 디자인은 tailwind.css의 ui-app-workspace에 둡니다. 프로젝트별 별도 CSS를 만들지 않습니다.

- Panel.tsx: 접이식 패널·키/값 표시.
- 패널 설명은 제목 옆 안내 아이콘으로 분리합니다. 기본 화면은 제목·제어·상태·결과를 표시하며, 설명은 선택했을 때 펼칩니다.
- Primitives.tsx: Button·IconButton·Input·Select·Textarea·상태·탭·Drawer·오류·빈 상태 등 재사용 요소. Button은 기존 기본 동작을 유지하며 아이콘 버튼은 같은 로딩·비활성화·ref 계약을 사용합니다.
- ../tailwind.css: 공통 Tailwind 진입점·테마·대화 폭·서식·에이전트 화면 스타일.
- DataTable.tsx: 검색·정렬·선택·페이지 이동.
- 표의 정렬 가능한 열만 버튼을 제공하고 정렬 방향을 표시합니다. 정렬이 없는 열은 일반 제목으로 읽힙니다. 검색·선택·페이지 이동은 유지합니다.
- SystemControls.tsx: 기존 자동 운영 시작·중지 명령과 실제 실행 단계 표시.
- JobLog.tsx, ServiceProgress.tsx: 실제 작업 로그·단계 표시.
- ../tailwind.css: 전체 메뉴·화면의 색상·타이포그래피·여백·버튼·입력·패널·반응형 디자인을 공통 Tailwind 테마와 유틸리티로 관리합니다. 별도 Workspace.css는 불러오지 않습니다.

공통 컴포넌트를 재사용합니다. 기능 실행 버튼을 여러 화면에 복제하지 않으며 등록·선택·적재·검사·학습 상태를 구분합니다.

ChampionSpec은 선택 알고리즘과 실제 정책·Critic 또는 가치 출력 구조를 표시합니다.

공통 디자인: 밝은 중성 배경·흰 카드·한 가지 파란 실행 강조색을 사용합니다. ui-button/input/status/tabs/drawer 스타일은 기존 컴포넌트의 동작과 분리합니다. 760px 이하에서는 전체 메뉴를 Drawer로 열고, 1100px 이하의 운영 개요는 한 열로 배치합니다. 키보드 본문 이동·포커스 표시·모션 감소 설정을 제공합니다. 운영 명령·API·모델 설정을 변경하지 않습니다.

2026-10-15 탭 키보드 조작: 선택된 탭만 Tab 순서에 포함하고 좌우 방향키로 선택·초점을 순환합니다. Home/End는 첫/마지막 탭을 선택합니다. 탭 버튼은 form 제출을 유발하지 않습니다. 타입 검사·빌드·프론트 반영 완료. 실제 가상계좌 통화·보유/체결·MoE 분류 탭에서 순환·Home/End·Tab으로 묶음 이탈·선택 상태 일치를 확인했습니다. 브라우저 오류 없음. 통화/분류 화면 선택만 변경했으며 모델·학습·매매·설정 저장은 실행하지 않았습니다.

2026-10-16: React·Vite·공통 tailwind.css를 사용하며 버튼·입력·선택 요소는 src/ui/Primitives.tsx를 재사용합니다. 화면의 API·데이터 처리 계약은 유지합니다.

DocumentPreview.tsx는 공통 Drawer·Button·ErrorMessage를 사용해 비동기 로컬 문서를 표시합니다. 파일 로더는 소메뉴가 전달하고, 닫힌 뒤 도착한 응답은 무시합니다. Markdown의 원본 HTML은 실행하지 않습니다. DocumentContent는 HTML을 전체 sandbox와 CSP가 적용된 iframe에서 미리보고, 소스 전환은 원문을 표시합니다. 스크립트·외부 이미지/스타일·폼 전송은 허용하지 않습니다. 다른 텍스트 형식은 원문으로 표시합니다.

Hermes 대화는 DocumentWorkspace·DocumentPanel을 사용해 문서를 대화 옆에 표시합니다. 문서를 보면서 입력할 수 있고 문서/소스를 전환합니다. 다른 화면의 DocumentPreview는 기존 Drawer 동작을 유지합니다.

문서 패널은 읽기 성공 후에만 열립니다. 실패는 링크 옆에 표시하고 기존 문서·대화 폭을 유지합니다. 축소·확대·닫기, 경계 드래그·방향키 너비 조절을 제공하며 디자인은 공통 Tailwind에서 관리합니다.

ComposerFrame은 전체 폭 편집 영역·첨부·도구 모음·실행 옵션을 배치하는 공통 입력 폼입니다. FileChips는 파일 이름·크기·첨부 취소를 표시합니다. 디자인은 tailwind.css의 ui-composer·ui-file 클래스에 있습니다.

SettingsSection은 설정 제목·설명·상태/액션·본문 경계를 공유합니다. SettingsLoadState는 설정 읽기 실패 시 원인과 다시 불러오기를 함께 표시합니다. ui-settings 계열 디자인은 tailwind.css에서 관리합니다.

문서 참조는 ui-document-link 텍스트 링크로 표시해 본문을 버튼 모양으로 쪼개지 않습니다. Tabs는 선택된 항목만 강조하고 설정 화면에서 내용 폭만 사용합니다. 스킬·MCP 입력창도 별도 모달 구현 대신 공통 Drawer를 사용합니다.

DocumentContent.tsx는 팝업과 나란히 보기에서 공통으로 사용하는 문서 본문입니다. HTML 미리보기와 원문 보기는 분리되며 기존 문서 읽기 API를 그대로 사용합니다.

ToggleSwitch는 공통 버튼을 사용하는 키보드 접근 가능한 on/off 스위치입니다. role=switch·aria-checked를 제공하고 공통 tailwind.css로 표시합니다.

documentPaths는 로컬 문서 경로와 문서 기준 상대 링크를 해석합니다. 열린 Markdown 안의 로컬 링크도 같은 문서 패널에서 읽으며 외부 URL은 외부 링크로 유지합니다.

PanelResizeHandle은 공통 사이드 패널 크기 조절 컴포넌트입니다. 드래그·방향키·Home/End·더블클릭 초기화와 폭 기억을 제공하며 범위·이동 간격은 tailwind.css의 공통 토큰을 따릅니다. 문서·작업 내역에서 공유합니다.

AppExecution.tsx는 설치 앱 화면과 Hermes 상단 탭에서 재사용하는 앱 소유 작업 내역·질문·권한 응답·중지 제어입니다. 기존 projects/harness의 세션 소유권 검사를 사용하며 다른 사용자 작업은 제어하지 않습니다.
