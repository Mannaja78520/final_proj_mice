#include "sim/MiceSim.h"
#ifdef MICE_SIM
#include <stdlib.h>

namespace {
constexpr int PINS = 40, CHANS = 16;
int8_t  forcedDigital[PINS];         // -1 = not forced
int16_t forcedAdc[PINS];             // -1 = not forced
uint32_t chanDuty[CHANS];
bool     chanSeen[CHANS];
uint32_t pinDuty[PINS];
bool     pinSeen[PINS];
uint32_t rgbCount = 0;
int16_t  encRaw = 0;                 // what the PCNT (encoder) counter reads
bool     ready = false;

void simInit() {
    if (ready) return;
    for (int i = 0; i < PINS; i++) { forcedDigital[i] = -1; forcedAdc[i] = -1; }
    ready = true;
}
}

namespace micesim {
void rgbShown() { rgbCount++; }

bool handle(const String& line, String& reply) {
    if (!line.length() || line[0] != '~') return false;
    simInit();
    String l = line.substring(1);
    l.trim();
    if (l == "PWM?") {
        reply = "~PWM";
        for (int i = 0; i < CHANS; i++) if (chanSeen[i]) reply += " ch" + String(i) + "=" + String(chanDuty[i]);
        for (int i = 0; i < PINS; i++) if (pinSeen[i]) reply += " pin" + String(i) + "=" + String(pinDuty[i]);
        return true;
    }
    if (l == "PINS?") {                      // what is forced right now
        reply = "~PINS";
        for (int i = 0; i < PINS; i++) if (forcedDigital[i] >= 0) reply += " " + String(i) + "=" + String(forcedDigital[i]);
        return true;
    }
    if (l.startsWith("ENC ")) { encRaw = (int16_t)l.substring(4).toInt(); reply = "~OK"; return true; }
    if (l == "RGB?") { reply = "~RGB shows=" + String(rgbCount); return true; }
    const bool pin = l.startsWith("PIN "), adc = l.startsWith("ADC ");
    if (pin || adc) {
        const int sp = l.indexOf(' ', 4);
        const int g = l.substring(4, sp < 0 ? l.length() : sp).toInt();
        if (g < 0 || g >= PINS || sp < 0) { reply = "~ERR pin"; return true; }
        String v = l.substring(sp + 1);
        v.trim();
        if (pin) forcedDigital[g] = v == "-" ? -1 : (v.toInt() ? 1 : 0);
        else     forcedAdc[g]     = v == "-" ? -1 : (int16_t)constrain(v.toInt(), 0, 4095);
        reply = "~OK";
        return true;
    }
    reply = "~ERR unknown sim command";
    return true;
}
}

// ---- linker wraps: the firmware's own calls land here -------------------
extern "C" {
int  __real_digitalRead(uint8_t pin);
void __real_analogWrite(uint8_t pin, int value);

int __wrap_digitalRead(uint8_t pin) {
    simInit();
    if (pin < PINS && forcedDigital[pin] >= 0) return forcedDigital[pin];
    return __real_digitalRead(pin);
}
// QEMU has no ADC: the real analogRead never finishes. Default = mid-scale.
// QEMU has no pulse counter: the real call fails and logs from a task that holds
// the console lock, which aborts the chip. The encoder reads what ~ENC set.
int __wrap_pcnt_get_counter_value(int unit, int16_t* count) {
    if (count) *count = encRaw;
    return 0;   // ESP_OK
}
int __wrap_analogRead(uint8_t pin) {
    simInit();
    return (pin < PINS && forcedAdc[pin] >= 0) ? forcedAdc[pin] : 2048;
}
void __wrap_ledcWrite(uint8_t chan, uint32_t duty) {
    if (chan < CHANS) { chanSeen[chan] = true; chanDuty[chan] = duty; }
}
void __wrap_analogWrite(uint8_t pin, int value) {
    if (pin < PINS) { pinSeen[pin] = true; pinDuty[pin] = (uint32_t)value; }
}
}
#endif
