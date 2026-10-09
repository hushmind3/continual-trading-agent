"""Register the existing native architectures without copying their forward code.

The existing backend function is specialized in memory: checkpoint reads become
state reads when packaging, constructors become registered modules on reuse.
No original source/checkpoint is changed and no expert probe is repeated.
"""
import ast
import inspect
import json
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace
import torch
from torch import nn
from . import expert_backends
from .expert_device import host_state,finish_device


class NativeExpert(nn.Module):
    def __init__(self, models, entry, runner_source=None):
        super().__init__()
        self.models = nn.ModuleList(models)
        self.entry = entry
        self.runner_source=runner_source
        self.requires_grad_(False).eval()

    def forward_tensors(self,*args,module_index=0,**kwargs):
        """Differentiable native entrypoint for a selected expert parameter group.

        Diagnostic JSON evidence detaches outputs. Native fine tuning instead
        calls this registered module with that architecture's native tensors.
        """
        return self.models[module_index](*args,**kwargs)

    def forward(self, root, data, device="cpu"):
        # Frozen CPU tensors are views into the single mmap PT. Retain those
        # views rather than copying every expert GPU -> newly allocated RAM.
        frozen=all(not p.requires_grad for p in self.parameters())
        home=host_state(self) if frozen else None
        try:
            return native_call(self.entry["backend"], root, data, device,
                               modules=list(self.models),runner_source=self.runner_source)
        finally:
            if frozen:
                finish_device(self,home,device)
            else:self.cpu()


@lru_cache(maxsize=8)
def _compiled_runner(runner):
    """Cache code only; model instances and per-call bindings stay outside."""
    source = runner if isinstance(runner, str) else inspect.getsource(runner)
    tree = ast.parse(source)
    constructors = {"EXAONEFinance", "PatchedTimeSeriesDecoder", "PatchedTimeSeriesDecoder_MOE",
                    "TimeMoeForPrediction", "Toto2Model"}

    class Reuse(ast.NodeTransformer):
        def visit_Dict(self,node):
            node=self.generic_visit(node)
            for index,key in enumerate(node.keys):
                if isinstance(key,ast.Constant) and key.value=='native_output':
                    value=node.values[index]
                    if isinstance(value,ast.Call) and isinstance(value.func,ast.Attribute) and value.func.attr=='tolist':
                        node.values[index]=ast.Call(ast.Name('_packet_output',ast.Load()),[value.func.value],[])
            return node

        def visit_Call(self,node):
            node=self.generic_visit(node)
            name=node.func.id if isinstance(node.func,ast.Name) else node.func.attr if isinstance(node.func,ast.Attribute) else ""
            if name=='numpy' and isinstance(node.func,ast.Attribute) and isinstance(node.func.value,ast.Call) and isinstance(node.func.value.func,ast.Attribute) and node.func.value.func.attr=='cpu':
                return ast.Call(ast.Name('_native_array',ast.Load()),[node.func.value.func.value],[])
            if name in ('asarray','isfinite') and isinstance(node.func,ast.Attribute) and isinstance(node.func.value,ast.Name) and node.func.value.id=='np' and len(node.args)==1:
                arg=node.args[0]
                if isinstance(arg,ast.Name) and arg.id=='output' or isinstance(arg,ast.Call) and isinstance(arg.func,ast.Name) and arg.func.id=='infer':
                    return ast.Call(ast.Name('_finite_output' if name=='isfinite' else '_native_array',ast.Load()),node.args,[])
            if name in ('manual_seed','seed'):
                return ast.Call(ast.Name('_runner_seed',ast.Load()),[node.func,*node.args],node.keywords)
            if name=="load_native_pretrained":
                return ast.Call(ast.Name("_pretrained",ast.Load()),node.args,node.keywords)
            if name in constructors:
                return ast.Call(ast.Name("_construct",ast.Load()),[ast.Lambda(ast.arguments(posonlyargs=[],args=[],kwonlyargs=[],kw_defaults=[],defaults=[]),node)],[])
            if name=="from_pretrained" and isinstance(node.func,ast.Attribute) and isinstance(node.func.value,ast.Name) and node.func.value.id in {"ChronosPipeline","Kronos","KronosTokenizer"}:
                return ast.Call(ast.Name("_pretrained",ast.Load()),[node.func.value,*node.args],node.keywords)
            if name=="load_state_dict":
                return ast.Call(ast.Name("_restore",ast.Load()),[node.func.value,*node.args],node.keywords)
            if name=="load_file" or name=="load" and isinstance(node.func,ast.Attribute) and isinstance(node.func.value,ast.Name) and node.func.value.id=="torch":
                return ast.Call(ast.Name("_weights",ast.Load()),[ast.Constant(name),*node.args],node.keywords)
            if name=='to' and isinstance(node.func,ast.Attribute):
                return ast.Call(ast.Name('_move',ast.Load()),[node.func.value,*node.args],node.keywords)
            return node

        def visit_BinOp(self,node):
            node=self.generic_visit(node)
            if isinstance(node.op,(ast.Mult,ast.Add)) and isinstance(node.right,ast.Name) and node.right.id in ('scale','mean'):
                node.right=ast.Call(ast.Name('_native_operand',ast.Load()),[node.right],[])
            return node

    tree=Reuse().visit(tree)
    function=tree.body[0]
    for index,node in enumerate(function.body):
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=="loaded_seconds" for t in node.targets):
            function.body.insert(index,ast.If(ast.Name("_load_only",ast.Load()),[ast.Return(ast.Name("models",ast.Load()))],[]))
            break
    ast.fix_missing_locations(tree)
    return compile(tree, "<registered baseline native backend>", "exec")


