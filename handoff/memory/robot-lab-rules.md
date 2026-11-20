---
name: robot-lab-rules
description: Hardware and lab rules for robot work
metadata:
  type: project
---

Robot tests happen only in a lab session (lab until 21:00 Thai time). Never wait for or ask for a robot test mid-task; collect board tests for ONE later lab session (handoff/tasks/lab-day.md). Almost nothing is tested on real hardware: say tested against fakes plainly. Never change rig axes, senses, zero, home or servo numbers; never edit URDF/SolidWorks originals.

**Why:** the lab is not always available; a blocked thread wastes the day.
**How to apply:** build against fakes, list the real test in the lab file.
