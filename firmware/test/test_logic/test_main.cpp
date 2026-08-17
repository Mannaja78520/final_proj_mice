// Runs the nong's real arithmetic on a PC — no board, no servos.
//
// These assert BEHAVIOUR, which the source-reading QC checks cannot: that a
// joint angle becomes the right pulse for a given gear and travel, that a move
// is never shorter than the servos can achieve, and that a sequence chain
// cannot run forever. Each one is a bug that was actually hit.
//
//   pio test -e native
#include <unity.h>
#include "modules/nong/NongMath.h"
#include "core/WifiArgs.h"
#include "core/WifiLink.h"

using namespace nongmath;

static const uint32_t MIN_MS = 80;

// ---------------------------------------------------------------- gear maths
// Joint 90 is home and must sit at the MIDDLE of the servo's travel whatever
// that travel is, so swapping a 180 servo for a 270 does not move the arm and
// does not invalidate a single saved pose.
void test_home_is_mid_travel_on_any_servo(void) {
    TEST_ASSERT_EQUAL_INT(1500, jointToUs(90, 180, 1, 1, 0, 500, 2500, false));
    TEST_ASSERT_EQUAL_INT(1500, jointToUs(90, 270, 1, 1, 0, 500, 2500, false));
    TEST_ASSERT_EQUAL_INT(1500, jointToUs(90, 270, 14, 19, 0, 500, 2500, false));
}

// The shoulder case that started the whole calibration hunt: 14:19 through a
// 180 deg sweep must put joint 25..155 across very nearly the full pulse band.
void test_shoulder_14_19_uses_the_whole_band(void) {
    const int lo = jointToUs(25, 180, 14, 19, 0, 500, 2500, false);
    const int hi = jointToUs(155, 180, 14, 19, 0, 500, 2500, false);
    TEST_ASSERT_INT_WITHIN(25, 520, lo);
    TEST_ASSERT_INT_WITHIN(25, 2480, hi);
}

// Same gear on a 270 scale reaches far less of the band — this is exactly why
// a 270 setting made the arm fall short and the gear got faked to compensate.
void test_same_gear_on_270_falls_short(void) {
    const int lo = jointToUs(25, 270, 14, 19, 0, 500, 2500, false);
    TEST_ASSERT_TRUE(lo > 800);          // ~847, nowhere near the 520 it needs
}

// Bigger gear = more servo travel per joint degree. Inverting mirrors about
// the centre and must leave home untouched.
void test_gear_direction_and_invert(void) {
    const int small = jointToUs(120, 180, 1, 1, 0, 500, 2500, false);
    const int big   = jointToUs(120, 180, 14, 19, 0, 500, 2500, false);
    TEST_ASSERT_TRUE(big > small);
    TEST_ASSERT_EQUAL_INT(1500, jointToUs(90, 180, 14, 19, 0, 500, 2500, true));
    const int normal   = jointToUs(120, 180, 1, 1, 0, 500, 2500, false);
    const int inverted = jointToUs(120, 180, 1, 1, 0, 500, 2500, true);
    TEST_ASSERT_EQUAL_INT(3000, normal + inverted);   // mirrored about 1500
}

// A pulse must never leave the configured band, whatever nonsense is asked for.
void test_pulse_never_escapes_the_band(void) {
    for (int j = -400; j <= 400; j += 7) {
        const int us = jointToUs((float)j, 270, 19, 14, 60.0f, 500, 2500, false);
        TEST_ASSERT_TRUE(us >= 500 && us <= 2500);
    }
}

// ---------------------------------------------------------------- move times
// The floor is PER JOINT: the slowest joint on this move decides, not the
// biggest angle. A tiny move of a slow joint can outlast a big move of a fast
// one, and the editor enforces the identical rule.
void test_time_floor_is_per_joint(void) {
    float from[3] = {90, 90, 90};
    float to[3]   = {90, 90, 120};
    float fast[3] = {400, 400, 400};
    float slow[3] = {400, 400, 30};      // joint 3 is the slow one
    TEST_ASSERT_EQUAL_UINT32(75 > MIN_MS ? 75 : MIN_MS,
                             minDuration(from, to, fast, 3, MIN_MS));
    TEST_ASSERT_EQUAL_UINT32(1000, minDuration(from, to, slow, 3, MIN_MS));
}

