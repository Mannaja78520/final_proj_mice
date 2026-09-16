# Panel review - 2026-08-27 19:10

**Question.** A TPA3110 is an ANALOG class-D amp (line input), but firmware/src/core/AudioPlayer.cpp begin() always builds AudioOutputI2S and drives digital I2S on 3 pins - wrong for this amp. Plan: a new DATA file firmware/config/amps.json listing amp kinds (id, label, mode i2s|analog|dac, which pins are wired, a plain wiring hint), generated into a C header by tools/gen_tables.py the way servos.json and cam_boards.json are; the CHOICE stored per board in NVS next to the pin map in core/HwConfig, picked by NAME from the boards Hardware-pins page; AudioPlayer::begin then builds AudioOutputI2SNoDAC for analog (one wire, delta-sigma, mono), AudioOutputI2S with INTERNAL_DAC for the built-in DAC on GPIO25-26, or plain AudioOutputI2S for a real I2S amp. Constraint: a nong board has ONLY GPIO 0, 2 and 12 free after 10 servos + SD(5,18,19,23) + RS485(4,16,17); 25 and 26 are servos 3 and 4. Question: what is WRONG or missing in this plan, and is putting the amp kind in HwConfig the right home or should it live somewhere else. Answer in at most 20 lines.

**Files.** AudioPlayer.cpp, AudioPlayer.h, BrownoutGuard.cpp, BrownoutGuard.h, BusUpdate.cpp, BusUpdate.h, CommandRouter.cpp, CommandRouter.h, ConfigStore.cpp, ConfigStore.h, HwConfig.cpp, HwConfig.h, Identity.cpp, Identity.h, Log.cpp, Log.h, PeerDiscovery.cpp, PeerDiscovery.h, PortWrite.h, RS485Bus.cpp, RS485Bus.h, SDStore.cpp, SDStore.h, SequencePlayer.cpp, SequencePlayer.h, UserStore.cpp, UserStore.h, Util.cpp, Util.h, WebPortal.cpp, WebPortal.h, WifiArgs.h, WifiLink.h
**Cost.** 328205 tokens across 3 models

## The head reviewer (gemini-3.1-pro-high)

 - **real** `E:/final_proj/mice/code/.staging/firmware/src/core/AudioPlayer.h:49` out_ pointer is typed AudioOutputI2S*, must be base AudioOutput* to store AudioOutputI2SNoDAC.
 - **real** `E:/final_proj/mice/code/.staging/firmware/src/core/AudioPlayer.cpp:18` SetPinout called unconditionally, invalid for DAC and NoDAC modes.
 - **real** `E:/final_proj/mice/code/.staging/firmware/src/core/HwConfig.h:10` Pins struct only holds int GPIOs, storing amp kind needs enum or string field in HwConfig.
 - **real** `E:/final_proj/mice/code/.staging/firmware/src/core/HwConfig.cpp:41` FIELDS assumes three I2S pins, analog mode only needs DOUT making BCLK and LRC optional.
 - **real** `E:/final_proj/mice/code/.staging/firmware/config/esp32_hardware_nong_module.h:98` GPIO 25/26 are servos 3/4, ESP32 DAC is fixed to 25/26 in silicon making INTERNAL_DAC fail on nong.
 - **real** `E:/final_proj/mice/code/.staging/firmware/config/esp32_hardware_nong_module.h:115` GPIO 0/2/12 are strapping pins, audio line on GPIO 12 must not pull high at boot or flash voltage brownouts.
 - **fine** `firmware/config/amps.json:1` no issues
 - **fine** `firmware/src/core/HwConfig.h:1` no issues

## What each model said

### gemini-3.1-pro-high  _(143.7s, 67389 tokens)_

 - **fine** `firmware/config/amps.json:1` This is fine. Edit this file to add the next one.
 - **fine** `firmware/src/core/HwConfig.h:1` This is fine.
 - **real** `firmware/src/core/AudioPlayer.cpp:1` INTERNAL_DAC fails. ESP32 internal DAC requires GPIO 25 and 26, conflicting with servos.
 - **maybe** `firmware/src/core/HwConfig.cpp:1` GPIO 0, GPIO 2, GPIO 12: strapping pins. Connected circuits alter boot state, breaking boot mode or flash voltage.
 - **real** `firmware/src/core/AudioPlayer.cpp:1` AudioOutputI2SNoDAC: outputs digital PDM. TPA3110 analog input requires external RC low-pass filter.

### gemini-3.7-flash-high  _(76.6s, 197319 tokens)_

 - **real** `E:/final_proj/mice/code/.staging/firmware/src/core/HwConfig.h:16` HwConfig is correct home; amp choice defines hardware wiring and frees pins, unlike runtime ConfigStore.h.
 - **real** `E:/final_proj/mice/code/.staging/firmware/src/core/HwConfig.h:10` Pins struct only holds int GPIOs; storing amp kind needs an enum or string field in HwConfig.
 - **real** `E:/final_proj/mice/code/.staging/firmware/src/core/HwConfig.cpp:41` FIELDS assumes three I2S pins; analog mode only needs DOUT, so BCLK and LRC should be optional.
 - **real** `E:/final_proj/mice/code/.staging/firmware/config/esp32_hardware_nong_module.h:98` GPIO 25/26 are servos 3/4; ESP32 DAC is fixed to 25/26 in silicon, so INTERNAL_DAC cannot work on nong.
 - **real** `E:/final_proj/mice/code/.staging/firmware/src/core/AudioPlayer.h:49` out_ pointer is typed AudioOutputI2S*; must be base AudioOutput* to store AudioOutputI2SNoDAC.
 - **real** `E:/final_proj/mice/code/.staging/firmware/src/core/AudioPlayer.cpp:18` SetPinout called unconditionally; invalid for DAC and NoDAC modes.
 - **real** `E:/final_proj/mice/code/.staging/firmware/config/esp32_hardware_nong_module.h:115` GPIO 0/2/12 are strapping pins; audio line on GPIO 12 must not pull high at boot or flash voltage brownouts.
