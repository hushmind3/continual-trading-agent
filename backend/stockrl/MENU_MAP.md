# Platform menu map

Read the relevant small-menu README before implementation files.

- API: web_api.py imports menu_registry.py.
- Coordinator: menu_registry.py imports each large-menu manager; each imports its small-menu metadata and routers.
- trading/: control/, paper_account/
- finrl/: policy_learning/, tools/
- rea/: analysis/, project_browser/
- extensions/: moe/, project_modules/
- management/: connection_settings/, diagnostics/, backend_browser/

Frontend mirrors these folders under frontend/src/pages/. Its coordinator is frontend/src/shell/menu_groups/menu_registry.ts. Shared libraries are documented in backend/stockrl/README.md. Registered/imported/execution-verified states are distinct.

Registration: feature modules → submenu_manager → large-menu registration → menu_registry → single API. New project features are registered through their own managers; the central API and existing finance implementation stay independent of that addition.
