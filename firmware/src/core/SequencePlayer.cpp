#include "core/SequencePlayer.h"
#include "core/CommandRouter.h"
#include "core/Log.h"            // LOGF: the skipped-step trace
#include "core/SDStore.h"
#include "core/SeqSteps.h"      // generated from config/commands.json
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

// The show reached its own end. MOVE STOP silences everything; this path must
// only end a track told to REPEAT, because a one-shot outliving a short show is
// deliberate. Not folded into stop(): stop() is also the failure path and the
// unload path, and neither should touch sound.
void SequencePlayer::endOfShow() {
    Module* m = router_->module();
    if (m) m->silenceLoop();
    stop();
}

void SequencePlayer::loop() {
    if (!running_) return;
    if ((int32_t)(millis() - waitUntil_) < 0) return;
    if (waitBusy_) {
        Module* m = router_->module();
        if (m && m->busy()) return;   // a board with no module is never busy
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
            if (!next.length() || depth >= MAX_CHAIN) { endOfShow(); return; }
            if (!next.startsWith("/")) next = "/moves/" + next;
            String err;
            if (!startAt(next, err, depth)) { endOfShow(); return; }
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
        } else if (v.is<bool>()) {
            // "- home: true" is YAML for DO IT, not an argument. Flattened as
            // a string it appended the word: "HOME true".
            val = "";
        } else {
            val = v.as<String>();
        }

        // Two keys are not commands, so they cannot come from the table:
        // `wait` is a timer here, and `cmd` is whatever the file says.
        if (key == "wait") {
            long w = v.as<long>();
            if (w < 0) w = 0;   // negative would wrap to ~49 days and stall
            waitUntil_ = millis() + (uint32_t)w;
            continue;
        }
        if (key == "cmd") {
            router_->handleFromSequence(val);
            continue;
        }
        // Everything else is declared on the command it calls
        // (config/commands.json -> SeqSteps.h), so a new step key is one
        // entry there and this file never learns another module's verbs.
        const SeqStepDoc* s = findSeqStep(key);
        if (!s) {
            // Still skipped - a file written for another module type must
            // play what it can - but never silently: a typo'd step ("got:"
            // for "goto:") otherwise just vanishes from the show.
            LOGF(seq, "step key '%s' is not known to this board - skipped",
                 key.c_str());
            continue;
        }
        router_->handleFromSequence(val.length() ? String(s->cmd) + " " + val
                                                 : String(s->cmd));
        if (s->wait) waitBusy_ = true;
    }
}
