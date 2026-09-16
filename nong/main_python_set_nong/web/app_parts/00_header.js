/* Nong Studio — pose & keyframe editor for the nong humanoid.
 *
 * The robot: upper body, 2 arms, no fingers. Each arm has a universal joint
 * in the shoulder and one in the elbow; every universal joint is built from
 * 2 MG90S servos => 8 logical joints, same order as the firmware
 * (code/firmware/src/modules/nong/NongModule.h):
 *   1 L_SH_P  2 L_SH_R  3 L_EL_P  4 L_EL_R  5 R_SH_P  6 R_SH_R  7 R_EL_P  8 R_EL_R
 * Angles are JOINT degrees (the physical joint angle), neutral 90, clamped to
 * each joint's [min,max] (a 2-servo universal joint can't reach 0..180).
 * The reduction gear (pinion:gear, e.g. 12:13) is applied ON THE ROBOT
 * (firmware converts joint->servo); the editor and commands stay in joint deg.
 * Each joint's rotation axis (roll X / pitch Y / yaw Z) is editable in Rig setup.
 */
"use strict";

const $ = (id) => document.getElementById(id);

// sidebar tabs: Movement (posing/robot, the main one) and Setup (rig + model)
// Four task tabs instead of Movement/Setup. Cards carry data-stab and are
// shown by it, so NOTHING moved in the DOM — every id, handler and QC driver
// works exactly as before, and only what is on screen at once changed.
// "move" is still accepted so any older link or habit keeps working.
const STAB_BTN = { pose: "tabBtnMove", sequence: "tabBtnSeq",
                   robot: "tabBtnRobot", setup: "tabBtnSetup" };
let sideTab = "pose";