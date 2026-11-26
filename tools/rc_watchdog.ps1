<#
Keeps the Claude remote-control session ("PC assistant") for this repo folder running.

  powershell -File tools\rc_watchdog.ps1                 one check (what the Scheduled Task runs every 3 minutes)
  powershell -File tools\rc_watchdog.ps1 -DryRun         say what it would do, change nothing
  powershell -File tools\rc_watchdog.ps1 -Status         one line: running or not
  powershell -File tools\rc_watchdog.ps1 -DecideJson f   decision logic only, on a JSON file (QC self-test)

How it decides (config/rc_watchdog.json):
  * only a claude.exe started as `remote-control ... --spawn same-dir` from the user's own .local\bin counts;
    the desktop app and every other claude process are never touched;
  * the one it launched last time (pid in .local\rc_watchdog.state.json) is the one it watches; if none is
    recorded and exactly one candidate exists it adopts it; two or more candidates = ambiguous, it does nothing;
  * a connected session that has written no heartbeat for stallMinutes while a task file says "Doing now" is
    STALLED and is handled like an unhealthy one (stallAction in config);
  * "connected" = the process holds an established network connection; not connected on two checks in a row
    = stop that one process and start it again;
  * not running = start it; at most 3 starts per hour, then it waits and logs why;
  * at a usage limit (tools/ai_watch.py wrote "limited: claude until <time>") it does nothing until the reset time:
    detecting the limit, reading the reset time and handing the work to Codex is the AI watcher's job, not this one's;
  * it does nothing in the first 90 s after logon, and only one copy runs at a time (a named mutex).
Log: .local\rc_watchdog.log (rotated). Turn it off: tools\rc_watchdog_uninstall.ps1 or "Stop PC Assistant.bat".
#>
param([switch]$DryRun, [switch]$Status, [switch]$StopSession, [string]$DecideJson = "", [string]$TaskName = "")

$ErrorActionPreference = "Stop"
$Repo = Split-Path -Parent $PSScriptRoot
$CfgPath = Join-Path $Repo "config\rc_watchdog.json"
$LocalDir = Join-Path $Repo ".local"
$LogPath = Join-Path $LocalDir "rc_watchdog.log"
$StatePath = Join-Path $LocalDir "rc_watchdog.state.json"

function Read-Config {
    $text = Get-Content -Raw -Path $CfgPath
    # drop // comments (outside strings is all this file uses)
    $clean = ($text -split "`n" | ForEach-Object { if ($_ -match '^\s*//') { '' } else { $_ } }) -join "`n"
    return $clean | ConvertFrom-Json
}

function Test-Candidate($p, $profileDir) {
    # a remote-control claude.exe from the user's own install, never the desktop app
    if ($p.Name -ne "claude.exe") { return $false }
    $cmd = [string]$p.CommandLine
    if ($cmd -notmatch '\bremote-control\b') { return $false }
    if ($cmd -notmatch '--spawn\s+same-dir') { return $false }
    if ($cmd -notmatch [regex]::Escape($profileDir)) { return $false }
    return $true
}

