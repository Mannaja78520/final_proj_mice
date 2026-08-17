# ESP32-only sketches

These need real hardware (I2C, encoder, WiFi, motor) and cannot run on a
PC. They were directly in `test/`, where PlatformIO compiles every file
into EVERY test environment — including `native`, which then failed on
`Arduino.h`. Moving them into a folder makes them their own suite that
`test_filter = test_logic` leaves alone.
