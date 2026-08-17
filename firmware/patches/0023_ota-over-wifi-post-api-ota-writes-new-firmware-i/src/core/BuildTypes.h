#pragma once

// Which module types THIS binary carries.
//
// A board runs one module type, so it should not have to carry the others.
// platformio.ini defines exactly one `MICE_TYPE_*` per env (see the header of
// that file); everything that is per-type — the module classes, their pin
// entries, their web cards, their commands — is behind the macros below.
//
// No flag at all means "carry everything", which is the legacy
// `mice_module_firmware` build. That default is deliberate: a new env, or a
// hand-run compile that forgets the flag, gets the OLD behaviour (too much
// code) rather than a board with no module at all.
//
// The same rule is applied on the PC side by firmware/tools/gen_tables.py,
// which reads these defines and generates the command table and the web page
// for this build only. Keep the two in step: this header decides what
// COMPILES, the generator decides what is GENERATED, and they must agree.

#if !defined(MICE_TYPE_LIFT) && !defined(MICE_TYPE_NONG) && !defined(MICE_TYPE_BLANK)
#define MICE_TYPE_LIFT
#define MICE_TYPE_NONG
#endif

#ifdef MICE_TYPE_LIFT
#define MICE_HAS_LIFT 1
#else
#define MICE_HAS_LIFT 0
#endif

#ifdef MICE_TYPE_NONG
#define MICE_HAS_NONG 1
#else
#define MICE_HAS_NONG 0
#endif