# The whole decision, pure: no process, no disk, no clock. QC runs it with made-up inputs.
function Get-WatchdogDecision($In) {
    $cfg = $In.Config
    $now = [double]$In.Now
    $state = @{ pid = 0; unhealthy = 0; launches = @() }
    if ($In.State) {
        if ($In.State.pid) { $state.pid = [int]$In.State.pid }
        if ($In.State.unhealthy) { $state.unhealthy = [int]$In.State.unhealthy }
        if ($In.State.launches) { $state.launches = @($In.State.launches | ForEach-Object { [double]$_ }) }
    }
    $out = @{ Action = "ok"; Pid = 0; Reason = ""; State = $state }
    # THE CHECK REMOVES ITSELF when the PC shuts down, restarts or the user logs in again (user 2026-11-27): after a
    # restart the user messages to resume, and "Start PC Assistant" installs the check again. Three signals: a shutdown
    # / restart event in the last 2 minutes, a different boot time than when it was installed, a different logon time
    # (Fast Startup keeps the boot time across a "Shut down", the logon time always changes).
    if ($In.ShutdownRecent) { $out.Action = "self-remove"; $out.Reason = "the PC is shutting down or restarting"; return $out }
    if ($In.Install) {
        $db = [math]::Abs([double]$In.BootEpochNow - [double]$In.Install.boot)
        $dl = [math]::Abs([double]$In.LogonEpochNow - [double]$In.Install.logon)
        if ($db -gt 5 -or $dl -gt 5) {
            $out.Action = "self-remove"; $out.Reason = "the PC was restarted or you logged in again since this was installed"; return $out
        }
    }
    if ($In.LogonAgeSeconds -lt $cfg.minLogonAgeSeconds) {
        $out.Action = "wait"; $out.Reason = "logon is only $([int]$In.LogonAgeSeconds) s old"; return $out
    }
    # AT A USAGE LIMIT: tools/ai_watch.py (the AI watcher) has seen the limit notice in Claude's log, parsed the reset time
    # and handed the work to Codex. Starting or restarting Claude now would only hit the limit again, so do nothing until
    # the reset time has passed.
    if ($In.ClaudeLimitedUntil -ne $null -and $now -lt [double]$In.ClaudeLimitedUntil) {
        $out.Action = "limited"; $out.Reason = "Claude is at its usage limit until epoch $([int64]$In.ClaudeLimitedUntil); waiting (the AI watcher hands the work on)"
        return $out
    }
    $cands = @($In.Procs | Where-Object { Test-Candidate $_ $In.ProfileDir })
    $target = $null
    if ($state.pid -gt 0) { $target = $cands | Where-Object { [int]$_.Id -eq $state.pid } | Select-Object -First 1 }
    if (-not $target) {
        if ($cands.Count -eq 1) { $target = $cands[0]; $out.Action = "adopt"; $out.Reason = "found the one running session (pid $($target.Id))" }
        elseif ($cands.Count -gt 1) {
            $out.Action = "ambiguous"; $out.Reason = "$($cands.Count) remote-control sessions are running; touching none"; return $out
        }
    }
    if ($target) {
        $conns = 0
        if ($In.Connections) { $v = $In.Connections."$($target.Id)"; if ($v) { $conns = [int]$v } }
        $out.Pid = [int]$target.Id
        $state.pid = $out.Pid
        if ($conns -ge [int]$cfg.minConnections) {
            $state.unhealthy = 0
            if ($out.Action -ne "adopt") { $out.Action = "ok"; $out.Reason = "running, $conns connection(s)" }
            # connected, but is it still WORKING? no heartbeat for stallMinutes while a task says "Doing now"
            $stallMin = [double]$cfg.stallMinutes
            $age = $null; if ($In.HeartbeatAgeMinutes -ne $null) { $age = [double]$In.HeartbeatAgeMinutes }
            $doing = 0; if ($In.DoingTasks) { $doing = [int]$In.DoingTasks }
            if ($cfg.stallAction -ne "off" -and $doing -gt 0 -and $age -ne $null -and $age -gt $stallMin) {
                if ($cfg.stallAction -eq "restart") {
                    $out.Action = "restart"; $out.Reason = "stalled: no heartbeat for $([int]$age) min while $doing task(s) say Doing now"
                } else {
                    $out.Action = "stalled"; $out.Reason = "no heartbeat for $([int]$age) min while $doing task(s) say Doing now (log only)"
                    return $out
                }
            } else { return $out }
        } else {
            $state.unhealthy = $state.unhealthy + 1
            if ($state.unhealthy -lt [int]$cfg.unhealthyChecksBeforeRestart) {
                $out.Action = "unhealthy"; $out.Reason = "no connection (check $($state.unhealthy) of $($cfg.unhealthyChecksBeforeRestart))"; return $out
            }
            $out.Action = "restart"; $out.Reason = "no connection on $($state.unhealthy) checks in a row"
        }
    } else {
        $out.Action = "launch"; $out.Reason = "no remote-control session is running"
    }
    if (-not $In.ExeExists) { $out.Action = "no-exe"; $out.Reason = "claude.exe was not found"; return $out }
    $recent = @($state.launches | Where-Object { ($now - $_) -lt 3600 })
    $state.launches = $recent
    if ($recent.Count -ge [int]$cfg.maxRelaunchesPerHour) {
        $out.Action = "backoff"; $out.Reason = "already started $($recent.Count) times in the last hour"; return $out
    }
    $state.launches = @($recent + $now)
    $state.unhealthy = 0
    return $out
}

