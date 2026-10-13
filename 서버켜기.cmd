@echo off
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYTHONPATH=%~dp0backend"
"%~dp0.venv\Scripts\python.exe" "%~dp0development\scripts\start_server.py"
if errorlevel 1 pause
