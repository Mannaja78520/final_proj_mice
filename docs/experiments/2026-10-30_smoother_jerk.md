# 2026-10-30 — Why the shared smoother raised jerk on RL motion, and the fix

Plan id A54-2. Owner claude:yinmmk. Fakes and maths only: no robot, no board PASS run on hardware.
The RL and cheer dances come from YouTube videos, so their numbers are here but their data is not
(private: project files `experiments/2026-10-29_motion_smooth/`, `cheer/*_v5.json`).

## Question
The four-dance RL run (experiment-records.md, "Final") found the shared smoother (A54-1,
`main_python/motion_smooth.py`) made dense RL motion ROUGHER: come_and_cheer center rl 25033 ->
rl_smooth 33168, witsawa center 29813 -> 39922 (RMS jerk deg/s³ after the servo model). Why, and
can smoothing be made to never raise jerk while keeping music timing and real flicks?

## Cause (measured)
RL keys are thinned from the 50 Hz policy (RDP, tolDeg 3, minKeyMs 120), so a key every ~160 ms.
The smoother then picks a speed to pass each key. Two things threw nearly all of them away:

1. No collision check runs on the curve in the RL tools, so the curve had to stay within
   `uncheckedOffLineDeg` = 1 deg of the straight line between keys (all 10 joints together). A curve
   through 10 joints moving at dance speed leaves the line by more than that almost always, so every
   failing move shrank its speeds to 0. Synthetic 60 s dance: 3586 speeds guessed, **75 left (2 %)**.
2. With speeds at 0 the move is the old cosine: rest to rest, a full stop every ~160 ms. That is the
   stutter, and it is rougher than the policy itself.

Also the guesses were Fritsch-Carlson slopes from the keys alone (0 wherever a joint turns back),
though the policy's own speed at each key is known.

## Fix (config: `nong/main_python_set_nong/web/motion_smooth.json`)
- `followDensePath` (true): when keys come from a dense motion (`DensePath(frames, idx, hz)`, used by
  `tools/rl_compare/smooth.py` and `to_sequence.py`), each key is passed at that motion's own speed,
  and the curve is measured against that motion (it was what got scored and collision-checked), not
  the straight line: it may be no farther from it than the plain cosine move is, or than the off-line
  limit, and may go at most that limit past where the motion itself went. `to_sequence` still replays
  the file and re-checks collisions.
- `jerkGuard` (true, `jerkFrameMs` 20): for every source, per key, the jerk over the two moves it
  joins is compared with the cosine's at the board's 50 Hz; rougher shrinks that key's speeds; then the
  whole dance is compared, so a smoothed file is never rougher than the same keys without smoothing.
  Same code in Studio's `motion_smooth.js` (parity in check_motion_smooth).
- Key times are untouched (music), and a key where the motion turns back keeps its exact pose (flick).

## Results

### Synthetic 50 Hz "policy" (60 s, 10 joints, 4 sines per joint + low-passed jitter σ; jerk RMS deg/s³)
Commanded = what is sent; servo = after `tools/rl_compare/servo.py` (40 ms lag, 3000–4000 °/s²), as rl_compare scores.

| jitter σ | dense policy cmd / servo | keyed, before cmd / servo | keyed, after cmd / servo | keys |
|---|---|---|---|---|
| 0.0 | 5225 / 5000 | 58972 / 29178 | 6081 / 5204 | 371 |
| 0.3 | 32617 / 11544 | 59517 / 29352 | 7208 / 5535 | 372 |
| 0.6 | 64605 / 21405 | 59873 / 29552 | 16584 / 9140 | 372 |

Keyed after the fix is 5–8x smoother than before. Against the dense policy it is smoother whenever the
policy has jitter (as real RL does: 23096–30275 after the servo model). On a perfectly smooth source
(σ 0) keying at 3 deg costs +4 % (servo) / +16 % (commanded): a cubic between keys has a speed-up step
at each key that the dense sines did not. Fewer of those need more keys (tolDeg / minKeyMs), not a
different smoother; left as is (board file size, 30 KB crash 2026-10-28).

### Cheer v5 dances (Studio keys, video source; jerk_report at 50 Hz, commanded)
| dance | cosine | before, unchecked 1 deg | after, unchecked | before, Studio (6 deg + checks) | after, Studio | stops after (unchecked / Studio) |
|---|---|---|---|---|---|---|
| come_and_cheer center | 37349 | 36654 | 36652 | 28791 | 28791 | 302 / 100 |
| come_and_cheer left | 36069 | 35508 | 35505 | 25877 | 25877 | 282 / 74 |
| witsawa center | 33241 | 32701 | 32695 | 22721 | 22721 | 171 / 47 |
| witsawa left | 36376 | 36055 | 36053 | 22785 | 22785 | 190 / 35 |

Keyed sources were already below the cosine; the guard changes them by under 0.02 % (it takes speeds
off the few keys where they added jerk, which can add a stop). Studio results are identical.

### Regression (check_motion_smooth, made-up data, in the public repo)
- 20 s dense dance, σ 0.05, a 240 ms 30 deg flick: dense 24008, keyed held to the line (before) 39632,
  keyed following the motion 12293, cosine 44595; 94 % of via speeds kept; flick peak kept exactly.
- Guard case (3 keys from a 20000-case search): cosine 313, without guard 337, with guard 313.

## Compared with the literature
- Flash & Hogan (1985) model smooth human arm motion as minimum jerk; a rest-to-rest cosine at every
  key (the "before") is the opposite of that for a continuous dance. Passing keys at the motion's own
  speed moves toward it; a C2 spline (de Boor 1978) would remove the remaining speed-up steps but can
  overshoot keys, which the collision checks forbid here.
- Fritsch & Carlson (1980) monotone tangents keep a cubic inside its keys; they are still used where no
  dense motion exists (Studio, video, hub).
- Douglas & Peucker (1973) thinning is what produces the keys; its tolerance bounds the distance to the
  dense motion, not the jerk, which is why the speeds at the keys matter.

References: T. Flash, N. Hogan, J. Neurosci. 5(7):1688–1703, 1985. F. N. Fritsch, R. E. Carlson,
SIAM J. Numer. Anal. 17(2):238–246, 1980. D. Douglas, T. Peucker, Cartographica 10(2):112–122, 1973.
C. de Boor, A Practical Guide to Splines, Springer, 1978.

## Not done / needs the PC or the robot
- The real RL dances were not re-run here (their data is private on the PC): re-run the compare
  (`rl_smooth`) and `to_sequence` there to get the real before/after.
- The board's PASS command is still untested on hardware.
