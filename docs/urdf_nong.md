# The nong as a URDF — what to build in SolidWorks, and why each number is what it is

Written for whoever runs the **sw2urdf** add-in on `nong_assembly.SLDASM`
(`E:\final_proj\mice\model\21_09_2026_nangrum_full\`), and for the next session
that picks this up. Asked by the user on 2026-09-23: *first of all you open my
solidwork and make the geomatry for me too and then export to urdf i already
have that addin*, and *make show urdf look like in nong studio too*.

Another session (`claude:09230033-96eb`) had SolidWorks open on these same files
for the structural studies, and two sessions holding one assembly is how work
gets lost — so this is the table first, the export second.

**You may not need SolidWorks at all.** Every number sw2urdf would ask for is
already measured, in `nong/main_python_set_nong/rig_default.json`, which came
from `nong_assembly.STEP`. So:

```
python tools/make_urdf.py
```

writes the whole file — tree, origins, axes, limits — straight from the rig, in
one command, and re-writes it whenever the rig changes. What it *cannot* write
is the meshes: a URDF names them, it does not carry them. Export one STL per
body part from SolidWorks (six files) and either drop them in
`nong/main_python_set_nong/models/` as `torso.stl`, `head.stl`, `L_upper.stl`,
`L_fore.stl`, `R_upper.stl`, `R_fore.stl`, or name them with `--meshes`. A part
with no mesh is written as a link with no `<visual>`, which Studio lists and
skips rather than drawing an empty body.

Use the full sw2urdf wizard below instead when you want the meshes and the
joint frames to come from the CAD itself rather than from the measured rig —
they should agree, and if they do not, the CAD is right and the rig needs
re-measuring.

---

## 1. What this gets you

Nong Studio can already read a URDF (Setup ▸ **Build it from a URDF**). It takes
from the file the four things an STL does not carry:

* where each part sits,
* which way it is turned,
* how big it is,
* which part hangs off which.

Today every STL dragged into Studio lands at the middle of the robot and has to
be rotated, offset and scaled by hand until it looks right. With a URDF none of
that is typed. That is the whole reason for doing this.

So the export is judged by one test: **import it into Studio and the nong looks
like the nong.** Not "the file validates".

---

## 2. The link tree

Eleven links, ten joints — the same ten joints the firmware drives, in the same
order (`firmware/src/modules/nong/NongModule.h`).

```
base_link                     the hanging bar / body_shaft
└── waist_link                WAIST      (joint 9)
    └── shrug_link            SHRUG      (joint 10)  the see-saw shoulder bar
        ├── L_upper_link      L_SH_P (1) → L_SH_R (2)
        │   └── L_fore_link   L_EL_P (3) → L_EL_R (4)
        ├── R_upper_link      R_SH_P (5) → R_SH_R (6)
        │   └── R_fore_link   R_EL_P (7) → R_EL_R (8)
        └── head_link         fixed
```

A shoulder and an elbow are each a **universal joint built from two servos**, so
each one is two URDF revolute joints stacked at the same origin with a
zero-length link between them. sw2urdf makes you name that middle link; call
them `L_sh_mid`, `L_el_mid`, `R_sh_mid`, `R_el_mid` and give them no mesh.
Studio ignores a link with no mesh, so they cost nothing there.

### Name the links exactly like this

Studio guesses which link is which body part from its name
(`URDF_GUESS` in `nong/main_python_set_nong/web/app_parts/urdf_import.js`).
The names above are already what it looks for, so a correct export needs no
correcting by hand:

| link | Studio part |
|---|---|
| `torso_link` *(or `base_link`)* | `torso` |
| `head_link` | `head` |
| `L_upper_link` | `L_upper` |
| `L_fore_link` | `L_fore` |
| `R_upper_link` | `R_upper` |
| `R_fore_link` | `R_fore` |

Any other name still works — Studio lists every link and lets the part be picked
— but then somebody has to pick it every time the file is re-exported.

---

## 3. The numbers

Sources: `code/nong/main_python_set_nong/rig_default.json`, which is the rig
measured from `nong_assembly.STEP` (A26-72 / A30-1), and the firmware's joint
table. **Every length here is in metres, because that is what URDF uses.**

### Axes

URDF/ROS is **Z-up, X-forward**. Nong Studio is **Y-up, Z-forward**. Studio's
importer converts with the cyclic swap `(x, y, z) → (y, z, x)`, which keeps the
handedness, so rotations keep turning the same way. Going the other way — what
to type into sw2urdf — is:

| Studio axis | URDF axis |
|---|---|
| `x` (side to side, along the shoulder bar) | `y` |
| `y` (up) | `z` |
| `z` (forward) | `x` |

### Joint origins

Each origin is measured **from its parent joint**, which is what sw2urdf asks
for.

| joint | parent link | child link | type | axis (URDF) | origin xyz (m) |
|---|---|---|---|---|---|
| `waist` | `base_link` | `waist_link` | revolute | `0 0 1` | `0 0 0` |
| `shrug` | `waist_link` | `shrug_link` | revolute | `0 1 0` | `0 0 0.180` |
| `L_SH_P` | `shrug_link` | `L_sh_mid` | revolute | `0 0 1` | `0 0.180 0` |
| `L_SH_R` | `L_sh_mid` | `L_upper_link` | revolute | `0 1 0` | `0 0 0` |
| `L_EL_P` | `L_upper_link` | `L_el_mid` | revolute | `0 0 1` | `0 0 -0.129` |
| `L_EL_R` | `L_el_mid` | `L_fore_link` | revolute | `0 1 0` | `0 0 0` |
| `R_SH_P` | `shrug_link` | `R_sh_mid` | revolute | `0 0 1` | `0 -0.180 0` |
| `R_SH_R` | `R_sh_mid` | `R_upper_link` | revolute | `0 1 0` | `0 0 0` |
| `R_EL_P` | `R_upper_link` | `R_el_mid` | revolute | `0 0 1` | `0 0 -0.129` |
| `R_EL_R` | `R_el_mid` | `R_fore_link` | revolute | `0 1 0` | `0 0 0` |
| `head` | `shrug_link` | `head_link` | fixed | — | measure in CAD |

`0.180` is `shoulderX` / `shoulderY`, `0.129` is `upperLenL`/`upperLenR`. The
forearm is `0.183` (`foreLenL`/`foreLenR`) — it carries no child joint, so that
length only shows in the mesh, not in a joint origin.

`shrugPivot` is 0 in the shipped rig, which is why the shrug and the shoulder
line sit at the same height. If it is ever measured, the shrug origin moves up
by it and the two shoulder origins move down by it.

### Limits

URDF limits are in radians, measured from each joint's own zero. Studio holds
them in joint degrees with a zero per joint, so `lower = (min − zero)·π/180`.

| joint | Studio min–max (°) | zero | URDF lower / upper (rad) |
|---|---|---|---|
| the 8 arm joints | 25 – 155 | 0 | `0.4363` / `2.7053` |
| `waist` | 30 – 150 | 90 | `−1.0472` / `1.0472` |
| `shrug` | 80 – 100 | 90 | `−0.1745` / `0.1745` |

`effort` and `velocity` are required by URDF and unused by Studio. Use the real
numbers anyway, so the file is worth something to a simulator later: the
shoulders are PDI-1181MG (3.6 N·m, 375 °/s → `6.54` rad/s), the elbows MG90S
(0.31 N·m, 400 °/s → `6.98`), WAIST a TD-8135MG (33.4 N·m, 200 °/s → `3.49`).

### The gear ratios do NOT go in the URDF

The shoulders are 14:19 and the elbows 12:13, and **the robot applies that
itself** — the firmware converts joint angles to servo angles. Studio, the
sequences and this URDF are all in JOINT degrees. Putting the reduction in the
URDF as well would count it twice.

---

## 4. In SolidWorks, in order

1. Open `nong_assembly.SLDASM`. Close anything the structural session left open
   — two sessions in one assembly is how work gets lost.
2. Put the assembly in its **neutral pose**: every joint at Studio's 90°, arms
   hanging straight. The URDF's zero is whatever the assembly is mated to when
   you export, and a URDF exported mid-gesture is one whose every angle is
   offset by that gesture.
3. **Tools ▸ Export as URDF.**
4. Build the tree from section 2. For each joint, sw2urdf asks for a reference
   **axis** and a reference **coordinate system** — make them in the assembly
   first (Insert ▸ Reference Geometry) rather than letting the add-in guess, or
   the origins come out on the component's own origin instead of the real pivot.
5. Type the limits from section 3 into the add-in's Joint Properties page.
6. Export. You get a folder with `urdf/<name>.urdf`, `meshes/*.STL` and a
   `textures` folder.
7. **Check it in Studio**, which is the real test:
   * Studio ▸ Setup ▸ Model — Import each `meshes/*.STL`;
   * Studio ▸ Setup ▸ Build it from a URDF — pick the `.urdf`, press **Read
     URDF**, check the parts it guessed, press **Use this URDF**;
   * the nong should look like the nong. If it is lying on its side, switch
     **Up is** to `Y`. If it is a thousand times too big or too small, switch
     **Sizes are in**.

---

## 5. What is still open

* **The head origin** is not in `rig_default.json`, so it has to be measured in
  CAD. Everything else above comes from the measured rig.
* **`shrugPivot`** is 0. The real see-saw has a bearing above the shoulder line
  (`nong_dogdag_body_bearing_holder`); when that height is measured, two origins
  in the table change.
* **Studio does not yet drive a joint tree from the URDF**, only the six body
  meshes and the arm lengths. Driving the joint axes and limits from the file as
  well is the natural next step, and the importer already parses them.
* sw2urdf writes its STL meshes in **metres**. That is why Studio's default is
  `×1000` for both the lengths and the mesh scale, and why a `<mesh scale>` of
  `0.001` in the file ends up as `1` in Studio and not `1000` — the two
  conversions multiply.
