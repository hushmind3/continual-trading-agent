# 플랫폼 대메뉴

- [trading](trading/README.md)
- [finrl](finrl/README.md)
- [extensions](extensions/README.md)
- [management](management/README.md)
- [rea](rea/README.md)

shared/는 여러 메뉴에서 재사용하는 화면 부품입니다. 메뉴 취합 파일은 각 대메뉴 폴더에 있고, 전체 총괄은 shell/menu_groups/menu_registry.ts입니다.

Registration: feature modules → submenu_manager → large-menu registration → menu_registry → single API. New project features are registered through their own managers; the central API and existing finance implementation stay independent of that addition.
