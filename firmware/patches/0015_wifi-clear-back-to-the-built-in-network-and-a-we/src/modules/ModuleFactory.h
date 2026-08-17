#pragma once
#include <Arduino.h>
#include <ArduinoJson.h>

class Module;
class SDStore;

// Creates the Module implementation for the type stored in NVS.
// To add a new module type: implement Module in src/modules/<type>/,
// then register it in ModuleFactory.cpp (create + KNOWN_TYPES).
namespace ModuleFactory {
    Module* create(const String& type, SDStore* sd);
    bool isKnown(const String& type);
    String knownTypesCsv();
    void appendKnownTypes(JsonArray arr);
}
