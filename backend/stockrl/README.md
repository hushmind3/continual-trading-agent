# Finance project

금융 대메뉴 하나로 등록합니다: submenu_manager.py → finance_menu_manager.py → ../menu_registry.py → ../web_api.py.

- [trading/](trading/README.md): 운영 제어·가상계좌.
- [finrl/](finrl/README.md): 정책 학습·FinRL 도구.
- [extensions/](extensions/README.md): MoE·모듈.
- [management/](management/README.md): 연결·설정·진단·기능 조회.

이 네 폴더는 금융 내부 분류입니다. REA는 독립 ../rea/에 있으며 금융 대메뉴에 포함하지 않습니다.
platform/과 루트 모델 모듈은 공유 금융 실행 계약입니다. 모델·계좌·가격·설정·공식 라이브러리·알고리즘 기본값은 변경하지 않습니다.
