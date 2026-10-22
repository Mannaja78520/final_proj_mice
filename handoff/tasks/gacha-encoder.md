# Gachapon: optional motor encoder (stall + smooth stop)

Owner: claude:10qzvx
Updated: 2026-10-22 20:00Z
Branch: claude/project-thread-10qzvx
Last commit: (none yet)
Plan: A47-11

## Goal
CAD (read on the PC 2026-10-23, see gachapon.md): Namiki 22CL-3501PG geared motor WITH an
encoder. Add optional encoder support: pins, counts per pocket, on/off. The hall stays the
source of truth (a pocket = magnet arrivals); the encoder only catches a stall sooner than the
hall timeout and slows the motor just before the last magnet. Do not flash.

## Facts found
- firmware/src/modules/gacha/GachaModule.cpp loop() :70-93: hall arrivals counted, jam = no
  arrival for timeoutMs_; GCFG table :210-250 ([key, field, lo, hi] one line each); cfgJson /
  load / saveCfg mirror the keys. Pure logic in GachaMath.h, native tests in
  firmware/test/test_logic/test_main.cpp:414-455 + RUN_TEST list :529.
- Pins: core/HwConfig.cpp FIELDS has enc_a/enc_b for lift only; Pins.encA/encB exist; default
  MOTOR_ENCODER_PIN_A/B (lift's) - the gacha build must default to -1 (no encoder).
- Module page: WebUI.h GA_CFG table :1103 (one row per GCFG key). Docs: COMMANDS.md:763,
  firmware/config/commands.json:168.

## Doing now
GachaMath EncWatch + slow logic + native tests; GachaModule ISR + GCFG keys; HwConfig pins;
WebUI rows; COMMANDS/commands.json; pio run -e mice_gacha; pio test -e native.

## Done

## Next
1. QC (check names for firmware: tools/systems.py which firmware/src/modules/gacha/...), PR, merge.

## Blocked
- Bench: counts per pocket and the stall time need the real motor (A47-5).
