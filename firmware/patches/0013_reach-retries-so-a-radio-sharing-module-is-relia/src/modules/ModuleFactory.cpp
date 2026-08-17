#include "modules/ModuleFactory.h"
#include "modules/Module.h"
#include "modules/lift/LiftModule.h"
#include "modules/nong/NongModule.h"

namespace {

// Fallback when NVS holds an unknown type: identity/RS485/web still work,
// so the type can be fixed remotely with SET TYPE.
class BlankModule : public Module {
public:
    const char* type() const override { return "blank"; }
};

const char* KNOWN_TYPES[] = {"lift", "nong", "blank"};

} // namespace

namespace ModuleFactory {

Module* create(const String& type, SDStore* sd) {
    if (type == "lift") return new LiftModule(sd);
    if (type == "nong") return new NongModule(sd);
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
