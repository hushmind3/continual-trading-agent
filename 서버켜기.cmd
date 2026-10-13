@echo off
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYTHONPATH=%~dp0backend"
if exist "%ProgramFiles%\Git\cmd\git.exe" set "PATH=%ProgramFiles%\Git\cmd;%PATH%"
for /d %%N in ("%LOCALAPPDATA%\Programs\node-v*-win-x64") do if exist "%%N\node.exe" set "PATH=%%N;%PATH%"
"%~dp0.venv\Scripts\python.exe" -X utf8 -B "%~dp0development\scripts\start_server.py" --apply-only --skip-checks
if errorlevel 1 (
    pause
    exit /b 1
)
start "" "http://127.0.0.1:8766/"
