"""Shared provider credentials used by collection and connection settings."""
from .. import finrlx

PROVIDER_FIELDS={
    'FMP':['FMP_API_KEY'],
    'WRDS':['WRDS_USERNAME','WRDS_PASSWORD'],
}

def provider_environment():
    from stockrl.management.connection_settings.provider_credentials import _vault
    vault=_vault()
    return {key:value for keys in PROVIDER_FIELDS.values() for key in keys
        if (value:=vault.get_password('stockrl.official-framework',key))}

def provider_status():
    import os
    saved=provider_environment();config=finrlx('config.settings').get_config()
    existing={'FMP':bool(config.fmp.api_key),
              'WRDS':bool(config.wrds.username and config.wrds.password)}
    return {'items':[{'name':name,'fields':keys,'configured':existing[name] or all(saved.get(key) or os.environ.get(key) for key in keys if not key.endswith('BASE_URL')),
        'status':'설정 여부만 확인 · 실제 인증·수신 미확인'} for name,keys in PROVIDER_FIELDS.items()]}

def save_provider(name,values):
    import os
    from stockrl.management.connection_settings.provider_credentials import _vault
    if name not in PROVIDER_FIELDS:raise ValueError('공식 공급원 설정을 선택하세요.')
    vault=_vault()
    for key,value in values.items():
        if key not in PROVIDER_FIELDS[name]:raise ValueError('원본 공급원 환경변수 이름이 아닙니다: '+key)
        if value:vault.set_password('stockrl.official-framework',key,str(value))
    os.environ.update(provider_environment());finrlx('config.settings').reload_config()
    return provider_status()
