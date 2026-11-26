<# Removes the watchdog Scheduled Task (and only that). The assistant itself keeps running; stop it with
   "Stop PC Assistant.bat" or tools\rc_watchdog.ps1 -StopSession. Safe to run when nothing is installed. #>
param([string]$TaskName = "")
$Repo = Split-Path -Parent $PSScriptRoot
$text = Get-Content -Raw -Path (Join-Path $Repo "config\rc_watchdog.json")
$cfg = (($text -split "`n" | ForEach-Object { if ($_ -match '^\s*//') { '' } else { $_ } }) -join "`n") | ConvertFrom-Json
if (-not $TaskName) { $TaskName = $cfg.taskName }
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    "removed: $TaskName"
} else { "not installed: $TaskName" }
