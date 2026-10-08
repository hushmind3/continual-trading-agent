@echo off
setlocal
set "PROJECT_ROOT=%~dp0"
set "PID_FILE=%~dp0runtime\finrlx\frontend-vite.pid"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$f=$env:PID_FILE; if (-not (Test-Path -LiteralPath $f)) { Write-Host '관리 중인 Vite 서버가 없습니다.'; exit 0 }; $id=[int](Get-Content -Raw -LiteralPath $f); $p=Get-CimInstance Win32_Process -Filter ('ProcessId='+$id); $root=[IO.Path]::GetFullPath((Join-Path $env:PROJECT_ROOT 'frontend\node_modules')); $cmd=if($p){$p.CommandLine.Replace('/','\')}else{''}; if ($p -and $cmd -like ('*'+$root+'*') -and $cmd -like '*vite\bin\vite.js*') { Stop-Process -Id $id -Force; Remove-Item -LiteralPath $f -Force; Write-Host 'Vite 개발 서버를 종료했습니다. Python 서버는 계속 실행 중입니다.' } else { Remove-Item -LiteralPath $f -Force; Write-Host 'Vite PID 파일이 만료되어 정리했습니다.' }"
pause