def native_call(backend, root, data, device="cpu", *, modules=None, states=None,
                load_only=False, runner_source=None, quantization=None):
    """Use exactly the baseline native data preparation and native forward."""
    code = _compiled_runner(runner_source or expert_backends.run_native)
    namespace=dict(vars(expert_backends))
    cursor=0
    restored=0

    def construct(factory):
        nonlocal cursor
        model=modules[cursor] if modules is not None else factory()
        cursor+=1
        return model

    def pretrained(cls,directory,**kwargs):
        nonlocal cursor
        if modules is None and states is None:
            result=expert_backends.load_native_pretrained(cls,directory,**kwargs)
            cursor+=1
            return result
        cfg=json.loads((Path(directory)/"config.json").read_text(encoding="utf-8"))
        if cls.__name__=="ChronosPipeline":
            from chronos import ChronosConfig, ChronosModel
            from transformers import AutoConfig, AutoModelForSeq2SeqLM
            if modules is None:
                model=AutoModelForSeq2SeqLM.from_config(AutoConfig.from_pretrained(directory,local_files_only=True))
                restore(model,states[0],strict=True)
            else: model=modules[cursor]
            cc=ChronosConfig(**cfg["chronos_config"])
            result=cls(cc.create_tokenizer(),ChronosModel(cc,model))
        else:
            result=modules[cursor] if modules is not None else cls(**cfg)
            if modules is None: restore(result,states[cursor],strict=True)
        cursor+=1
        return result

    def weights(kind,path,**kwargs):
        if modules is not None or states is not None:
            return states[0] if states else {}
        if kind=="load": return torch.load(path,**kwargs)
        from safetensors.torch import load_file
        return load_file(path,**kwargs)

    def restore(model,state,**kwargs):
        nonlocal restored
        if modules is not None: return SimpleNamespace(missing_keys=[],unexpected_keys=[])
        if states is not None:
            state=states[restored]
            kwargs["assign"]=True
        index=restored;restored+=1
        if quantization:
            from .platform.quantized_linear import restore_packed
            result=restore_packed(model,state,quantization,prefix=f'models.{index}')
        else:result=model.load_state_dict(state,**kwargs)
        if hasattr(model,"tie_weights"): model.tie_weights()
        return result

    def move(value,*args,**kwargs):
        return value if isinstance(value,nn.Module) and (hasattr(value,'_hf_hook') or any(hasattr(m,'_hf_hook') for m in value.modules())) else value.to(*args,**kwargs)
    tensor_output=isinstance(data,dict) and data.get('_tensor_output',False)
    def native_array(value):
        if torch.is_tensor(value):return value.detach() if tensor_output else value.detach().cpu().numpy()
        import numpy as np
        return torch.as_tensor(value,device=device) if tensor_output else np.asarray(value)
    def native_operand(value):return torch.as_tensor(value,device=device) if tensor_output else value
    def finite(value):
        import numpy as np
        return torch.isfinite(value) if torch.is_tensor(value) else np.isfinite(value)
    namespace.update(_construct=construct,_pretrained=pretrained,_weights=weights,_restore=restore,_load_only=load_only,_move=move,
        _native_array=native_array,_native_operand=native_operand,_finite_output=finite,
        _packet_output=lambda value:value.detach() if tensor_output and torch.is_tensor(value) else value.tolist(),
        _runner_seed=lambda fn,*args,**kwargs:None if tensor_output else fn(*args,**kwargs))
    exec(code,namespace)
    # Baseline backend reseeds isolated workers; do not overwrite policy RNG here.
    with torch.random.fork_rng(devices=[]):
        return namespace["run_native"](backend,Path(root),data,device)
