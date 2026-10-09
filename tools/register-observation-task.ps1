param([switch]$Remove)
$ErrorActionPreference = 'Stop'
$taskName = 'CompanyResearch2-Observation'
$taskPython = 'C:\Users\aidan\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\pythonw.exe'
$taskScript = Join-Path $PSScriptRoot 'observation.py'
$taskRoot = Split-Path $PSScriptRoot -Parent
$expectedArguments = '-B "' + $taskScript + '" daemon'
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existingTask -and (($existingTask.Actions.Arguments -ne $expectedArguments) -or ($existingTask.Actions.Execute -ne $taskPython))) {
    throw 'A task with this name belongs to another action; refusing to replace or remove it.'
}
if ($Remove) {
    if ($existingTask) {
        Stop-ScheduledTask -TaskName $taskName
        $stopDeadline = (Get-Date).AddSeconds(10)
        do {
            $stoppedTask = Get-ScheduledTask -TaskName $taskName
            if ($stoppedTask.State -ne 'Running') { break }
            Start-Sleep -Milliseconds 250
        } while ((Get-Date) -lt $stopDeadline)
        if ($stoppedTask.State -eq 'Running') { throw 'Task did not stop; registration preserved.' }
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    }
    exit
}
if (-not (Test-Path -LiteralPath $taskPython)) { throw 'Bundled windowless Python runtime unavailable.' }
$taskUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$action = New-ScheduledTaskAction -Execute $taskPython -Argument $expectedArguments -WorkingDirectory $taskRoot
$triggers = @((New-ScheduledTaskTrigger -AtLogOn -User $taskUser), (New-ScheduledTaskTrigger -Daily -At '09:00'), (New-ScheduledTaskTrigger -Daily -At '18:00'))
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal -UserId $taskUser -LogonType Interactive -RunLevel Limited
$task = New-ScheduledTask -Action $action -Trigger $triggers -Settings $settings -Principal $principal -Description 'Observation-only £300 research monitor. No broker execution. Requires signed-in Windows user, internet and configured credentials for Telegram.'
Register-ScheduledTask -TaskName $taskName -InputObject $task -Force | Select-Object TaskName, State