void test_time_never_below_the_minimum(void) {
    float from[2] = {90, 90};
    float to[2]   = {90.2f, 90};
    float dps[2]  = {400, 400};
    TEST_ASSERT_EQUAL_UINT32(MIN_MS, minDuration(from, to, dps, 2, MIN_MS));
    TEST_ASSERT_EQUAL_UINT32(MIN_MS, durationFor(from, to, 2, 120.0f, MIN_MS));
}

// Show speed sets the requested time; halving the speed doubles it.
void test_duration_scales_with_speed(void) {
    float from[1] = {90};
    float to[1]   = {150};               // 60 deg
    TEST_ASSERT_EQUAL_UINT32(500,  durationFor(from, to, 1, 120.0f, MIN_MS));
    TEST_ASSERT_EQUAL_UINT32(1000, durationFor(from, to, 1, 60.0f,  MIN_MS));
}

// A zero or silly speed must not divide by zero or return garbage.
void test_bad_speed_is_survivable(void) {
    float from[1] = {90};
    float to[1]   = {150};
    TEST_ASSERT_TRUE(durationFor(from, to, 1, 0.0f, MIN_MS) >= MIN_MS);
    float dps[1] = {0};
    TEST_ASSERT_TRUE(minDuration(from, to, dps, 1, MIN_MS) >= MIN_MS);
}

// ---------------------------------------------------------------- easing
void test_ease_is_smooth_and_bounded(void) {
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 0.0f, ease(0.0f));
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 0.5f, ease(0.5f));
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 1.0f, ease(1.0f));
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 0.0f, ease(-3.0f));   // clamped
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 1.0f, ease(9.0f));
    float prev = -1.0f;                                     // monotonic
    for (float t = 0.0f; t <= 1.0f; t += 0.05f) {
        const float e = ease(t);
        TEST_ASSERT_TRUE(e >= prev - 0.0001f);
        prev = e;
    }
}

// ------------------------------------------------------------ SET WIFI args
// Both of these were found by flashing a board and watching it refuse to join
// a network that was working. Neither crashes; both just quietly never
// connect, and both read back looking exactly right.

// "MSI 3058" is one network name, not an ssid and a password.
void test_quoted_ssid_keeps_its_spaces(void) {
    std::string ssid, pass;
    TEST_ASSERT_TRUE(wifiargs::parse("\"MSI 3058\" mypass", ssid, pass));
    TEST_ASSERT_EQUAL_STRING("MSI 3058", ssid.c_str());
    TEST_ASSERT_EQUAL_STRING("mypass", pass.c_str());
}

// THE one that cost an afternoon on the bench: quoting the password too
// stored the quote characters as part of it.
void test_quoted_password_loses_its_quotes(void) {
    std::string ssid, pass;
    TEST_ASSERT_TRUE(wifiargs::parse("\"manny\" \"qwertyui\"", ssid, pass));
    TEST_ASSERT_EQUAL_STRING("manny", ssid.c_str());
    TEST_ASSERT_EQUAL_STRING("qwertyui", pass.c_str());
}

void test_unquoted_still_works(void) {
    std::string ssid, pass;
    TEST_ASSERT_TRUE(wifiargs::parse("homewifi secret123", ssid, pass));
    TEST_ASSERT_EQUAL_STRING("homewifi", ssid.c_str());
    TEST_ASSERT_EQUAL_STRING("secret123", pass.c_str());
}

// An open network has no password, and a password may itself hold spaces.
void test_open_network_and_spaced_password(void) {
    std::string ssid, pass;
    TEST_ASSERT_TRUE(wifiargs::parse("guestnet", ssid, pass));
    TEST_ASSERT_EQUAL_STRING("", pass.c_str());
    TEST_ASSERT_TRUE(wifiargs::parse("\"my net\" \"two words\"", ssid, pass));
    TEST_ASSERT_EQUAL_STRING("two words", pass.c_str());
}

