#include "core/SequencePlayer.h"
#include "core/CommandRouter.h"
#include "core/SDStore.h"
#include "modules/Module.h"

void SequencePlayer::begin(SDStore* sd, CommandRouter* router) {
    sd_ = sd;
    router_ = router;
}

bool SequencePlayer::start(const String& path, String& err) {
    stop();
    if (!sd_ || !sd_->available()) {
        err = "no sd card";
        return false;
    }
    doc_ = new JsonDocument();
    if (!sd_->loadYaml(path.c_str(), *doc_)) {
        err = "cannot read/parse " + path;
        stop();
        return false;
    }
    JsonArray steps = (*doc_)["steps"].as<JsonArray>();
    if (steps.isNull() || steps.size() == 0) {
        err = "no steps in " + path;
        stop();
        return false;
    }
    loopSeq_ = (*doc_)["loop"] | false;
    idx_ = 0;
    waitUntil_ = millis(); // must be a recent reading for the signed-diff gate
    waitBusy_ = false;
    file_ = path;
    running_ = true;
    return true;
}

void SequencePlayer::stop() {
    running_ = false;
    file_ = "";
    delete doc_;
    doc_ = nullptr;
}

void SequencePlayer::loop() {
    if (!running_) return;
    if ((int32_t)(millis() - waitUntil_) < 0) return;
    if (waitBusy_) {
        if (router_->module()->busy()) return;
        waitBusy_ = false;
    }
    JsonArray steps = (*doc_)["steps"].as<JsonArray>();
    if (idx_ >= steps.size()) {
        if (loopSeq_) idx_ = 0;
        else { stop(); return; }
    }
    execStep(steps[idx_++]);
}

void SequencePlayer::execStep(JsonVariant step) {
    if (!step.is<JsonObject>()) return;
    for (JsonPair kv : step.as<JsonObject>()) {
        String key = kv.key().c_str();
        key.toLowerCase();
        JsonVariant v = kv.value();

        // value as string, also flattening [255,0,0] -> "255 0 0"
        String val;
        if (v.is<JsonArray>()) {
            for (JsonVariant e : v.as<JsonArray>()) {
                if (val.length()) val += ' ';
                val += e.as<String>();
            }
        } else {
            val = v.as<String>();
        }

        if (key == "wait") {
            waitUntil_ = millis() + (uint32_t)v.as<long>();
        } else if (key == "goto") {
            router_->handle("GOTO " + val);
            waitBusy_ = true;
        } else if (key == "home") {
            router_->handle("HOME");
            waitBusy_ = true;
        } else if (key == "up") {
            router_->handle("UP");
            waitBusy_ = true; // runs until the top limit switch
        } else if (key == "down") {
            router_->handle("DOWN");
            waitBusy_ = true;
        } else if (key == "stop") {
            router_->handle("STOP");
        } else if (key == "rgb") {
            router_->handle("RGB " + val);
        } else if (key == "effect") {
            router_->handle("RGB EFFECT " + val);
        } else if (key == "bright") {
            router_->handle("RGB BRIGHT " + val);
        } else if (key == "play") {
            router_->handle("PLAY " + val);
        } else if (key == "vol") {
            router_->handle("VOL " + val);
        } else if (key == "pose") {
            // nong humanoid: 8 joint angles (+ optional "T <ms>"), e.g.
            //   - pose: "90 45 120 90 90 135 60 90 T 800"
            router_->handle("POSE " + val);
            waitBusy_ = true; // waits until the interpolated move finishes
        } else if (key == "joint") {
            router_->handle("JOINT " + val);
            waitBusy_ = true;
        } else if (key == "speed") {
            router_->handle("SPEED " + val);
        } else if (key == "relax") {
            router_->handle("RELAX");
        } else if (key == "attach") {
            router_->handle("ATTACH");
        } else if (key == "cmd") {
            router_->handle(val);
        }
        // unknown keys are ignored so future modules can extend the format
    }
}
