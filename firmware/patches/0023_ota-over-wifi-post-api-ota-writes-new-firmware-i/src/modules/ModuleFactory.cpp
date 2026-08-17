#include "modules/ModuleFactory.h"
#include "core/BuildTypes.h"
#include "modules/Module.h"
#if MICE_HAS_LIFT
#include "modules/lift/LiftModule.h"
#endif
#if MICE_HAS_NONG
#include "modules/nong/NongModule.h"
#endif

// Only the types THIS binary was built with (see src/core/BuildTypes.h and the
// header of platformio.ini). A board carries one module type, so the others
// are not compiled in — which also makes `SET TYPE` honest: it can only accept
// a type this board can actually boot, and it says which ones those are.

namespace {

// Fallback when NVS holds an unknown type: identity/RS485/web still work,
// so the type can be fixed remotely with SET TYPE.
class BlankModule : public Module {
public:
    const char* type() const override { return "blank"; }
};

const char* KNOWN_TYPES[] = {
#if MICE_HAS_LIFT
    "lift",
#endif
#if MICE_HAS_NONG
    "nong",
#endif
    "blank"};

} // namespace

namespace ModuleFactory {

Module* create(const String& type, SDStore* sd) {
#if MICE_HAS_LIFT
    if (type == "lift") return new LiftModule(sd);
#endif
#if MICE_HAS_NONG
    if (type == "nong") return new NongModule(sd);
#endif
    (void)sd;
    return new BlankModule();
}

bool isKnown(const String& type) {
    for (auto t : KNOWN_TYPES)
        if (type == t) return true;
    return false;
}

String knownTypesCsv() {
    String out;
    for (auto t : KNOWN_TYPES) {
        if (out.length()) out += ",";
        out += t;
    }
    return out;
}

void appendKnownTypes(JsonArray arr) {
    for (auto t : KNOWN_TYPES) arr.add(t);
}

} // namespace ModuleFactory
