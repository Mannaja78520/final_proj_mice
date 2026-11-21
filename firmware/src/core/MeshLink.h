#pragma once
#include <Arduino.h>
#include <functional>

class Identity;
class CommandRouter;

// ESP-NOW side of the router-less mesh (logic and the frame format: MeshLogic.h).
//
//   MESH                 what it is doing (counters)
//   MESH <id|*> <cmd>    send a command through the mesh; the answer arrives
//                        later as a line "@<id> <reply>" like an RS485 reply
//   SET MESH ON|OFF      stored on the board, off by default
//
// OFF unless asked for: it shares the radio with WiFi (the same channel), so a
// board that is online to a router on channel 6 only meshes with boards on
// channel 6. With no router every board sits on channel 1 and they all hear
// each other. Needs a group (the group key signs every frame). Not testable in
// QEMU (no radio): lab list. Tested as logic on a PC and in tools/bench/mesh_model.py.
class MeshLink {
public:
    static void begin(Identity* id, CommandRouter* router);
    static void loop();                       // from main loop(): start when the radio is up, move frames
    static String command(const String& dst, const String& cmd);   // MESH <dst> <cmd>
    static String status();                   // MESH
    static void onReply(std::function<void(const String&)> cb);   // "@<id> <reply>" lines
    static bool enabled();
};