void test_rubbish_is_rejected(void) {
    std::string ssid, pass;
    TEST_ASSERT_FALSE(wifiargs::parse("", ssid, pass));
    TEST_ASSERT_FALSE(wifiargs::parse("   ", ssid, pass));
    TEST_ASSERT_FALSE(wifiargs::parse("\"unclosed", ssid, pass));
}

// ------------------------------------------------- which WiFi to be on
// You cannot make a real -80 dBm signal appear on a bench, and this is the
// behaviour that only matters in a big venue - so it is decided by a pure
// function and proved here instead.
using namespace wifilink;

void test_a_good_link_is_left_alone(void) {
    TEST_ASSERT_EQUAL_INT(STAY, decide(false, -50, -40));   // peer stronger, but we are fine
    TEST_ASSERT_EQUAL_INT(STAY, decide(false, -67, -30));
}

// The whole point: a link can be connected AND too weak to run a show on.
void test_a_weak_link_moves_to_a_stronger_neighbour(void) {
    TEST_ASSERT_EQUAL_INT(RELAY, decide(false, -85, -45));
    TEST_ASSERT_EQUAL_INT(RELAY, decide(false, 0, -60));    // main not visible at all
}

// ...but only if the neighbour is actually better. Swapping a bad link for
// an equally bad one just costs a disconnection.
void test_no_move_to_an_equally_bad_neighbour(void) {
    TEST_ASSERT_EQUAL_INT(STAY, decide(false, -85, -80));   // only 5 dB better
    TEST_ASSERT_EQUAL_INT(STAY, decide(false, -85, -90));   // worse
    TEST_ASSERT_EQUAL_INT(STAY, decide(false, -85, 0));     // no neighbour at all
}

// THE ONE THAT MATTERS: no flapping. A module sitting near the threshold must
// not swap networks forever - every swap drops the link for a second, which at
// a show looks like the robot randomly freezing.
void test_it_cannot_flap(void) {
    // weak enough to leave...
    TEST_ASSERT_EQUAL_INT(RELAY, decide(false, -80, -50));
    // ...and once relaying, that same -80 is NOT good enough to go back
    TEST_ASSERT_EQUAL_INT(STAY, decide(true, -80, -50));
    // there must be a real gap between the two thresholds
    TEST_ASSERT_TRUE(GOOD_RSSI > WEAK_RSSI);
}

void test_it_returns_when_the_network_is_properly_back(void) {
    TEST_ASSERT_EQUAL_INT(RETURN, decide(true, -50, -40));
    TEST_ASSERT_EQUAL_INT(STAY, decide(true, 0, -40));      // main gone: stay put
}

// Unity calls these around every test. Nothing here holds state — every
// function under test is pure — so they are deliberately empty.
void setUp(void) {}
void tearDown(void) {}

int main(int, char **) {
    UNITY_BEGIN();
    RUN_TEST(test_home_is_mid_travel_on_any_servo);
    RUN_TEST(test_shoulder_14_19_uses_the_whole_band);
    RUN_TEST(test_same_gear_on_270_falls_short);
    RUN_TEST(test_gear_direction_and_invert);
    RUN_TEST(test_pulse_never_escapes_the_band);
    RUN_TEST(test_time_floor_is_per_joint);
    RUN_TEST(test_time_never_below_the_minimum);
    RUN_TEST(test_duration_scales_with_speed);
    RUN_TEST(test_bad_speed_is_survivable);
    RUN_TEST(test_ease_is_smooth_and_bounded);
    RUN_TEST(test_quoted_ssid_keeps_its_spaces);
    RUN_TEST(test_quoted_password_loses_its_quotes);
    RUN_TEST(test_unquoted_still_works);
    RUN_TEST(test_open_network_and_spaced_password);
    RUN_TEST(test_rubbish_is_rejected);
    RUN_TEST(test_a_good_link_is_left_alone);
    RUN_TEST(test_a_weak_link_moves_to_a_stronger_neighbour);
    RUN_TEST(test_no_move_to_an_equally_bad_neighbour);
    RUN_TEST(test_it_cannot_flap);
    RUN_TEST(test_it_returns_when_the_network_is_properly_back);
    return UNITY_END();
}
