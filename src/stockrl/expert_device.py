"""Retain a frozen model for one bounded GPU job; restore original CPU views at release."""
def host_state(module):
    saved=getattr(module,'_device_home',None)
    if saved is not None:return saved
    return ([(p,p.detach()) for p in module.parameters()],
            [(m,k,v) for m in module.modules() for k,v in m._buffers.items() if v is not None])


def restore_host(module,saved=None):
    saved=saved or getattr(module,'_device_home',None)
    if saved is None:
        if getattr(module,'_gpu_owned',False):module.cpu();module._gpu_owned=False
        return
    parameters,buffers=saved
    for parameter,value in parameters:parameter.data=value
    for child,name,value in buffers:child._buffers[name]=value
    module.__dict__.pop('_device_home',None)


def finish_device(module,saved,device):
    if getattr(module,'_layer_offloaded',False):return
    if getattr(module,'keep_device',False) and device.startswith('cuda'):
        if getattr(module,'retain_host_weights',True):module._device_home=saved
        else:module.__dict__.pop('_device_home',None);module._gpu_owned=True
    else:restore_host(module,saved)
