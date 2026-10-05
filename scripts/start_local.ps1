$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$frontend = Join-Path $root 'frontend'
$vite = Join-Path $frontend 'node_modules\vite\bin\vite.js'
$runtime = Join-Path $root 'runtime\markets\korea'
$pidFile = Join-Path $runtime 'frontend-vite.pid'
$pythonLauncher = Join-Path $root 'start_stockrl.py'

if (-not (Get-Command node.exe -ErrorAction SilentlyContinue)) {
    throw 'Node.js를 찾을 수 없습니다. Node.js LTS를 설치한 뒤 다시 실행하세요.'
}
if (-not (Test-Path -LiteralPath $vite)) {
    throw '프론트엔드 의존성이 없습니다. frontend 폴더에서 npm ci를 한 번 실행하세요.'
}

$pythonEnv = Join-Path $root 'artifacts\experts\venv\Scripts\python.exe'
if (Test-Path -LiteralPath $pythonEnv) {
    & $pythonEnv $pythonLauncher --no-browser
} else {
    $py = Get-Command py.exe -ErrorAction SilentlyContinue
    if (-not $py) { throw 'Python 실행기 py.exe를 찾을 수 없습니다. 설치.cmd를 먼저 실행하세요.' }
    & $py.Source -3 $pythonLauncher --no-browser
}
if ($LASTEXITCODE -ne 0) { throw 'Python API 서버가 시작되지 않았습니다.' }

$node = (Get-Command node.exe).Source
$viteArgs = @($vite, '--host', '127.0.0.1', '--port', '5173', '--strictPort')
$viteProcess = $null
if (Test-Path -LiteralPath $pidFile) {
    $savedId = 0
    [void][int]::TryParse((Get-Content -Raw -LiteralPath $pidFile), [ref]$savedId)
    if ($savedId -gt 0) {
        $candidate = Get-CimInstance Win32_Process -Filter "ProcessId=$savedId" -ErrorAction SilentlyContinue
        if ($candidate -and $candidate.CommandLine -like "*$vite*") { $viteProcess = $candidate }
    }
    if (-not $viteProcess) { Remove-Item -LiteralPath $pidFile -Force }
}

if (-not $viteProcess) {
    $listener = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($listener) {
        $candidate = Get-CimInstance Win32_Process -Filter "ProcessId=$($listener.OwningProcess)" -ErrorAction SilentlyContinue
        if ($candidate -and $candidate.CommandLine -like "*$vite*") {
            $viteProcess = $candidate
        } else {
            throw '5173 포트는 다른 프로그램이 사용 중입니다. 기존 프로그램은 종료하지 않았습니다.'
        }
    } else {
        $viteProcess = Start-Process -FilePath $node -ArgumentList $viteArgs -WorkingDirectory $frontend -WindowStyle Hidden -PassThru
        New-Item -ItemType Directory -Path $runtime -Force | Out-Null
        Set-Content -LiteralPath $pidFile -Value $viteProcess.Id -Encoding ascii
    }
}

$vitePid = if ($viteProcess -is [System.Diagnostics.Process]) { $viteProcess.Id } else { $viteProcess.ProcessId }
New-Item -ItemType Directory -Path $runtime -Force | Out-Null
Set-Content -LiteralPath $pidFile -Value $vitePid -Encoding ascii

$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    if ($viteProcess -is [System.Diagnostics.Process] -and $viteProcess.HasExited) { break }
    try {
        $request = [System.Net.WebRequest]::Create('http://127.0.0.1:5173/')
        $request.Timeout = 2000
        $response = $request.GetResponse()
        if ([int]$response.StatusCode -eq 200) { $ready = $true }
        $response.Close()
        if ($ready) { break }
    } catch { }
    Start-Sleep -Milliseconds 500
}
if (-not $ready) {
    if ($viteProcess -is [System.Diagnostics.Process] -and -not $viteProcess.HasExited) { Stop-Process -Id $viteProcess.Id -Force }
    if (Test-Path -LiteralPath $pidFile) { Remove-Item -LiteralPath $pidFile -Force }
    throw 'Vite dev server did not become ready on port 5173.'
}

Write-Host 'Python API: http://127.0.0.1:8766'
Write-Host 'React 개발 화면: http://127.0.0.1:5173'
Start-Process 'http://127.0.0.1:5173'
