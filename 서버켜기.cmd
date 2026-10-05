@echo off
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_local.ps1"
if errorlevel 1 (
  echo Startup failed. Read the message above and check Node.js, frontend dependencies, and ports 8766/5173.
  pause
  exit /b 1
)
