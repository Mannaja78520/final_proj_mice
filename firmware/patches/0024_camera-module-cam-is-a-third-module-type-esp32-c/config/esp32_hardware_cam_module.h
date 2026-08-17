#pragma once

// ---------------------------------------------------------------------------
// CAM module — AI-Thinker ESP32-CAM (the board with the OV2640 on a ribbon)
// ---------------------------------------------------------------------------
//
// These pins are NOT configurable, and that is deliberate. Every other pin in
// this firmware lives in NVS and is set from the website, because a lift or a
// humanoid is wired by whoever builds it. The camera is not wired by anyone:
// it is etched onto the ESP32-CAM board, and "changing" a camera pin here can
// only ever break the camera. So they are compile-time constants and the pin
// page does not offer them.
//
// What is left over is the reason a camera board can never also be a servo
// board. The camera takes GPIO 0, 5, 18, 19, 21-23, 25-27, 32, 34-36, 39 and
// the on-board SD card takes 2, 4, 12-15. There is nothing left to drive a
// servo with, so `cam` is its own module type rather than an option on
// another one.
//
// GPIO 4 is the white flash LED, and it is shared with the SD card's data
// line — it flickers while the card is written. GPIO 33 is the small red LED
// on the back (inverted: LOW is on).

#define CAM_PWDN_PIN     32
#define CAM_RESET_PIN    -1     // not wired on this board
#define CAM_XCLK_PIN      0
#define CAM_SIOD_PIN     26     // SCCB data  (I2C-like)
#define CAM_SIOC_PIN     27     // SCCB clock
#define CAM_Y9_PIN       35
#define CAM_Y8_PIN       34
#define CAM_Y7_PIN       39
#define CAM_Y6_PIN       36
#define CAM_Y5_PIN       21
#define CAM_Y4_PIN       19
#define CAM_Y3_PIN       18
#define CAM_Y2_PIN        5
#define CAM_VSYNC_PIN    25
#define CAM_HREF_PIN     23
#define CAM_PCLK_PIN     22

#define CAM_FLASH_PIN     4     // white flood LED (shared with SD data)
#define CAM_LED_PIN      33     // small red LED, LOW = on

// The sensor clock. 20 MHz is the usual figure; 10 MHz is kinder to a board on
// a long or thin USB lead, where a browned-out sensor is the classic
// "camera init failed 0x105".
#define CAM_XCLK_HZ 20000000
