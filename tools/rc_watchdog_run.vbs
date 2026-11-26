' Runs the watchdog check with NO window (a plain powershell.exe would flash a console every 3 minutes).
' Used by the Scheduled Task made by tools\rc_watchdog_install.ps1. Arguments are passed on to the script.
Set sh = CreateObject("WScript.Shell")
here = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
extra = ""
For Each a In WScript.Arguments
  extra = extra & " " & a
Next
sh.Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & here & "\rc_watchdog.ps1""" & extra, 0, False
