"""Frozen Chronos-2/Bolt via installed official APIs, without remote Python execution."""
import time
import torch
from torch import nn
from ..expert_device import host_state,finish_device


def construct(config,kind):
    import transformers.utils.import_utils as iu
    iu._torchvision_available=False
    if kind=='chronos2':
        from chronos import Chronos2Model
        from chronos.chronos2.config import Chronos2CoreConfig
        return Chronos2Model(Chronos2CoreConfig.from_dict(config))
    if kind=='chronos_bolt':
        from chronos.chronos_bolt import ChronosBoltModelForForecasting
        from transformers import T5Config
        return ChronosBoltModelForForecasting(T5Config.from_dict(config))
    raise ValueError('지원하는 공식 시계열 실행기가 없습니다.')


def definition(config):
    architecture=(config.get('architectures') or [''])[0]
    kind={'Chronos2Model':'chronos2','ChronosBoltModelForForecasting':'chronos_bolt'}.get(architecture)
    if not kind or not config.get('chronos_config'):return None
    if config.get('d_model',512)>4096 or config.get('num_layers',6)>64:raise ValueError('현재 운영 자원의 모델 구성 범위를 초과합니다.')
    with torch.device('meta'):model=construct(config,kind)
    return kind,model


class HfForecastExpert(nn.Module):
    def __init__(self,model,entry):
        super().__init__();self.models=nn.ModuleList([model]);self.entry=entry;self.requires_grad_(False).eval()

    @classmethod
    def restore(cls,package):
        kind=package['entry']['backend'];model=construct(package['metadata']['model_config'],kind)
        state={k.removeprefix('models.0.'):v for k,v in package['state_dict'].items()}
        if package.get('quantization'):
            from .quantized_linear import restore_packed
            restore_packed(model,state,package['quantization'],prefix='models.0')
        else:model.load_state_dict(state,strict=True,assign=True)
        return cls(model,package['entry'])

    def forward(self,root,data,device='cpu'):
        from chronos import Chronos2Pipeline,ChronosBoltPipeline
        model=self.models[0];home=host_state(self)
        started=time.perf_counter()
        try:
            model.to(device)
            # Chronos-2 pins CPU input batches and transfers them to its model device internally.
            input_device='cpu' if self.entry['backend']=='chronos2' else device
            context=torch.as_tensor(data['series'],dtype=torch.float32,device=input_device)
            levels=[i/10 for i in range(1,10)]
            if self.entry['backend']=='chronos2':
                values,_=Chronos2Pipeline(model).predict_quantiles(context.unsqueeze(1),prediction_length=1,quantile_levels=levels)
                forecast=torch.cat(values,dim=0)
            else:forecast,_=ChronosBoltPipeline(model).predict_quantiles(context,prediction_length=1,quantile_levels=levels)
            output=forecast.float().cpu()
            if tuple(output.shape)!=(len(data['symbols']),1,9) or not torch.isfinite(output).all():raise ValueError('공식 예측 출력의 크기 또는 값이 유효하지 않습니다.')
            return dict(expert=self.entry['id'],as_of=data['as_of'],symbols=data['symbols'],native_output=output.tolist(),
                output_shape=list(output.shape),layout='symbol,horizon,quantile',units=data['units'],
                horizon=1,sampling_seconds=data['sampling_seconds'],quantile_levels=levels,frozen=True,
                native_features_verified=True,forward_seconds=time.perf_counter()-started)
        finally:
            finish_device(self,home,device)
