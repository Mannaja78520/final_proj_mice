# Friend's face server under full load

Owner:
Updated: 2026-10-21 04:20 (Bangkok)
Branch: main
Last commit: c859601
Plan: A45-14

## Goal
The friend's face server must serve Face_Regonize, our robot and Photobooth at the same time on one PC.

## Done
- Friend pulled in dual/CUDA concurrent inference (A45-17); four stateless sources 32/32.
- Request doc for the friend: project files friend_api/ขอเพื่อนแก้_2026-10-19.md.

## Next
1. Run their app + our robot faces watcher + Photobooth together and time a name per source.
2. Anything slow goes on the list for the friend. Never edit their code.

## Blocked
- The robot for the real run (see robot-tests.md).
