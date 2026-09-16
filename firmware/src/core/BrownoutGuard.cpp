#include "core/BrownoutGuard.h"
#include "core/Log.h"
#include <esp_system.h>

BrownoutGuard brownout;

// Two brownout resets in a row means the supply cannot start this board. One
// can be a stalled servo or a motor's inrush, and punishing that would turn a
// momentary dip into a board with no radio for no reason.
static const uint32_t TRIP_AT = 2;

// RTC memory survives a reset and NOT a power cut, which is exactly the
// lifetime this count wants: the resets being counted keep it, and somebody
// unplugging the board to change its cable clears it. It comes up as rubbish on
// a cold start, so the magic word says whether the count means anything at all.
static const uint32_t MAGIC = 0x42524E4FUL;   // "BRNO"
RTC_NOINIT_ATTR static uint32_t g_magic;
RTC_NOINIT_ATTR static uint32_t g_count;

void BrownoutGuard::begin() {
    esp_reset_reason_t why = esp_reset_reason();
    if (g_magic != MAGIC) {          // cold start: the count is meaningless
        g_magic = MAGIC;
        g_count = 0;
    }
    if (why == ESP_RST_BROWNOUT) {
        g_count++;
    } else if (why == ESP_RST_POWERON) {
        // Somebody has just given it power again - a new cable, a new port, a
        // different supply. Whatever was true before, it gets a clean try.
        g_count = 0;
    }
    // Any OTHER reason (a normal REBOOT, a panic, the watchdog) leaves the
    // count alone rather than clearing it: an update that reboots the board
    // must not hide a supply that has been failing all afternoon.
    count_ = g_count;
    tripped_ = (g_count >= TRIP_AT);
    // "IN A ROW" HAS TO MEAN IN A ROW. Only a power-on cleared this, so one
    // brownout, weeks of perfect running, and one more would turn the radio
    // off - and once tripped it re-tripped at every soft reboot, because a
    // REBOOT or an FWEND keeps the count. See markBooted(), called from
    // main.cpp once the board has actually reached its command loop: a boot
    // that got that far is proof the supply held. Found 2026-08-21.
    if (tripped_) {
        LOGF(boot, "brownout %u times in a row - starting with the radio OFF. "
                   "This is a POWER fault: check the cable, the USB port, or "
                   "feed 5V to VIN. Commands still work on USB and RS485; "
                   "WIFI ON tries the radio again.", (unsigned)g_count);
    } else if (why == ESP_RST_BROWNOUT) {
        LOGF(boot, "that reset was a brownout (%u in a row) - one more and the "
                   "radio stays off so this board can be talked to",
             (unsigned)g_count);
    }
}

String BrownoutGuard::why() const {
    if (!tripped_) return "";
    return "radio off after " + String((unsigned)count_) +
           " brownout resets in a row - a power fault, not a setting. Check the "
           "cable, the USB port, or feed 5V to VIN, then WIFI ON.";
}

void BrownoutGuard::markBooted() {
    // Reached the command loop, so the supply held through the radio starting -
    // which is the only part that was ever in doubt. Clearing here is what
    // makes TRIP_AT mean "in a row" instead of "ever".
    //
    // NOT cleared when tripped: this boot only got here because the radio was
    // left off, which proves nothing about the supply. Clearing it would turn
    // the guard on and off forever, one boot each way.
    if (tripped_) return;
    g_count = 0;
    count_ = 0;
}
