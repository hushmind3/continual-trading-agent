# StockRL finance project

Finance implementation stays in this package. Its project folders are trading/, finrl/, extensions/ and management/. Read each small-menu README first.

The platform entry and overall menu coordinator are ../web_api.py and ../menu_registry.py. REA is the independent sibling ../rea/; its implementation is outside this finance package.

platform/ and root expert_*/moe_* modules are shared financial execution/model contracts. Existing policy class import names are retained. Models, settings, accounts and market data are not moved.
