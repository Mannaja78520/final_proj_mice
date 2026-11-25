# QC on the PC: stop the QC hub from touching the real hub's world
Owner: Claude
Updated: 2026-11-25 19:55 (Bangkok)
Status: working
Branch: claude/qc-fixes-1125
Last commit: ca51182b
Plan: QC on the PC (no plan id; follow-up of the PC full QC of 2026-11-25)

## Doing now
Full serial QC on the fix branch, then draft PR, merge when green, rebuild MiceHub.exe and restart the hub.

## Done
- Full QC on the PC (main 1b52eeb9) had 13 failures; the cloud run had none of the camera or report ones.
- Report pictures (th), 3 checks: the PC runs the real voice helper, so the hub translated the QC report
  (text_en) and the list showed the English twin, not the words the check looks for. The check now points
  the hub at a dead helper (MICE_VOICE_CONFIG). Broken on purpose with tools/sabotage.py: caught.
- Camera set (pc_camera and alone_apps in a full run): the QC hub shared %TEMP%/mice-peers with the real
  hub, saw its Cameras app and read the real webcam ("Lavc63" frames). qc/lib/qc.py start_hub now sets a
  throwaway MICE_PEERS_DIR per QC run (a check that sets its own still wins). pc_camera 13/13. Sabotage: caught.

## Not changed, and why
- check_responsive "got 0 want 171": fails only in the parallel run; QC already reruns it alone and reports it FLAKY.
- visual_language "Thai on voice in ja" / "page threw showTab": 165/165 when run alone on the PC and in a clean
  worktree; not reproduced. Cause not proven (web files were rebuilt while the full run was going).
- "the system map is sound" (studio.md, app-voice.md): line-ending noise of the Windows checkout, no content change.
