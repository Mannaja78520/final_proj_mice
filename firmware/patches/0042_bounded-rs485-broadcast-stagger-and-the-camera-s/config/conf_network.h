/**
 * @file conf_network.h
 * @brief Default network parameters. WiFi credentials can be overridden at
 *        runtime (SET WIFI <ssid> <pass>) and are then stored in NVS.
 */
#ifndef CONF_NETWORK_H
#define CONF_NETWORK_H

#include <Arduino.h>

//---- Wi-Fi (defaults, used when nothing is stored in NVS) ----
static const char* WIFI_SSID = "manny";
static const char* WIFI_PASS = "qwertyui";

// If STA connect fails, the module opens its own AP "MOD-<id>-<name>"
static const char* AP_FALLBACK_PASS = "12345678";
#define WIFI_CONNECT_TIMEOUT_MS 15000

#endif
