"""Dispose one verified library file through the desktop's normal trash."""
import os


def recycle(path):
    if os.name!='nt':path.unlink();return
    import ctypes
    from ctypes import wintypes
    class Operation(ctypes.Structure):
        _fields_=[('hwnd',wintypes.HWND),('func',wintypes.UINT),('source',wintypes.LPCWSTR),
                  ('target',wintypes.LPCWSTR),('flags',wintypes.WORD),('aborted',wintypes.BOOL),
                  ('mappings',ctypes.c_void_p),('title',wintypes.LPCWSTR)]
    value=Operation(None,3,str(path.resolve())+'\0',None,0x40|0x10|0x04|0x400,False,None,None)
    result=ctypes.windll.shell32.SHFileOperationW(ctypes.byref(value))
    if result or value.aborted:raise OSError('패키지를 휴지통으로 보내지 못했습니다.')
