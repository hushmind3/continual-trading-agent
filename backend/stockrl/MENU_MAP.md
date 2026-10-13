# Finance menu map

대메뉴: 금융 하나. 취합은 submenu_manager.py, 대메뉴 등록은 finance_menu_manager.py입니다.

- trading/: operation_control/, virtual_account_orders/
- finrl/: policy_learning/, modules_tools/
- extensions/: moe/
- management/: connection_settings/, diagnostics_logs_code_apply/, all_backend_features/

위 폴더는 금융 내부 분류입니다. 전체 총괄 ../menu_registry.py에는 금융과 독립 REA만 등록합니다. API는 ../web_api.py입니다.
