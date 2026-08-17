#include "core/SequencePlayer.h"
#include "core/CommandRouter.h"
#include "core/SDStore.h"
#include "modules/Module.h"

void SequencePlayer::begin(SDStore* sd, CommandRouter* router) {
    sd_ = sd;
    router_ = router;
}

// Parse and play a sequence straight from text. Same player, same steps —
// only the source differs, so chaining, loop and every step key behave
// identically to a file on the card.
bool SequencePlayer::startText(const String& yaml, String& err) {
    stop();
    ramYaml_ = yaml;
    if (!yaml.length()) { err = "no sequence in memory"; return false; }
    doc_ = new JsonDocument();
    if (!SDStore::parseYaml(yaml, *doc_)) {
        err = "cannot parse the sequence";
        stop();
        return false;
    }
    JsonArray steps = (*doc_)["steps"].as<JsonArray>();
    if (steps.isNull() || steps.size() == 0) {
        err = "no steps in the sequence";
        stop();
        return false;
    }
    loopSeq_ = (*doc_)["loop"] | false;
    idx_ = 0;
    waitUntil_ = millis();
    waitBusy_ = false;
    file_ = "(memory)";
    chain_ = 0;
    running_ = true;
    return true;
}

bool SequencePlayer::start(const String& path, String& err) {
    return startAt(path, err, 0);   // a fresh run starts the chain at zero
}

bool SequencePlayer::startAt(const String& path, String& err, int depth) {
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
    chain_ = depth;
    running_ = true;
    return true;
}

void SequencePlayer::stop() {
    // ramYaml_ deliberately survives: stopping a run does not unload the
    // sequence, so it can be played again without re-sending it.
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
        if (loopSeq_) {
            idx_ = 0;              // a looping sequence never reaches its end,
        } else {                   // so "next" only applies when it does
            // Copy the name BEFORE starting the next file: startAt() calls
            // stop(), which deletes the document this string points into.
            String next = (*doc_)["next"] | "";
            int depth = chain_ + 1;
            if (!next.length() || depth >= MAX_CHAIN) { stop(); return; }
            if (!next.startsWith("/")) next = "/moves/" + next;
            String err;
            if (!startAt(next, err, depth)) { stop(); return; }
            return;                // the next file runs from the following tick
        }
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
            router_->handleFromSequence("GOTO " + val);
            waitBusy_ = true;
        } else if (key == "home") {
            router_->handleFromSequence("HOME");
            waitBusy_ = true;
        } else if (key == "up") {
            router_->handleFromSequence("UP");
            waitBusy_ = true; // runs until the top limit switch
        } else if (key == "down") {
            router_->handleFromSequence("DOWN");
            waitBusy_ = true;
        } else if (key == "stop") {
            router_->handleFromSequence("STOP");
        } else if (key == "rgb") {
            router_->handleFromSequence("RGB " + val);
        } else if (key == "effect") {
            router_->handleFromSequence("RGB EFFECT " + val);
        } else if (key == "bright") {
            router_->handleFromSequence("RGB BRIGHT " + val);
        } else if (key == "play") {
            router_->handleFromSequence("PLAY " + val);
        } else if (key == "vol") {
            router_->handleFromSequence("VOL " + val);
        } else if (key == "pose") {
            // nong humanoid: 8 joint angles (+ optional "T <ms>"), e.g.
            //   - pose: "90 45 120 90 90 135 60 90 T 800"
            router_->handleFromSequence("POSE " + val);
            waitBusy_ = true; // waits until the interpolated move finishes
        } else if (key == "joint") {
            router_->handleFromSequence("JOINT " + val);
            waitBusy_ = true;
        } else if (key == "speed") {
            router_->handleFromSequence("SPEED " + val);
        } else if (key == "relax") {
            router_->handleFromSequence("RELAX");
        } else if (key == "attach") {
            router_->handleFromSequence("ATTACH");
        } else if (key == "cmd") {
            router_->handleFromSequence(val);
        }
        // unknown keys are ignored so future modules can extend the format
    }
}
