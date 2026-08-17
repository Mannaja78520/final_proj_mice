#include "core/HwConfig.h"
#include "core/BuildTypes.h"
#include <config.h>

HwConfig hw;

// key <-> struct field <-> NVS key (<=15 chars) <-> label/group for the web.
// output=true means the pin must drive a signal (input-only 34-39 not allowed).
//
// Only the pins THIS build's module type actually has. A nong has no motor and
// no speaker, so offering to wire them was an invitation to a mistake — and
// every one of those entries was also a PIN key, an NVS slot and a select box
// on the Setup page. The `Pins` struct keeps all its fields (a handful of ints,
// and the defaults stay valid); it is the *configurable* list that shrinks.
struct Field {
    const char* key;
    const char* nvs;
    const char* label;
    const char* group;
    bool output;
};
static const Field FIELDS[] = {
#if MICE_HAS_LIFT
    {"motor_a",   "motora",  "Motor A",       "lift",  true},
    {"motor_b",   "motorb",  "Motor B",       "lift",  true},
    {"motor_pwm", "motorpwm","Motor PWM (-1=none)", "lift", true},
    {"enc_a",     "enca",    "Encoder A",     "lift",  false},
    {"enc_b",     "encb",    "Encoder B",     "lift",  false},
    {"limit_top", "limtop",  "Limit top",     "lift",  false},
    {"limit_down","limdn",   "Limit bottom",  "lift",  false},
#endif
    {"rs485_rx",  "485rx",   "RS485 RX",      "bus",   false},
    {"rs485_tx",  "485tx",   "RS485 TX",      "bus",   true},
    {"rs485_de",  "485de",   "RS485 DE/RE",   "bus",   true},
    {"sd_cs",     "sdcs",    "SD CS",         "sd",    true},
    {"sd_sck",    "sdsck",   "SD SCK",        "sd",    true},
    {"sd_miso",   "sdmiso",  "SD MISO",       "sd",    false},
    {"sd_mosi",   "sdmosi",  "SD MOSI",       "sd",    true},
#if MICE_HAS_LIFT
    {"i2s_bclk",  "i2sbclk", "I2S BCLK",      "audio", true},
    {"i2s_lrc",   "i2slrc",  "I2S LRC",       "audio", true},
    {"i2s_dout",  "i2sdout", "I2S DOUT",      "audio", true},
#endif
#if MICE_HAS_NONG
    {"servo1",    "sv1",     "Nong servo 1 L_SH_P", "nong", true},
    {"servo2",    "sv2",     "Nong servo 2 L_SH_R", "nong", true},
    {"servo3",    "sv3",     "Nong servo 3 L_EL_P", "nong", true},
    {"servo4",    "sv4",     "Nong servo 4 L_EL_R", "nong", true},
    {"servo5",    "sv5",     "Nong servo 5 R_SH_P", "nong", true},
    {"servo6",    "sv6",     "Nong servo 6 R_SH_R", "nong", true},
    {"servo7",    "sv7",     "Nong servo 7 R_EL_P", "nong", true},
    {"servo8",    "sv8",     "Nong servo 8 R_EL_R", "nong", true},
    {"servo9",    "sv9",     "Nong servo 9 WAIST",  "nong", true},
    {"servo10",   "sv10",    "Nong servo 10 SHRUG", "nong", true},
#endif
};
static const int NFIELDS = sizeof(FIELDS) / sizeof(FIELDS[0]);

int* HwConfig::memberFor(const String& key) {
    if (key == "motor_a")   return &pins.motorA;
    if (key == "motor_b")   return &pins.motorB;
    if (key == "motor_pwm") return &pins.motorPwm;
    if (key == "enc_a")     return &pins.encA;
    if (key == "enc_b")     return &pins.encB;
    if (key == "limit_top") return &pins.limitTop;
    if (key == "limit_down")return &pins.limitDown;
    if (key == "rs485_rx")  return &pins.rs485Rx;
    if (key == "rs485_tx")  return &pins.rs485Tx;
    if (key == "rs485_de")  return &pins.rs485De;
    if (key == "sd_cs")     return &pins.sdCs;
    if (key == "sd_sck")    return &pins.sdSck;
    if (key == "sd_miso")   return &pins.sdMiso;
    if (key == "sd_mosi")   return &pins.sdMosi;
    if (key == "i2s_bclk")  return &pins.i2sBclk;
    if (key == "i2s_lrc")   return &pins.i2sLrc;
    if (key == "i2s_dout")  return &pins.i2sDout;
    if (key.startsWith("servo")) {
        int n = key.substring(5).toInt();
        if (n >= 1 && n <= 10) return &pins.servo[n - 1];
    }
    return nullptr;
}

const char* HwConfig::nvsFor(const String& key) {
    for (auto& f : FIELDS) if (key == f.key) return f.nvs;
    return nullptr;
}

