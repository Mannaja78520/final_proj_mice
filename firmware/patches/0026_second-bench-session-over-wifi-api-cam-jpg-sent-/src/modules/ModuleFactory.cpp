#include "modules/ModuleFactory.h"
#include "modules/ModuleTable.h"
#include "modules/Module.h"

// The types are declared in config/modules.json and generated into
// ModuleTable.h at build time (includes + factory, each behind its
// MICE_HAS_<TYPE> guard). Adding a module type does not touch this file.
//
// Only the types THIS binary was built with are in that table. A board carries
// one module type, so the others are not compiled in — which also makes
// `SET TYPE` honest: it can only accept a type this board can actually boot,
// and it says which ones those are.

namespace {

// Fallback when NVS holds a type this build does not have: identity, RS485 and
// the website still work, so the type can be fixed remotely with SET TYPE.
class BlankModule : public Module {
public:
    const char* type() const override { return "blank"; }
};

} // namespace

namespace ModuleFactory {

Module* create(const String& type, SDStore* sd) {
    Module* m = makeModule(type, sd);
    return m ? m : new BlankModule();
}

bool isKnown(const String& type) {
    for (int i = 0; i < MODULE_TYPE_COUNT; i++)
        if (type == MODULE_TYPES[i]) return true;
    return false;
}

String knownTypesCsv() {
    String out;
    for (int i = 0; i < MODULE_TYPE_COUNT; i++) {
        if (out.length()) out += ",";
        out += MODULE_TYPES[i];
    }
    return out;
}

void appendKnownTypes(JsonArray arr) {
    for (int i = 0; i < MODULE_TYPE_COUNT; i++) arr.add(MODULE_TYPES[i]);
}

} // namespace ModuleFactory