if ($DecideJson) {
    $in = Get-Content -Raw -Path $DecideJson | ConvertFrom-Json
    $d = Get-WatchdogDecision $in
    $d | ConvertTo-Json -Depth 6 -Compress
    exit 0
}

function Write-Log($msg) {
    if (-not (Test-Path $LocalDir)) { New-Item -ItemType Directory -Path $LocalDir | Out-Null }
    $cfg = Read-Config
    if ((Test-Path $LogPath) -and ((Get-Item $LogPath).Length -gt ([int]$cfg.logMaxKB * 1KB))) {
        for ($i = [int]$cfg.logKeepFiles - 1; $i -ge 1; $i--) {
            $a = "$LogPath.$i"; $b = "$LogPath.$($i + 1)"
            if (Test-Path $a) { Move-Item -Force $a $b }
        }
        Move-Item -Force $LogPath "$LogPath.1"
    }
    Add-Content -Path $LogPath -Value ("{0}  {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $msg)
}

function Get-Snapshot($cfg) {
    $profileDir = $env:USERPROFILE
    $procs = @(Get-CimInstance Win32_Process -Filter "Name='claude.exe'" -ErrorAction SilentlyContinue |
               ForEach-Object { @{ Id = $_.ProcessId; Name = $_.Name; CommandLine = $_.CommandLine } })
    $conns = @{}
    foreach ($p in $procs) {
        try {
            $n = @(Get-NetTCPConnection -State Established -OwningProcess $p.Id -ErrorAction SilentlyContinue).Count
            $conns["$($p.Id)"] = $n
        } catch { $conns["$($p.Id)"] = 0 }
    }
    $explorer = Get-Process explorer -ErrorAction SilentlyContinue | Sort-Object StartTime | Select-Object -First 1
    $logon = if ($explorer) { ((Get-Date) - $explorer.StartTime).TotalSeconds } else { 0 }
    $exe = Join-Path $profileDir $cfg.exe
    $bootEpoch = [double][DateTimeOffset]::new((Get-CimInstance Win32_OperatingSystem).LastBootUpTime).ToUnixTimeSeconds()
    $logonEpoch = if ($explorer) { [double][DateTimeOffset]::new($explorer.StartTime).ToUnixTimeSeconds() } else { 0 }
    $install = $null
    $instPath = Join-Path $LocalDir "rc_install.json"
    if (Test-Path $instPath) { try { $install = Get-Content -Raw $instPath | ConvertFrom-Json } catch { $install = $null } }
    $shutdown = $false
    try {
        $ev = @(Get-WinEvent -FilterHashtable @{ LogName = "System"; Id = 1074; StartTime = (Get-Date).AddMinutes(-2) } -ErrorAction SilentlyContinue)
        $shutdown = ($ev.Count -gt 0)
    } catch { $shutdown = $false }
    $state = $null
    if (Test-Path $StatePath) { try { $state = Get-Content -Raw $StatePath | ConvertFrom-Json } catch { $state = $null } }
    $limitedUntil = $null
    $awState = Join-Path (Join-Path (Join-Path $Repo "_out") "ai_watch") "state.json"
    if (Test-Path $awState) {
        try {
            $aw = Get-Content -Raw -Path $awState | ConvertFrom-Json
            $u = $aw.limited.claude
            if ($u) { $limitedUntil = [double][DateTimeOffset]::Parse([string]$u).ToUnixTimeSeconds() }
        } catch { $limitedUntil = $null }
    }
    $hbAge = $null
    $hb = Join-Path $LocalDir "rc_heartbeat.json"
    if (Test-Path $hb) { $hbAge = ((Get-Date) - (Get-Item $hb).LastWriteTime).TotalMinutes }
    $doing = 0
    foreach ($f in @(Get-ChildItem (Join-Path $Repo "handoff\tasks") -Filter *.md -ErrorAction SilentlyContinue)) {
        $t = Get-Content -Raw -Path $f.FullName -ErrorAction SilentlyContinue
        if ($t -match '(?ms)^##\s+Doing now\s*\r?\n+([^\r\n]+)') {
            if ($Matches[1] -notmatch '^(paused|nothing|none|done|-|n/a)') { $doing++ }
        }
    }
    return @{
        BootEpochNow = $bootEpoch; LogonEpochNow = $logonEpoch; Install = $install; ShutdownRecent = $shutdown
        HeartbeatAgeMinutes = $hbAge; DoingTasks = $doing; ClaudeLimitedUntil = $limitedUntil
        Config = $cfg; Now = [double][DateTimeOffset]::UtcNow.ToUnixTimeSeconds(); LogonAgeSeconds = $logon
        ProfileDir = $profileDir; Procs = $procs; Connections = $conns; ExeExists = (Test-Path $exe)
        State = $state; ExePath = $exe
    }
}

$cfg = Read-Config
if ($Status) {
    $snap = Get-Snapshot $cfg
    $c = @($snap.Procs | Where-Object { Test-Candidate $_ $snap.ProfileDir })
    if ($c.Count -eq 0) { "not running" } else { "running (pid $($c[0].Id), $($snap.Connections["$($c[0].Id)"]) connection(s))" }
    exit 0
}

if ($StopSession) {
    # the one session this watchdog manages, and nothing else
    $snap = Get-Snapshot $cfg
    $c = @($snap.Procs | Where-Object { Test-Candidate $_ $snap.ProfileDir })
    $pid0 = 0; if ($snap.State -and $snap.State.pid) { $pid0 = [int]$snap.State.pid }
    $t = $c | Where-Object { [int]$_.Id -eq $pid0 } | Select-Object -First 1
    if (-not $t -and $c.Count -eq 1) { $t = $c[0] }
    if ($DryRun) { if ($t) { "would stop pid $($t.Id)" } else { "nothing to stop" }; exit 0 }
    if ($t) { Stop-Process -Id $t.Id -Force -ErrorAction SilentlyContinue; Write-Log "stopped pid $($t.Id) on request"; "stopped" } else { "nothing to stop" }
    exit 0
}

$mutex = New-Object System.Threading.Mutex($false, "Local\MiceRcWatchdog")
if (-not $mutex.WaitOne(0)) { exit 0 }                      # another check is running: this one stops
try {
    $snap = Get-Snapshot $cfg
    $d = Get-WatchdogDecision $snap
    $line = "$($d.Action): $($d.Reason)"
    if ($DryRun) { "would do: $line"; exit 0 }
    if ($d.Action -eq "self-remove") {
        $tn = if ($TaskName) { $TaskName } else { $cfg.taskName }
        Write-Log "$line; removing the Scheduled Task '$tn'"
        Remove-Item -Path (Join-Path $LocalDir "rc_install.json") -ErrorAction SilentlyContinue
        Unregister-ScheduledTask -TaskName $tn -Confirm:$false -ErrorAction SilentlyContinue
        exit 0
    }
    if ($d.Action -in @("restart", "launch")) {
        if ($d.Action -eq "restart" -and $d.Pid -gt 0) {
            Write-Log "restart: stopping only pid $($d.Pid)"
            Stop-Process -Id $d.Pid -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 3
        }
        $p = Start-Process -FilePath $snap.ExePath -ArgumentList $cfg.args -WorkingDirectory $Repo -WindowStyle Hidden -PassThru
        $d.State.pid = $p.Id
        Write-Log "$line; started pid $($p.Id)"
    } elseif ($d.Action -ne "ok" -or $d.State.unhealthy -gt 0) {
        Write-Log $line                                     # quiet when everything is fine
    }
    if (-not (Test-Path $LocalDir)) { New-Item -ItemType Directory -Path $LocalDir | Out-Null }
    ($d.State | ConvertTo-Json -Compress) | Set-Content -Path $StatePath -Encoding UTF8
} finally {
    $mutex.ReleaseMutex()
}
