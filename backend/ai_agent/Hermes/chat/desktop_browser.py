"""Platform browser launcher; registered by the native tool discovery adapter."""
import json
import os
from pathlib import Path
import subprocess
_worker=None
def bind(worker):
    global _worker
    _worker=worker

def launch(args,**kwargs):
    worker=_worker
    if worker is None:return json.dumps({'error':'Platform worker is unavailable.'})
    browser=args.get('browser','chrome')
    url=str(args.get('url') or 'about:blank')
    from urllib.parse import urlsplit
    if url!='about:blank' and (urlsplit(url).scheme not in ('http','https') or not urlsplit(url).hostname):
        return json.dumps({'error':'http/https 주소 또는 about:blank만 사용할 수 있습니다.'},ensure_ascii=False)
    paths=[Path(os.environ.get('PROGRAMFILES','C:/Program Files'))/'Google/Chrome/Application/chrome.exe',
           Path(os.environ.get('PROGRAMFILES(X86)','C:/Program Files (x86)'))/'Google/Chrome/Application/chrome.exe',
           Path(os.environ.get('LOCALAPPDATA',''))/'Google/Chrome/Application/chrome.exe'] if browser=='chrome' else [
           Path(os.environ.get('PROGRAMFILES(X86)','C:/Program Files (x86)'))/'Microsoft/Edge/Application/msedge.exe',
           Path(os.environ.get('PROGRAMFILES','C:/Program Files'))/'Microsoft/Edge/Application/msedge.exe']
    executable=next((p for p in paths if p.is_file()),None)
    if not executable:return json.dumps({'error':browser+' 실행파일을 찾지 못했습니다.'},ensure_ascii=False)
    key=(str(executable),url)
    if worker.job.get('_browser_launch')==key:
        return json.dumps({'launch_requested':True,'already_requested':True,'instruction':'Already launched this turn. Do not reopen if the user closed it. Finish.'})
    process=subprocess.Popen([str(executable),'--new-window',url],cwd=executable.parent,
        stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,close_fds=True,
        creationflags=subprocess.DETACHED_PROCESS|subprocess.CREATE_NEW_PROCESS_GROUP)
    worker.job['_browser_launch']=key
    return json.dumps({'launch_requested':True,'pid':process.pid,'executable':str(executable),'url':url,
        'instruction':'Launch requested, not yet visually verified. Use computer_use capture in ax mode once, then finish and leave the window open. Never close or relaunch it for cleanup.'})

SCHEMA={'name': 'desktop_browser', 'description': 'Open a VISIBLE Windows Chrome/Edge window, detached from terminal cleanup. Prefer this over terminal commands when the user asks to open Chrome. Does not navigate the separate headless automation browser. Verify once with computer_use capture mode ax; leave the window open.', 'parameters': {'type': 'object', 'properties': {'browser': {'type': 'string', 'enum': ['chrome', 'edge'], 'default': 'chrome'}, 'url': {'type': 'string', 'description': 'http/https URL or about:blank', 'default': 'about:blank'}}, 'additionalProperties': False}}
