$ErrorActionPreference = 'Stop'
$receiverProject = Split-Path -Parent $PSScriptRoot
$receiverScript = Join-Path $PSScriptRoot 'codex_fix_receiver.py'
$receiverData = Join-Path $receiverProject 'runtime\codex-fix-receiver'
$receiverTaskName = 'CodexFix-continual-trading-agent'
$receiverPython = (Get-Command python.exe -ErrorAction Stop).Source
$receiverPythonWindowless = Join-Path (Split-Path -Parent $receiverPython) 'pythonw.exe'
if (-not (Test-Path -LiteralPath $receiverPythonWindowless)) { throw '현재 Python의 pythonw.exe가 필요합니다.' }
$receiverCodex = (Get-Command codex.exe -ErrorAction Stop).Source
$receiverConfigFile = Join-Path $receiverData 'config.json'
[IO.Directory]::CreateDirectory($receiverData) | Out-Null
if (-not (Test-Path -LiteralPath $receiverConfigFile)) {
    $receiverConfig = @{
        codex_binary = $receiverCodex
        checkout_root = (Join-Path $env:USERPROFILE '.codex\issue-fixes\continual-trading-agent')
        exec_timeout_seconds = 3600
    } | ConvertTo-Json
    [IO.File]::WriteAllText($receiverConfigFile,$receiverConfig,[Text.UTF8Encoding]::new($false))
}
$receiverExisting = Get-ScheduledTask -TaskName $receiverTaskName -ErrorAction SilentlyContinue
if ($receiverExisting -and -not ($receiverExisting.Actions.Arguments -like '*codex_fix_receiver.py*')) { throw '같은 이름의 다른 작업이 있습니다. 덮어쓰지 않습니다.' }
$receiverSid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$receiverStart = (Get-Date).AddMinutes(1).ToString('s')
$receiverCommand = [Security.SecurityElement]::Escape($receiverPythonWindowless)
$receiverArguments = [Security.SecurityElement]::Escape(('"'+$receiverScript+'" --config "'+$receiverConfigFile+'"'))
$receiverDirectory = [Security.SecurityElement]::Escape($receiverProject)
$receiverXml = @"
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
 <RegistrationInfo><Description>Poll authorized [Codex-Fix] repository Issues and run isolated local ChatGPT-authenticated Codex exec.</Description></RegistrationInfo>
 <Triggers>
  <TimeTrigger><Repetition><Interval>PT5M</Interval><StopAtDurationEnd>false</StopAtDurationEnd></Repetition><StartBoundary>$receiverStart</StartBoundary><Enabled>true</Enabled></TimeTrigger>
  <LogonTrigger><Enabled>true</Enabled><UserId>$receiverSid</UserId></LogonTrigger>
 </Triggers>
 <Principals><Principal id="Author"><UserId>$receiverSid</UserId><LogonType>InteractiveToken</LogonType><RunLevel>LeastPrivilege</RunLevel></Principal></Principals>
 <Settings><MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy><DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries><StopIfGoingOnBatteries>false</StopIfGoingOnBatteries><StartWhenAvailable>true</StartWhenAvailable><Enabled>true</Enabled><Hidden>true</Hidden><ExecutionTimeLimit>PT0S</ExecutionTimeLimit></Settings>
 <Actions Context="Author"><Exec><Command>$receiverCommand</Command><Arguments>$receiverArguments</Arguments><WorkingDirectory>$receiverDirectory</WorkingDirectory></Exec></Actions>
</Task>
"@
Register-ScheduledTask -TaskName $receiverTaskName -Xml $receiverXml -Force | Select-Object TaskName,State
Write-Output ('설정: '+$receiverConfigFile)
