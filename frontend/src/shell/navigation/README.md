# 메뉴 탐색

용도: NavigationTree는 대메뉴(group) → 중메뉴(section, 선택) → 소메뉴(MenuItem)를 표시합니다. MenuLink는 공통 링크·현재 위치·축소 메뉴를 담당합니다. section 없는 금융·REA는 기존 2단계를 유지합니다. 데스크톱과 모바일이 같은 등록 정보를 사용합니다. 새 에이전트는 자체 section과 mountKey를 등록합니다.

MenuItem.sidebar=false는 주소 등록을 유지하면서 좌측 탐색에서만 숨깁니다. 기본값은 표시이므로 다른 메뉴는 유지합니다. mountKey와 같은 주 진입점은 하위 주소에서도 선택 상태를 표시합니다. Hermes 설정은 이 방식으로 기존 주소를 유지하고 설정 화면 상단 탭에서 전환합니다.
