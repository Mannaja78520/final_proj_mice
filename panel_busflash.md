# Panel review - 2026-08-20 19:21

**Question.** Firmware over any transport, new today. Read firmware/src/core/BusUpdate.cpp, BusUpdate.h, and Flash.start_bus plus _run_bus in main_python/main.py. It writes the spare OTA slot from commands: FWBEGIN reserves and sets md5, FWDATA carries seq and decoded length and is refused without advancing if either is wrong, FWEND verifies then reboots. Question: what here can still leave a board with a bad image, or lose an update, WITHOUT saying so? Name file and line. Ignore style.

> **NO REVIEW HAPPENED.** All 2 models failed, so nothing below is a judgement about the code — it is a list of outages. Do not read the absence of findings as approval.

> - Error: Eligibility check failed: Post "https://daily-cloudco

**Files.** AudioPlayer.cpp, AudioPlayer.h, BrownoutGuard.cpp, BrownoutGuard.h, BusUpdate.cpp, BusUpdate.h, CommandRouter.cpp, CommandRouter.h, ConfigStore.cpp, ConfigStore.h, HwConfig.cpp, HwConfig.h, Identity.cpp, Identity.h, Log.cpp, Log.h, PeerDiscovery.cpp, PeerDiscovery.h, PortWrite.h, RS485Bus.cpp, RS485Bus.h, RgbStrip.cpp, RgbStrip.h, SDStore.cpp, SDStore.h, SequencePlayer.cpp, SequencePlayer.h, UserStore.cpp, UserStore.h, Util.cpp, Util.h, WebPortal.cpp, WebPortal.h, WifiArgs.h, WifiLink.h, main.py
**Cost.** ? tokens across 3 models

## The head reviewer (gemini-3.1-pro-high)

 - **FAILED** Error: Eligibility check failed: Post "https://daily-cloudcode-pa.googleapis.com/v1internal:loadCodeAssist": dial tcp: lookup daily-cloudcode-pa.googleapis.com:

## What each model said

### gemini-3.1-pro-high  _(97.6s, 0 tokens)_

 - **FAILED** Error: Eligibility check failed: Post "https://daily-cloudcode-pa.googleapis.com/v1internal:loadCodeAssist": dial tcp: lookup daily-cloudcode-pa.googleapis.com:

### gemini-3.7-flash-high  _(97.6s, 0 tokens)_

 - **FAILED** Error: Eligibility check failed: Post "https://daily-cloudcode-pa.googleapis.com/v1internal:loadCodeAssist": dial tcp: lookup daily-cloudcode-pa.googleapis.com:
