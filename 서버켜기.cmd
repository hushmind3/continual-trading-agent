@echo off
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYTHONPATH=%~dp0src"
"%~dp0.venv\Scripts\python.exe" "%~dp0scripts\start_server.py"
if errorlevel 1 pause
