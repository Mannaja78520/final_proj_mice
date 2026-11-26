<#
Installs (or refreshes) the Scheduled Task that runs tools\rc_watchdog.ps1: every N minutes until the PC shuts down, restarts or the user logs in again (it then removes itself)
(config\rc_watchdog.json), as the current user, no admin needed, low priority, no window.
  -TaskName   use another name (QC uses a throwaway one)
  -Script     run another script instead of the real watchdog (QC uses a harmless one)
Safe to run twice: the old task is replaced. Remove it with tools\rc_watchdog_uninstall.ps1.
#>
param([string]$TaskName = "", [string]$Script = "", [switch]$NoStart)
$ErrorActionPreference = "Stop"
$Repo = Split-Path -Parent $PSScriptRoot
$text = Get-Content -Raw -Path (Join-Path $Repo "config\rc_watchdog.json")
$cfg = (($text -split "`n" | ForEach-Object { if ($_ -match '^\s*//') { '' } else { $_ } }) -join "`n") | ConvertFrom-Json
if (-not $TaskName) { $TaskName = $cfg.taskName }
$every = [int]$cfg.everyMinutes

# what the task runs: the hidden-window wrapper (or a test script)
if ($Script) { $exe = "powershell.exe"; $arg = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$Script`"" }
else { $exe = "wscript.exe"; $arg = "//B //Nologo `"" + (Join-Path $PSScriptRoot "rc_watchdog_run.vbs") + "`"" }

$action = New-ScheduledTaskAction -Execute $exe -Argument $arg -WorkingDirectory $Repo
# NO logon trigger on purpose (user 2026-11-27): a restart or shutdown removes the check, the user starts it again by hand.
$repeat = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes $every)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -Hidden `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 5)
$settings.Priority = 7                                          # below normal: it must never get in the way
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}
# a second trigger: the "shutdown / restart started" event (User32 1074): the check runs once and removes itself
$ev = New-CimInstance -CimClass (Get-CimClass -ClassName MSFT_TaskEventTrigger -Namespace Root/Microsoft/Windows/TaskScheduler) -ClientOnly
$ev.Subscription = "<QueryList><Query Id=`"0`" Path=`"System`"><Select Path=`"System`">*[System[Provider[@Name='User32'] and (EventID=1074)]]</Select></Query></QueryList>"
$ev.Enabled = $true
# the boot time and the logon time NOW: when either differs later, the check removes itself (Fast Startup keeps the boot time)
$bootNow = [double][DateTimeOffset]::new((Get-CimInstance Win32_OperatingSystem).LastBootUpTime).ToUnixTimeSeconds()
$exp = Get-Process explorer -ErrorAction SilentlyContinue | Sort-Object StartTime | Select-Object -First 1
$logonNow = if ($exp) { [double][DateTimeOffset]::new($exp.StartTime).ToUnixTimeSeconds() } else { 0 }
$localDir = Join-Path $Repo ".local"
if (-not (Test-Path $localDir)) { New-Item -ItemType Directory -Path $localDir | Out-Null }
if (-not $Script) {
    (@{ boot = $bootNow; logon = $logonNow; task = $TaskName } | ConvertTo-Json -Compress) | Set-Content -Path (Join-Path $localDir "rc_install.json") -Encoding UTF8
}
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger @($repeat, $ev) -Settings $settings `
    -Principal $principal -Description "Keeps the Claude PC assistant (remote control) for $Repo running. Remove: tools\rc_watchdog_uninstall.ps1" | Out-Null
if (-not $NoStart) { Start-ScheduledTask -TaskName $TaskName }
"installed: $TaskName (every $every minutes until the PC restarts, low priority, no window)"
