#include "core/Perf.h"
#include <esp_system.h>
#include <esp_heap_caps.h>

// Resets since power-on. RTC memory keeps it across a reset and loses it on a
// power cut - same trick as BrownoutGuard, so a board that restarts during a
// task shows boots>1 even when nobody saw it happen.
static const uint32_t MAGIC = 0x50455246UL;   // "PERF"
RTC_NOINIT_ATTR static uint32_t g_magic;
RTC_NOINIT_ATTR static uint32_t g_boots;

static uint32_t passStart, lastStart, passes;
static uint32_t periodMax, workMax, frameMax, frames;
static uint64_t periodSum;
static uint32_t stackMin = UINT32_MAX;
static uint32_t windowStart;
static uint32_t heldMax;
static char heldBy[40] = "-";
static uint32_t partAt, partMax;
static const char* partSlow = "-";

static const char* resetName(esp_reset_reason_t r) {
    switch (r) {
        case ESP_RST_POWERON:   return "poweron";
        case ESP_RST_SW:        return "reboot";
        case ESP_RST_PANIC:     return "CRASH";
        case ESP_RST_INT_WDT:
        case ESP_RST_TASK_WDT:
        case ESP_RST_WDT:       return "WATCHDOG";
        case ESP_RST_BROWNOUT:  return "BROWNOUT";
        case ESP_RST_DEEPSLEEP: return "deepsleep";
        case ESP_RST_EXT:       return "reset-pin";
        default:                return "other";
    }
}

void perf::begin() {
    if (g_magic != MAGIC || esp_reset_reason() == ESP_RST_POWERON) {
        g_magic = MAGIC;
        g_boots = 0;
    }
    g_boots++;
    windowStart = millis();
}

// loop() writes these on core 1 while PERF? reads them from the web task on
// core 0: one short critical section each, never a String inside one.
static portMUX_TYPE mux = portMUX_INITIALIZER_UNLOCKED;

void perf::passBegin() {
    uint32_t now = micros();
    portENTER_CRITICAL(&mux);
    if (passes) {
        uint32_t p = now - lastStart;
        periodSum += p;
        if (p > periodMax) periodMax = p;
    }
    lastStart = passStart = partAt = now;
    passes++;
    portEXIT_CRITICAL(&mux);
}

void perf::passEnd() {
    uint32_t w = micros() - passStart;
    // the loop task's own stack: a small number here is the next crash
    uint32_t s = uxTaskGetStackHighWaterMark(NULL);
    portENTER_CRITICAL(&mux);
    if (w > workMax) workMax = w;
    if (s < stackMin) stackMin = s;
    portEXIT_CRITICAL(&mux);
}

void perf::frame(uint32_t gapMs) {
    portENTER_CRITICAL(&mux);
    frames++;
    if (gapMs > frameMax) frameMax = gapMs;
    portEXIT_CRITICAL(&mux);
}

void perf::part(const char* name) {
    uint32_t now = micros();
    portENTER_CRITICAL(&mux);
    uint32_t us = now - partAt;
    if (us > partMax) { partMax = us; partSlow = name; }
    partAt = now;
    portEXIT_CRITICAL(&mux);
}

void perf::held(uint32_t us, const char* what) {
    if (us <= heldMax) return;   // cheap pre-check; re-checked below
    char by[sizeof(heldBy)];
    snprintf(by, sizeof(by), "%s@%s", what, pcTaskGetName(NULL));
    portENTER_CRITICAL(&mux);
    if (us > heldMax) { heldMax = us; memcpy(heldBy, by, sizeof(heldBy)); }
    portEXIT_CRITICAL(&mux);
}

String perf::report() {
    // snapshot and reset in one step, then format outside the lock
    portENTER_CRITICAL(&mux);
    uint32_t n = passes, fr = frames, pMax = periodMax, wMax = workMax;
    uint32_t fMax = frameMax, hMax = heldMax, ptMax = partMax, sMin = stackMin;
    uint64_t sum = periodSum;
    const char* slow = partSlow;
    char by[sizeof(heldBy)];
    memcpy(by, heldBy, sizeof(by));
    uint32_t since = windowStart;
    passes = frames = 0;
    periodMax = workMax = frameMax = heldMax = partMax = 0;
    strcpy(heldBy, "-");
    partSlow = "-";
    periodSum = 0;
    stackMin = UINT32_MAX;
    windowStart = millis();
    portEXIT_CRITICAL(&mux);

    uint32_t avg = n > 1 ? (uint32_t)(sum / (n - 1)) : 0;
    return "PERF loop_avg_us=" + String(avg) +
        " loop_max_us=" + String(pMax) +
        " work_max_us=" + String(wMax) +
        " passes=" + String(n) +
        " frames=" + String(fr) +
        " frame_max_ms=" + String(fMax) +
        " lock_max_us=" + String(hMax) + " lock_by=" + by +
        " slow_part=" + slow + ":" + String(ptMax) +
        " heap=" + String(ESP.getFreeHeap()) +
        " heap_min=" + String(ESP.getMinFreeHeap()) +
        " heap_big=" + String(heap_caps_get_largest_free_block(MALLOC_CAP_8BIT)) +
        " stack_free=" + String(sMin == UINT32_MAX ? 0 : sMin) +
        " window_ms=" + String(millis() - since) +
        " up_s=" + String(millis() / 1000) +
        " boots=" + String(g_boots) +
        " reset=" + resetName(esp_reset_reason());
}
