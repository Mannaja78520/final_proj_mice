#pragma once
#include <Arduino.h>

// A BOARD THAT KEEPS BROWNING OUT SHOULD STOP WALKING INTO THE SAME WALL.
// ======================================================================
// Measured at the bench 2026-08-20, on a 30-pin ESP32: it booted, got as far as
// the SD check, and reset - four brownouts and four boots in eight seconds,
// forever. The radio starting is what tips a marginal supply over, and it starts
// on every boot, so the board never once reached the point where it could be
// talked to. Not over WiFi, obviously. But not over USB or RS485 either, and
// those need no radio at all - the board was unreachable for a reason that had
// nothing to do with how it was being reached.
//
// Nothing in software fixes an undervoltage: that is a cable, a supply or a
// regulator. What software CAN do is stop the board from being inert while
// somebody works out which. After two brownout resets in a row it comes up with
// the radio OFF, which is an existing, supported mode (WebPortal::radioOff),
// answers on USB and RS485 as usual, and says loudly why. `WIFI ON` turns the
// radio back on for anyone who wants to try again.
//
// WHY THE COUNT LIVES IN RTC MEMORY. It has to survive a reset - that is the
// event being counted - but it must NOT survive the power being pulled, because
// pulling the power is exactly what somebody does after changing the cable, and
// they are entitled to a board that tries again. RTC memory is both of those
// things at once. It comes up as rubbish on a cold start, so a magic word says
// whether the count means anything.
//
// TWO, not one. A single brownout can be a one-off - a servo stalling, a
// motor's inrush. Two in a row, with no successful boot between them, is a
// supply that cannot start this board.
class BrownoutGuard {
public:
    // Call FIRST in setup(), before anything draws current.
    void begin();

    // True when the radio should stay off this boot.
    bool tripped() const { return tripped_; }

    // How many brownout resets in a row led here (0 when not tripped).
    uint32_t count() const { return count_; }

    // Call once the board has reached its command loop: the boot worked,
    // so the count of consecutive brownouts starts again.
    void markBooted();

    // One line for a person, or "" when there is nothing to say.
    String why() const;

private:
    bool tripped_ = false;
    uint32_t count_ = 0;
};

extern BrownoutGuard brownout;
