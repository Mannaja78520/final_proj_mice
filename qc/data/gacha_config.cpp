// Inserted after the fake IO and actual production GCFG/HOME methods.
// These cases exercise configuration commits, including rejected transactions.
class GachaConfigChecks {
public:
    static void run() {
        struct Change { const char* key; const char* value; };
        for (const auto c : {Change{"slots", "1"}, Change{"magnets", "8"}, Change{"dir", "-1"}}) {
            GachaModule m; String reply, args[] = {"GCFG", c.key, c.value};
            m.pos_ = 3; m.hall_.feed(true, 17, 5);
            m.config(args, 3, reply);
            check(reply.rfind("OK ", 0) == 0 && m.saves == 1, "valid reference configuration commits through GCFG");
            check(!m.posKnown_ && m.pos_ == 0 && m.pos_ < m.slots_,
                  "accepted layout or direction change cannot retain an old pocket reference");
            check(m.stock_ == 7 && m.given_ == 4 && m.hits_ == 0,
                  "reference invalidation does not change prize or magnet counts");
            m.home(reply);
            check(m.posKnown_ && m.pos_ == 0 && m.pos_ < m.slots_,
                  "GHOME can establish a fresh valid reference after a layout change");
        }
        for (const auto c : {Change{"slots", "3"}, Change{"magnets", "6"}, Change{"active_low", "2"}}) {
            GachaModule m; String reply, args[] = {"GCFG", c.key, c.value};
            m.pos_ = 3; m.hall_.feed(true, 17, 5);
            m.config(args, 3, reply);
            check(reply.rfind("ERR ", 0) == 0 && m.saves == 0 && m.slots_ == 4 && m.magnets_ == 4,
                  "rejected bounds or fractional layout does not persist a partial configuration");
            check(m.posKnown_ && m.pos_ == 3 && m.hall_.primed && m.hall_.stable && m.hall_.rawSince == 17,
                  "rejected GCFG preserves the existing logical and Hall reference");
        }
        for (const auto c : {Change{"slots", "4"}, Change{"speed", "600"}}) {
            GachaModule m; String reply, args[] = {"GCFG", c.key, c.value};
            m.pos_ = 3; m.hall_.feed(true, 17, 5);
            m.config(args, 3, reply);
            check(reply.rfind("OK ", 0) == 0 && m.posKnown_ && m.pos_ == 3 && m.hall_.stable,
                  "unchanged layout or non-reference setting preserves a valid reference");
        }
        {
            GachaModule m; String reply, args[] = {"GCFG", "active_low", "0"};
            m.pos_ = 3; m.activeLow_ = true; m.hall_.feed(true, 17, 5);
            m.config(args, 3, reply);
            check(reply == "OK active_low=0" && !m.activeLow_ && !m.posKnown_ && m.pos_ == 0,
                  "polarity change invalidates the logical reference");
            check(!m.hall_.primed && !m.hall_.stable && !m.hall_.raw,
                  "polarity change discards the old-polarity debounced Hall state");
            m.home(reply);
            check(reply == "OK finding the next magnet" && m.state_ == GachaModule::HOMING && !m.posKnown_,
                  "immediate GHOME cannot reuse stale Hall after polarity change");
            tick(m, 30, false);
            check(m.hall_.primed && !m.hall_.stable && m.got_ == 0 && m.hits_ == 0,
                  "fresh Hall priming after polarity change cannot invent a magnet arrival");
            m.stop(reply);
        }
        {
            GachaModule m; String reply, args[] = {"GCFG", "CLEAR"}; removedCfg = 0;
            m.magnets_ = 8; m.slots_ = 2; m.dir_ = -1; m.activeLow_ = false;
            m.pos_ = 1; m.hall_.feed(true, 17, 5);
            m.config(args, 2, reply);
            check(reply == "OK settings back to defaults" && removedCfg == 1 && m.saves == 1 &&
                  m.magnets_ == GACHA_MAGNETS && m.slots_ == GACHA_SLOTS && m.dir_ == 1,
                  "actual GCFG CLEAR restores and persists the default layout");
            check(!m.posKnown_ && m.pos_ == 0 && !m.hall_.primed && !m.hall_.stable,
                  "actual GCFG CLEAR invalidates position and stale sensor reference");
            check(m.stock_ == 7 && m.given_ == 4 && m.hits_ == 0,
                  "actual GCFG CLEAR preserves prize and lifetime counts");
        }
        for (bool clear : {false, true}) {
            GachaModule m; String reply, args[] = {"GCFG", clear ? "CLEAR" : "slots", "1"};
            m.state_ = GachaModule::TURNING; m.pos_ = 3; m.hall_.feed(true, 17, 5);
            m.config(args, clear ? 2 : 3, reply);
            check(reply == "ERR busy" && m.saves == 0 && m.slots_ == 4 && m.posKnown_ && m.pos_ == 3 && m.hall_.stable,
                  "busy configuration or CLEAR leaves the active job reference unchanged");
        }
    }
};
