"""Point-in-time normalization on the resident Champion device, without JSON/SQLite."""
import pandas as pd
import torch


def prepare_tensor_evidence(packets,symbols,spec,as_of,ttl,device):
    config=spec['config'];ids=spec['expert_ids']
    tokens={key:torch.zeros((len(symbols),size),device=device) for key,size in config['feature_sizes'].items()}
    mask=torch.zeros((len(symbols),len(ids)),dtype=torch.bool,device=device)
    policy_q={key:torch.zeros((len(symbols),4),device=device) for key in config.get('stock_policy_ids',[])}
    symbol_index={s:n for n,s in enumerate(symbols)};expert_index={k:n for n,k in enumerate(ids)}
    now=pd.Timestamp(as_of)
    for key,batches in packets.items():
        if key not in expert_index:continue
        for packet in batches if isinstance(batches,list) else [batches]:
            age=(now-pd.Timestamp(packet['as_of'])).total_seconds()
            limit=4*86400 if packet.get('sampling_seconds')==86400 else ttl
            if age<0 or age>limit:continue
            native=torch.as_tensor(packet['native_output'],dtype=torch.float32,device=device)
            if packet['layout']=='nine_quantiles,batch,variate,horizon':native=native[:,0].permute(1,0,2)
            native=native.reshape(len(packet['symbols']),-1)
            scale=native.double().square().mean(-1).sqrt().float().clamp_min(1e-6)
            horizon=torch.tensor(float(packet.get('horizon',1)),device=device).log1p()
            seconds=torch.tensor(float(packet.get('sampling_seconds') or 0),device=device).log1p()
            vector=torch.cat([native/scale[:,None],scale.log1p()[:,None],horizon.expand(len(native),1),seconds.expand(len(native),1)],-1)
            if vector.shape[-1]!=tokens[key].shape[-1]:raise ValueError(f'{key}: Champion 원본 입력 크기와 출력이 다릅니다.')
            valid=torch.isfinite(native).all(-1)
            for row,symbol in enumerate(packet['symbols']):
                n=symbol_index.get(symbol)
                if n is None:continue
                symbol_age=(now-pd.Timestamp(packet.get('symbol_as_of',{}).get(symbol,packet['as_of']))).total_seconds()
                if symbol_age<0 or symbol_age>limit:continue
                tokens[key][n]=torch.where(valid[row],vector[row],torch.zeros_like(vector[row]))
                if key in policy_q:
                    item=packet['common_output'][row]
                    policy_q[key][n]=torch.tensor([float(item[k]) for k in ('sell_score','hold_score','buy_score','target_weight')],device=device)
                mask[n,expert_index[key]]=valid[row]
    return tokens,mask,policy_q
