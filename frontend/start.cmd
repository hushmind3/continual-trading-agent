@echo off
cd /d "%~dp0"
rem Development only. The production frontend is served on 8766.
if not exist node_modules (
  echo Dependencies are missing. Install the locked frontend dependencies separately.
  pause
  exit /b 1
)
call npm run dev
