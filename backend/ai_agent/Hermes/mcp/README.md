# MCP

Catalog reads all 65 original optional-mcps manifests through hermes_cli.mcp_catalog. Install calls the original card_install_config and validated _save_mcp_server. Required settings are checked first; secret values use native project-local .env storage. Native Git/bootstrap installation runs only when the user installs an entry declaring it. Saving a remote entry registers its endpoint; it does not imply successful authentication or tool availability.

The frontend has Catalog and My Connections tabs: individual Korean descriptions, original setup/auth notes and source links, installation, local/HTTP setup, enable/disable, edit, JSON import, explicit Connect and removal. Native MCP discovery/status connects servers and registers tools. OAuth providers may require the original login flow or a service token; external OAuth accounts and all 65 remote services have not been tested.

Configuration changes are rejected while an agent or installer is active. Installed catalog search is distinct from public internet MCP search: the catalog contains the curated entries bundled with the pinned original source.
