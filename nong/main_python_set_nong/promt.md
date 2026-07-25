### 2026-07-12 07:40
make the program that like the 3d model edit and like the blender or solidworks i will export the robot model to this program and it have revolute joint pismatic joint and universal joint make from 2 revolute to make the shoulder of humanoid need to make the program that can setup the humanoid like video edit start with start post and can edit the start post after that wwhen drag the model to another position save that position and calculate the time to run from start point to drag p[osition can make like this in series and save it to use in the nong module it look like humanoid have universal joint make from 2 servo of MG90s in shoulder and universal joint make from 2 servo of MG90s in elbow per arm don't have finger, this nong humanoid have 2 arm

conclusion need to make the program that can setup and make the movement of the nong robot that only have the top part have 2 universal joint in shoulder and elbow per arm and make the module in the firmware move the firmware in lift to the code folder because we need to upload only 1 time and setup later which module of it

### 2026-07-12 07:55
make like the sequense of the humanoid pose and save it to some file i'll put it to sd card and then when use i'll run using sd card and select sequnse my self

if 1 esp not enough you can include more than 1 esp in nong module but you need to make the link of the nong module for me make it can use together

### 2026-07-12 08:00
make bypass everything like in the firmeare allow everything

### 2026-07-12 08:05
use the same setting and put the promt to promt.md like the firmware or you can use the same setting use it move the promt.md and use evetything the same

### 2026-07-12 08:40
make it
- save sequence to sd card
- can select to run which sequence first can edit sequence
- command the module by web sdk
- how the mode that can monitor the real sequence of the robot
- fix the at least time from point to point by distance if adjust the speed of servo the minimum time to run is change map with real move to avoid the realarm not go to that position, if need more time can adjust it but if time is smaller than can't

### 2026-07-12 09:05
if 1 esp can use it all use only 1 if can't can make it use 2 esp for this module but if use more than 1 esp make can select which esp_module pair with this one and can run with seameless.

this nong module it don't have the encoder and speaker and RGB have only 8 servo SD card only if i don't miss something let check it for me.

let check everything i want you did it all?
make the nong sdk can access the usb wifi and rs485 too like the access UI that run seperate.

### 2026-07-12 09:30
edit the joint of the robot when everything 90 deg it not close to the body make the mode that i can edit it by not edit in the code my self

the SD file can edit via wifi, usb, rs485 too not only wifi make all program dynamic can change everytime

### 2026-07-12 10:00
how to load the stl model i need to put it to model_folder?
make when run the nong SDK, when run the movement if the joint it stuck with other joint alert popup show can't run the robot the robot will crash. and red mark which sequence make the probelm, it will easy to check.
when i need to use the nong SDK in the future or another time the host pc need to run main.py?

### 2026-07-12 10:30
make when host run the nong studio the other device in the same local wifi can access the nong studio

when add the stl please donot remove the sphire joint in the middle of joint make it same without stl to know the length and the stl when upload sometime itnot the same origin with the robot make it can rotage rhe stl too

the stl have own length when upload the stl use the length of stl this will make the nong studio dynamic use make can edit the body, head texture or stl and can import the clothes to cover all part

### 2026-07-12 14:20
the run_nong_studio.bat make it exe file and edit the icon make it user friendly and can use with ubuntu or android
we already have the edit rigmode and stl edit make it in another tab the tap name setup the main tap is for movement only this will make it easy to use more than this
the model can use the texture to visiualize can import the file that like stl but can edit the color pixel by pixel i don't know what is that but some time i'll draw it and upload like the head need color to visualize
the exe file can't use with other system?

### 2026-07-12 14:35
show the important joint in x y z codinate too.

### 2026-07-12 17:30
do all your work that stuck before hit limit / make can edit the neutral pose too
(bug report: JOINT commands reply 0.0, joints stuck at 0, monitor shows arms inside body, can't pair)
make when use the nong module: show coordinate xyz, position not written realtime, stop = detach power, have attach button
modes: drag by slider / follow sequence / follow nong studio; feedback of now position; moving one joint must not zero the others
if nong studio alive show simulation in web too; nong studio = function of the main program
main web app: first web sees all rs485/usb modules, select child web per module, dynamic for future modules
fix usb connect in nong studio; gizmo deselect; stl length revert to built-in + separate L/R lengths
auto-discover modules (no typing nong.local); main app opens in the main folder

### 2026-07-12 18:20
in hub it have usb you can see inside the sub it is the module that we use or not and also serch the rs485 too
then make it can click for go to the module website to config everything for now it show only which port connect to pc make it go to the it own module web like wifi
the stl config rotage/offest/scale it not in the same line hard to understand make it rotage: roll,pitch,yaw / offset: x,y,z / scale: scale
and when select the stl make it refresh automatic like go to build in show the rotage, offet, scale box imedialy
the Joint positions in movement tab overlap go outside the box make it vertical per arm
the insert of the number in joints the number box it overlap go outside the black background
make can drag the movement/setup tab bigger or smaller
make can input the x y z in the sequece and show it
make the plane can select the plane of the program to drag nong easy than 3d plane

### 2026-07-12 23:30
in the nong studio joint rig control make min-max per servo (humanoid limit ~30-150, not 0-180).
the servo has gear 12:13 (pinion 12, gear 13) driving the joint — check the nong studio and the nong module, make it dynamic can change and setting.

### 2026-07-12 23:55
can fix the roll/pitch/yaw of the joint (editable axis), not only invert
the min-max 30 and 150 mean JOINT limit but the servo can run 0-180
the drag of the rig model — if a position is reachable, let me drag to it; dragging the left arm up should move shoulder AND elbow together to stay stable (currently limited by the joint)

### 2026-07-13 00:20
when set zero, does the servo need 0 or 180, or can it be 90?
make sure the nong studio can drag and the program fixes the position by adjusting the shoulder and elbow.

### 2026-07-13 00:40
when drag from the hand don't show/select the joint — the joint rings should show only when you CLICK on the joint.
(photo of the real arm: 2 universal joints — shoulder gimbal + elbow gimbal + paddle hand, confirms the rig structure.)

### 2026-07-14 12:10
make nong work without SD card too — run by live command from Nong Studio if no SD card.
make set-zero of the nong module pressable from the web; set-zero configures the zero-position angle based at 90°; add "move to zero-position".
put the zero-position behind a password tab, in BOTH the nong module web and Nong Studio web.
default user: manny, pass: 12345678; allow changing the password (and user).

### 2026-07-14 12:40
per hardware module per config file — NOT compile-time before download.
make a web where each module's pins can be configured (assign pins via the web),
stored in the ESP32's own memory (NVS) so it's remembered, and show in the web
which GPIOs can be used (pin picker with valid-pin hints).

### 2026-07-14 13:10
add an easy way to reach a per-module Setup page to configure everything, gated by the login (user+password) from before.
after logging in with manny, be able to ADD users (multi-user). default manny/12345678.

### 2026-07-14 13:40
cannot config via web usb — make it easy to reach but need login.
split hardware config into per-module files: esp32_hardware_lift_module.h + esp32_hardware_nong_module.h.
make the site the SAME over wifi, usb, rs485 — no difference between them.
in the pin config: select per module, same pin across different boards is fine; show which pins are input-only / RX / TX / PWM; add an ESP32 pinout image served from the PC (not embedded on the ESP32, saves ROM).

### 2026-07-14 14:00
can't see the pin setting when opening the module over USB — where is it? make USB/WiFi/RS485 the same web.
can setup the ESP32 WiFi mode (ON/OFF/AP) too — why was it deleted?

### 2026-07-14 14:20
add a tab selector to choose nong module or lift module (config/controls) — make it dynamic so more module types can be added in the future.

### 2026-07-14 14:35
clarify tabs: WITHOUT login you can only CONTROL the board's real type (nong board -> nong control only, lift -> lift only). The module-type tabs belong to the PIN CONFIG (after login): different tab per module to select which type's pins to config, same select-box dropdowns as before.

### 2026-07-14 15:00
login screen should only show when you click Login (hidden otherwise).
default WiFi mode = ON (join WiFi, AP fallback).
the pin select lost its tab — make the pin-select tabs appear again.

### 2026-07-14 15:20
rig model joint editing is ok — just increase it: let me rotate roll/pitch/yaw in degrees for the shoulder and elbow joints too, because the joint axes aren't exactly at 90°.

### 2026-07-14 15:50
when I rotate the joint orientation (axis tilt), make the red/green/blue rings rotate to follow the orientation I adjust too.
SD card and RS485 are on all modules, but RGB and AMP (I2S speaker) are lift-only — nong doesn't have them (so the audio pins should be under the lift module only).

### 2026-07-15 11:00
shoulder joint rings should rotate when moved, like the elbow (rotating the red circle should turn the second circle the same as the elbow does).
make the elbow joint draggable like the hand (IK), but keep the rings for rotating each roll servo.

### 2026-07-15 11:30
make manipulation drags require holding Shift (plain left-drag orbits the camera).

### 2026-07-15 12:15
add on-screen view/plane buttons (like a Fusion/SolidWorks view cube): clicking a plane moves the camera to look straight at it and sets the drag plane, so Shift+dragging a joint moves it flat in that plane.

### 2026-07-15 12:35
why did you remove being able to move the circle (rings)? keep the current setup but make the circles draggable too (rings should rotate without needing Shift; keep Shift only for the wrist/elbow IK balls).

### 2026-07-15 13:10
make the robot arm and the joints size-configurable — each joint can be a different size and each bar can be a different size.

### 2026-07-22 
make the shoulders use PDI-1181MG and the elbows use MG90S, and make it adjustable to another servo in the future. Shoulder gear ratio changes to pinion 15 : driven gear 18 teeth; the elbow keeps its old ratio. Also make the servo pulse changeable per joint (left/right, shoulder/elbow) because the servo may be swapped later.

### 2026-07-22
maybe sometime I'll use a 270 deg servo, not only 180 — make that easy to configure in Nong Studio and in the module config.

### 2026-07-24
Add 2 servos to the nong module: one to shrug the shoulders up/down (MG90S, only ~6°), one to rotate the WAIST so nong turns to look left/right (TianKongRC 35kg, 270°). This is the whole system (shown in SolidWorks nong_assembly.SLDASM). Update Nong Studio, the nong website, the nong module firmware — all of it. Also: when configuring a module over WiFi you can set the pins, but over USB you can't — make it the same page (it wasn't).

### 2026-07-24
Save the web app as patches — each patch is one change I asked for, and the old versions don't disappear.

### 2026-07-24
The PDI-1181MG is a 270° servo, same as the WAIST servo — not 180°.
