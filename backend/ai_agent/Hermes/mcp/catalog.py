"""Original Hermes MCP catalog exposed without its standalone web gateway."""
from dataclasses import asdict
import threading
import time

class Catalog:
    def __init__(self, worker):
        self.worker=worker
        self.job={'state':'idle','name':'','error':''}
        self.thread=None

    def listing(self):
        from hermes_cli import mcp_catalog as native
        servers=self.worker.native_config().get('mcp_servers',{})
        rows=[]
        for entry in native.list_catalog():
            row=asdict(entry);row.pop('manifest_path',None)
            row['installed']=entry.name in servers
            row['enabled']=native.server_enabled(servers.get(entry.name,{})) if row['installed'] else False
            rows.append(row)
        return {'entries':rows,'diagnostics':native.catalog_diagnostics(),'installation':dict(self.job)}

    def install(self, payload):
        self.worker.idle_required()
        from hermes_cli import mcp_catalog as native
        from hermes_cli.config import get_env_value
        entry=native.get_entry(str(payload.get('name') or ''))
        if entry is None:raise ValueError('카탈로그에 없는 서버입니다.')
        env=payload.get('env') or {}
        declared={spec.name for spec in entry.auth.env}
        if not isinstance(env,dict) or set(env)-declared:raise ValueError('이 서버가 요구하는 설정값만 입력하세요.')
        for spec in entry.auth.env:
            if spec.required and not (env.get(spec.name) or spec.default or (spec.secret and get_env_value(spec.name))):
                raise ValueError(spec.prompt or spec.name+' 설정이 필요합니다.')
        self.job={'state':'running','name':entry.name,'error':'','started_at':time.time()}
        def execute():
            try:
                from hermes_cli.config import save_env_value
                for spec in entry.auth.env:
                    value=str(env.get(spec.name) or spec.default or '')
                    if value and spec.secret:save_env_value(spec.name,value)
                # Native connection-card installer: clone/build when declared, preserve
                # curated tool filters, retain OAuth metadata; no terminal prompts.
                cfg=native.card_install_config(entry)
                for spec in entry.auth.env:
                    value=str(env.get(spec.name) or spec.default or '')
                    if value and not spec.secret:cfg=native._inline_non_secret_value(cfg,spec.name,value)
                from hermes_cli.mcp_config import _save_mcp_server
                if not _save_mcp_server(entry.name,cfg):
                    raise ValueError('원본 설정 검사에서 설치 설정을 거부했습니다.')
                self.job.update(state='complete',finished_at=time.time())
            except Exception as exc:
                self.job.update(state='failed',error=str(exc),finished_at=time.time())
        self.thread=threading.Thread(target=execute,daemon=True,name='hermes-mcp-install')
        self.thread.start()
        return dict(self.job)
