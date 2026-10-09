@echo off
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYTHONPATH=%~dp0src"
"%~dp0.venv\Scripts\python.exe" -m streamlit run "%~dp0ui.py" --server.address 127.0.0.1 --server.port 8766 --browser.gatherUsageStats false --server.fileWatcherType none
if errorlevel 1 pause
