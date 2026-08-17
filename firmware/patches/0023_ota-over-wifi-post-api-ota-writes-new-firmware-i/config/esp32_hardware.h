#ifndef ESP32_HARDWARE_H
#define ESP32_HARDWARE_H

    // ================= Shared / core hardware (all module types) =================
    // Per-hardware-module defines live in their own files, included at the
    // bottom of this one (still one firmware binary — the module type is
    // chosen at runtime, so every type's config must be visible at compile
    // time). All PIN defaults here are overridable per-board from the web
    // (Hardware pins card / PIN command; stored in the board's NVS).
    //   config/esp32_hardware_lift_module.h   — lift motor/encoder/limits/rack
    //   config/esp32_hardware_nong_module.h   — nong servos/limits/gear

    #define FW_VERSION "1.0.0"

    // Microcontroller PWM (motor + shared)
    #define PWM_BITS 10                                                     // PWM Resolution of the microcontroller
    #define PWM_FREQUENCY 20000                                             // PWM Frequency
    #define PWM_Max 1023
    #define PWM_Min PWM_Max * -1

    // ================= Bus / peripheral pin map (38-pin ESP32 DevKit) =================
    // Used: 2,4,5,13,14,16,17,18,19,21,22,23,25,26,27,32,33
    // Free for future sensors: 34,35,36,39 (input only, no internal pullup), 15.
    // GPIO12 is the MTDI flash-voltage strap: it must be LOW/floating at reset,
    // never wire anything with a pull-up to it or the board won't boot.

    // RS485 transceiver on UART2. DE and /RE tied together on RS485_DE_PIN.
    #define RS485_RX_PIN 16
    #define RS485_TX_PIN 17
    #define RS485_DE_PIN 4
    #define RS485_BAUD   115200

    // microSD card on VSPI
    #define SD_CS_PIN   5
    #define SD_SCK_PIN  18
    #define SD_MISO_PIN 19
    #define SD_MOSI_PIN 23

    // NOTE: the RGB strip and the I2S speaker (AMP) are LIFT-ONLY hardware —
    // their pins live in esp32_hardware_lift_module.h, not here. Only RS485
    // and the SD card are shared by every module type.

    // ---- per-hardware-module config ----
    #include "esp32_hardware_lift_module.h"
    #include "esp32_hardware_nong_module.h"

#endif
