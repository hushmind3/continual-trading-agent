@echo off
cd /d "%~dp0"
rem Development only. The production frontend is served on 8766.
if not exist "..\node_modules\vite\bin\vite.js" (
  echo Dependencies are missing. Run npm ci from the project root.
  pause
  exit /b 1
)
call npm run dev
