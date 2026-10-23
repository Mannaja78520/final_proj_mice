# Tests that need the real nong

Owner:
Updated: 2026-10-21 04:20 (Bangkok)
Branch: main
Last commit: c859601
Plan: A45-11

## Goal
Check on the real robot what so far ran only against the fake robot.

## Done
- Code for all of these is merged (PR #26, #27, #36, #39, #40). Show, Timeline, music and SD upload already played on the real nong 2026-10-12.

## Next
1. Palm up / back of hand per hand: flip each hand in Studio and watch the real arm.
2. Run last.yaml from the robot's own page http://nong.local/ without the hub.
3. OTA update over WiFi.
4. TALK ON with the phone microphone after the reboot fix.
5. Studio Video tab: "Put the video's sound on the robot" and listen.
6. A48-1 CAD look (Studio ▸ Views ▾ ▸ Robot look = CAD model): move each joint and raise each hand on the real nong; the CAD model and the arm must go the same way (fakes + real URDF only so far).
7. A48-6 rig with the CAD's sizes and shoulder spots (button in Views ▾ ▸ Robot look): at home and 3 poses the real arms vs Studio; servo numbers were not changed, so only the drawing moved. If the real arms follow the CAD better, add "joints" to urdf_view.json rigFromCad.

## Blocked
- nong powered on, PC hotspot "manny" on, RS485 on COM21. Ask the user when the robot is on the bench.
