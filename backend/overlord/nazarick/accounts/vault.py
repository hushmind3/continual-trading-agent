"""macOS Keychain generic-password storage. No secret in argv, files or responses."""
import ctypes as C
import sys


def supported():
    return sys.platform == 'darwin'


def _libraries():
    if not supported():
        raise ValueError('현재 공용 키 저장은 macOS 키체인에서 지원합니다.')
    security = C.CDLL('/System/Library/Frameworks/Security.framework/Security')
    core = C.CDLL('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation')
    security.SecKeychainFindGenericPassword.argtypes = [C.c_void_p, C.c_uint32, C.c_char_p, C.c_uint32, C.c_char_p, C.POINTER(C.c_uint32), C.POINTER(C.c_void_p), C.POINTER(C.c_void_p)]
    security.SecKeychainAddGenericPassword.argtypes = [C.c_void_p, C.c_uint32, C.c_char_p, C.c_uint32, C.c_char_p, C.c_uint32, C.c_char_p, C.c_void_p]
    security.SecKeychainItemModifyAttributesAndData.argtypes = [C.c_void_p, C.c_void_p, C.c_uint32, C.c_char_p]
    security.SecKeychainItemFreeContent.argtypes = [C.c_void_p, C.c_void_p]
    core.CFRelease.argtypes = [C.c_void_p]
    return security, core


def _service():
    from .state import STATE
    return ('project-platform:' + str(STATE.resolve())).encode()


def save(key, secret):
    security, core = _libraries()
    service, account, value = _service(), key.encode(), secret.encode()
    item = C.c_void_p()
    code = security.SecKeychainFindGenericPassword(None, len(service), service, len(account), account, None, None, C.byref(item))
    if code == 0:
        try:
            code = security.SecKeychainItemModifyAttributesAndData(item, None, len(value), value)
        finally:
            core.CFRelease(item)
    elif code == -25300:
        code = security.SecKeychainAddGenericPassword(None, len(service), service, len(account), account, len(value), value, None)
    if code:
        raise ValueError(f'키체인 저장에 실패했습니다 ({code}). macOS 키체인 접근 요청을 확인하세요.')


def read(key):
    security, _ = _libraries()
    service, account = _service(), key.encode()
    length, data = C.c_uint32(), C.c_void_p()
    code = security.SecKeychainFindGenericPassword(None, len(service), service, len(account), account, C.byref(length), C.byref(data), None)
    if code:
        raise ValueError(f'키체인에서 키를 읽지 못했습니다 ({code}).')
    try:
        return C.string_at(data, length.value).decode()
    finally:
        security.SecKeychainItemFreeContent(None, data)
