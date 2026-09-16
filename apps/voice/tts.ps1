# The local speaking voice: Windows' own synthesiser driven over WinRT.
#
# A20-9 sent the cloud away (edge-tts needed internet; mpg123 does not exist
# on Windows). What is left is the machine's built-in voice - measured
# 2026-08-23: this PC carries Microsoft Pattara (th-TH) plus David/Zira
# (en-US). PowerShell is the bridge because Python cannot reach WinRT without
# extra packages; the awkward async plumbing lives here in one editable file.
# The voice NAME comes in from config/voice.json, so adding a language means
# one entry there and nothing here.
param(
    [Parameter(Mandatory=$true)][string]$Text,
    [string]$Lang = "",
    [string]$Voice = "",
    [string]$Out = ""
)
$ErrorActionPreference = "Stop"
[void][Windows.Media.SpeechSynthesis.SpeechSynthesizer,Windows.Media.SpeechSynthesis,ContentType=WindowsRuntime]
Add-Type -AssemblyName System.Runtime.WindowsRuntime

$s = New-Object Windows.Media.SpeechSynthesis.SpeechSynthesizer
if ($Voice) {
    # Resolve short name (e.g. "Pattara") to exact installed DisplayName (e.g. "Microsoft Pattara")
    $installed = [Windows.Media.SpeechSynthesis.SpeechSynthesizer]::AllVoices | Where-Object { $_.DisplayName -match $Voice } | Select-Object -First 1
    if ($installed) {
        $Voice = $installed.DisplayName
        if (!$Lang) { $Lang = $installed.Language }
        # If Lang is short like "th", use the exact voice Language like "th-TH" to please SSML
        elseif ($installed.Language.StartsWith($Lang)) { $Lang = $installed.Language }
    }
}
$xmlLang = if ($Lang) { $Lang } else { $s.Voice.Language }
$EscapedText = $Text.Replace('&', '&amp;').Replace('<', '&lt;').Replace('>', '&gt;').Replace('"', '&quot;').Replace("'", '&apos;')
$voiceTag = if ($Voice) { "<voice name=`"$Voice`">{0}</voice>" -f $EscapedText }
            else { "{0}" -f $EscapedText }
$ssml = ('<?xml version="1.0" encoding="UTF-8"?>' +
         '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis"' +
         ' xml:lang="' + $xmlLang + '">' + $voiceTag + '</speak>')

$asTask = ([System.WindowsRuntimeSystemExtensions].GetMethods() |
           Where-Object { $_.Name -eq "AsTask" -and
                          $_.GetParameters().Count -eq 1 -and
                          $_.GetParameters()[0].ParameterType.Name -eq "IAsyncOperation``1" })[0]
$t = $asTask.MakeGenericMethod([Windows.Media.SpeechSynthesis.SpeechSynthesisStream]).Invoke(
        $null, @($s.SynthesizeSsmlToStreamAsync($ssml)))
$t.Wait(-1) | Out-Null
if ($t.IsFaulted) { throw $t.Exception.InnerException }

$net = [System.IO.WindowsRuntimeStreamExtensions]::AsStream($t.Result)
$ms = New-Object System.IO.MemoryStream
$net.CopyTo($ms)
$bytes = $ms.ToArray()
$s.Dispose()

if ($Out) {
    [System.IO.File]::WriteAllBytes($Out, $bytes)
} else {
    [System.Console]::OpenStandardOutput().Write($bytes, 0, $bytes.Length)
}