void HwConfig::begin() {
    // compile-time defaults from config/esp32_hardware.h
    pins.motorA = MOTOR_IN_A;   pins.motorB = MOTOR_IN_B;   pins.motorPwm = MOTOR_PWM;
    pins.encA = MOTOR_ENCODER_PIN_A; pins.encB = MOTOR_ENCODER_PIN_B;
    pins.limitTop = LIMIT_TOP;  pins.limitDown = LIMIT_DOWN;
    pins.rs485Rx = RS485_RX_PIN; pins.rs485Tx = RS485_TX_PIN; pins.rs485De = RS485_DE_PIN;
    pins.sdCs = SD_CS_PIN; pins.sdSck = SD_SCK_PIN; pins.sdMiso = SD_MISO_PIN; pins.sdMosi = SD_MOSI_PIN;
    pins.i2sBclk = I2S_BCLK_PIN; pins.i2sLrc = I2S_LRC_PIN; pins.i2sDout = I2S_DOUT_PIN;
    const int sv[10] = NONG_SERVO_PINS;
    for (int i = 0; i < 10; i++) pins.servo[i] = sv[i];

    // NVS overrides (whatever was set from the web)
    prefs_.begin("hwpins", false);
    for (auto& f : FIELDS) {
        if (prefs_.isKey(f.nvs)) {
            int* m = memberFor(f.key);
            if (m) *m = prefs_.getInt(f.nvs);
        }
    }
}

bool HwConfig::set(const String& key, int gpio) {
    const char* nvs = nvsFor(key);
    int* m = memberFor(key);
    if (!nvs || !m) return false;
    if (gpio < -1 || gpio > 39) return false;
    if (gpio >= 6 && gpio <= 11) return false; // SPI flash pins — never usable
    prefs_.putInt(nvs, gpio);
    *m = gpio; // struct updated now; hardware re-init happens at reboot
    return true;
}

bool HwConfig::clear(const String& key) {
    const char* nvs = nvsFor(key);
    if (!nvs) return false;
    prefs_.remove(nvs);
    return true;
}

void HwConfig::clearAll() {
    for (auto& f : FIELDS) prefs_.remove(f.nvs);
}

int HwConfig::get(const String& key) const {
    // const access via a non-const helper is fine here (no mutation)
    int* m = const_cast<HwConfig*>(this)->memberFor(key);
    return m ? *m : -2;
}

String HwConfig::listJson() {
    String out = "{";
    bool first = true;
    for (auto& f : FIELDS) {
        int* m = memberFor(f.key);
        if (!m) continue;
        if (!first) out += ",";
        first = false;
        out += "\"" + String(f.key) + "\":{\"gpio\":" + String(*m) +
               ",\"label\":\"" + f.label + "\",\"group\":\"" + f.group +
               "\",\"out\":" + (f.output ? "true" : "false") + "}";
    }
    return out + "}";
}

bool HwConfig::pinUsable(int gpio, bool output) {
    if (gpio == -1) return true;               // disabled
    if (gpio < 0 || gpio > 39) return false;
    if (gpio >= 6 && gpio <= 11) return false; // flash
    if (output && gpio >= 34) return false;    // 34-39 are input-only
    return true;
}

String HwConfig::validPinsJson() {
    // one entry per GPIO with its class + capability notes the web shows:
    //   ok / strap (boot pin, caution) / in (34-39 input-only) /
    //   uart0 (1,3 USB serial console) / flash (6-11, never) / rgb (fixed)
    // note flags: pwm (LEDC output), adc, dac, touch, in (input only).
    String out = "[";
    for (int g = 0; g <= 39; g++) {
        const char* cls = "ok";
        if (g >= 6 && g <= 11) cls = "flash";
        else if (g == 1 || g == 3) cls = "uart0";
        else if (g >= 34) cls = "in";
        else if (g == 0 || g == 2 || g == 5 || g == 12 || g == 15) cls = "strap";
        if (g == RGB_LED_PIN) cls = "rgb";

        String note;
        bool inputOnly = (g >= 34 && g <= 39);
        bool flash = (g >= 6 && g <= 11);
        if (!inputOnly && !flash) note += "pwm ";  // any output = LEDC PWM
        // ADC1: 32-39, ADC2: 0,2,4,12-15,25-27
        if ((g >= 32 && g <= 39) || g == 0 || g == 2 || g == 4 ||
            (g >= 12 && g <= 15) || (g >= 25 && g <= 27)) note += "adc ";
        if (g == 25 || g == 26) note += "dac ";
        if (inputOnly) note += "in-only ";
        note.trim();

        if (g) out += ",";
        out += "{\"g\":" + String(g) + ",\"c\":\"" + cls + "\",\"n\":\"" + note + "\"}";
    }
    return out + "]";
}
