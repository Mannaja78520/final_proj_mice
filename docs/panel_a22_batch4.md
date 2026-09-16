# Panel review - 2026-08-26 01:27

**Question.** Review these A22-1 firmware fixes in .staging for bugs the checks miss. Claim 1: RS485Bus broadcast replies now queue (4 slots, oldest displaced) instead of one pendingReply_ slot - see src/core/RS485Bus.h and .cpp loop()/handleLine(). Claim 2: /api/upload destination is now per-request locals computed from req dir query + filename arg each chunk; members removed - see WebPortal.cpp handler. Claim 3: checkLink scan pick moved to wifilink::PeerPick (known beats any guess, strongest within kind), tested natively - see core/WifiLink.h and WebPortal.cpp checkLink. What is NOT true or unsafe? Answer in at most 25 lines.

**Files.** AudioPlayer.cpp, AudioPlayer.h, BrownoutGuard.cpp, BrownoutGuard.h, BusUpdate.cpp, BusUpdate.h, CommandRouter.cpp, CommandRouter.h, ConfigStore.cpp, ConfigStore.h, HwConfig.cpp, HwConfig.h, Identity.cpp, Identity.h, Log.cpp, Log.h, PeerDiscovery.cpp, PeerDiscovery.h, PortWrite.h, RS485Bus.cpp, RS485Bus.h, SDStore.cpp, SDStore.h, SequencePlayer.cpp, SequencePlayer.h, UserStore.cpp, UserStore.h, Util.cpp, Util.h, WebPortal.cpp, WebPortal.h, WifiArgs.h, WifiLink.h
**Cost.** 472689 tokens across 3 models

## The head reviewer (gemini-3.1-pro-high)

 - **real** `src/core/SequencePlayer.cpp:87` router_->module()->busy() lacks null check, crashes if module pointer null.
 - **real** `src/core/AudioPlayer.cpp:63` cleanup() deletes file_ outside sd_->lock(), races SPI access with async web tasks.
 - **real** `src/core/WebPortal.cpp:839` filename lacks Util::safePath check and strips only forward slashes, allows directory traversal via backslashes.
 - **real** `src/core/WebPortal.cpp:856` onDisconnect appends handler per file closing shared req->_tempFile, prevents removal of interrupted temporary files.
 - **real** `src/core/WebPortal.cpp:872` req->_tempObject = malloc(1) overwrites pointer without freeing, leaks memory on multi-file uploads.
 - **real** `src/core/RS485Bus.cpp:90` smallest pendingAt_[i] displaces imminent replies instead of oldest queued, destroys waiting replies before slots arrive.
 - **real** `src/core/RS485Bus.cpp:90` pendingAt_[i] < oldest uses direct unsigned comparison without delta, fails on millis() rollover corrupting queue eviction order.
 - **real** `src/core/WifiLink.h:52` wifilink::decide ignores bestPeerRssi when onRelay is true, traps module on degraded or offline relay access point.

## What each model said

### gemini-3.1-pro-high  _(188.7s, 97186 tokens)_

 - **real** `src/core/RS485Bus.cpp:90` smallest pendingAt_[i] overwrites reply scheduled to fire next, destroying waiting replies before slots arrive. Evict maximum pendingAt_[i].
 - **real** `src/core/RS485Bus.cpp:90` pendingAt_[i] < oldest fails on millis() rollover, corrupting queue eviction order. Cast difference to int32_t.
 - **real** `src/core/WebPortal.cpp:872` req->_tempObject = malloc(1) overwrites pointer without freeing, leaking memory on multi-file uploads.
 - **real** `src/core/WebPortal.cpp:856` onDisconnect appends handler per file; early handlers close shared req->_tempFile, preventing removal of interrupted temporary files.
 - **real** `src/core/WebPortal.cpp:244` pick.feed stores ssid.c_str() from loop-scoped String, leaving wifilink::PeerPick with dangling pointers copying garbage memory.

### gemini-3.7-flash-high  _(199.5s, 303873 tokens)_

 - **real** `src/core/RS485Bus.cpp:90` Smallest pendingAt_[i] displaces reply due soonest instead of oldest queued reply; drops imminent broadcast responses.
 - **real** `src/core/RS485Bus.cpp:90` pendingAt_[i] < oldest uses direct unsigned comparison without delta; breaks displacement logic on millis() overflow.
 - **real** `src/core/WebPortal.cpp:839` filename strips only forward slashes and lacks Util::safePath check; allows directory traversal via backslashes or ..
 - **real** `src/core/WebPortal.cpp:872` req->_tempObject = malloc(1) is never freed by AsyncWebServerRequest destructor; leaks heap memory on every upload.
 - **real** `src/core/WifiLink.h:52` wifilink::decide ignores bestPeerRssi when onRelay is true; traps module on degraded or offline relay access point.
 - **real** `src/core/AudioPlayer.cpp:63` cleanup() deletes file_ outside sd_->lock(); races SPI access with async web server tasks.
 - **real** `src/core/SequencePlayer.cpp:87` router_->module()->busy() lacks null check on module(); crashes if module pointer is null.
