/* The smallest valid ESP32 app image that still says something.
 * Used by check_qemu_firmware to prove FWBEGIN/FWDATA/FWEND really switch the
 * boot slot: after the reboot this prints SENTINEL-SLOT-B through the ROM's
 * ets_printf (0x40007d54 on ESP32) and stops. Rebuild: see qc/data/README_sentinel.txt */
typedef int (*pf)(const char *, ...);
__attribute__((section(".text"), used)) static const char msg[] = "SENTINEL-SLOT-B\n";
void __attribute__((noreturn)) _start(void) {
    ((pf)0x40007d54)(msg);
    for (;;) {}
}
