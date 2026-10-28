#include "core/SequencePlayer.h"
#include "core/CommandRouter.h"
#include "core/Log.h"            // LOGF: the skipped-step trace
#include "core/SDStore.h"
#include "core/SeqSteps.h"
#include <YAMLDuino.h>          // deserializeYml: one step at a time      // generated from config/commands.json
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
    // its own copy: a new FBEGIN/FEND may replace ramYaml_ mid-show
    playText_ = yaml;
    textSrc_.text = playText_.c_str();
    textSrc_.len = playText_.length();
    src_ = &textSrc_;
    return begin_("(memory)", 0, err);
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
    sdSrc_.sd = sd_;
    sdSrc_.path = path;
    src_ = &sdSrc_;
    return begin_(path, depth, err);
}

// Shared by the card and RAM: scan once, read the header, play from step 0.
// The steps themselves are parsed one at a time in loop() (SeqScan.h says why).
bool SequencePlayer::begin_(const String& name, int depth, String& err) {
    std::string header, why;
    if (!scan_.index(*src_, header, why)) {
        err = "cannot read " + name + ": " + why.c_str();
        src_ = nullptr;
        return false;
    }
    if (scan_.count() == 0) {
        err = "no steps in " + name;
        src_ = nullptr;
        return false;
    }
    head_ = new JsonDocument();
    // a file with only `steps:` has no header text, and that is fine
    if (header.find_first_not_of(" \n#") != std::string::npos &&
        !SDStore::parseYaml(String(header.c_str()), *head_)) {
        err = "cannot parse " + name;
        stop();
        return false;
    }
    loopSeq_ = (*head_)["loop"] | false;
    waitUntil_ = millis(); // must be a recent reading for the signed-diff gate
    due_ = waitUntil_;
    waitBusy_ = false;
    file_ = name;
    chain_ = depth;
    running_ = true;
    if (router_->module()) router_->module()->showRunning(true);
    return true;
}

void SequencePlayer::stop() {
    // ramYaml_ deliberately survives: stopping a run does not unload the
    // sequence, so it can be played again without re-sending it.
    running_ = false;
    if (router_ && router_->module()) router_->module()->showRunning(false);
    file_ = "";
    delete head_;
    head_ = nullptr;
    src_ = nullptr;
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
        due_ = millis();           // an untimed step: the clock starts again here
    }
    std::string item;
    bool more = scan_.next(*src_, item);
    if (!more && !scan_.failed() && loopSeq_) {
        scan_.rewind();            // a looping sequence never reaches its end,
        more = scan_.next(*src_, item);   // so "next" only applies when it does
    }
    if (!more && scan_.failed()) {
        LOGF(seq, "read error in %s - stopped", file_.c_str());
        endOfShow();
        return;
    }
    if (!more) {
        // Copy the name BEFORE starting the next file: startAt() calls
        // stop(), which deletes the header this string points into.
        String next = (*head_)["next"] | "";
        int depth = chain_ + 1;
        if (!next.length() || depth >= MAX_CHAIN) { endOfShow(); return; }
        if (!next.startsWith("/")) next = "/moves/" + next;
        String err;
        if (!startAt(next, err, depth)) { endOfShow(); return; }
        return;                    // the next file runs from the following tick
    }
    // One small document for one step, reused: a 447-pose show costs what a
    // 1-pose show costs.
    step_.clear();
    if (deserializeYml(step_, item.c_str())) {
        LOGF(seq, "step not readable in %s - skipped", file_.c_str());
        return;
    }
    execStep(step_[0]);
}

// A real stall (an SD read, a slow WiFi request holding the router lock) is not
// paid back by rushing the moves after it: past CATCH_UP_MS late the clock
// starts again from now. The ordinary few ms of each loop pass are paid back.
void SequencePlayer::catchUp() {
    if ((int32_t)(millis() - due_) > (int32_t)CATCH_UP_MS) due_ = millis();
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
            due_ += (uint32_t)w;          // on the show's clock, not from now
            waitUntil_ = due_;
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
        if (s->wait) catchUp();
        String reply = router_->handleFromSequence(val.length() ? String(s->cmd) + " " + val
                                                                : String(s->cmd));
        if (!s->wait) continue;
        // ONE CLOCK FOR THE WHOLE FILE, as the hub's ShowPlayer keeps. Waiting
        // for busy() to clear started each move one 20 ms frame late, and the
        // lateness added up: a 90.5 s show ran 91.6 s on nong 67 and the song
        // drifted ahead of the arm (user 2026-10-12). A move that says how
        // long it takes (`OK pose T=<ms>ms`, the board's own lengthened time)
        // now ends on a deadline counted from the start, and the next step
        // leaves on that deadline. Anything else still waits for busy().
        // the LAST " T=": a joint reply names the joint first, and "WAIST=90"
        // has a T= of its own
        int at = reply.startsWith("OK") ? reply.lastIndexOf(" T=") : -1;
        long took = at >= 0 ? reply.substring(at + 3).toInt() : 0;
        if (took > 0) {
            due_ += (uint32_t)took;
            waitUntil_ = due_;
        } else {
            waitBusy_ = true;
        }
    }
}
