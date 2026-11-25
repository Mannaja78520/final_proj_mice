# Friend apps: ask the hub for the GPU before heavy work (2026-11-25)

We do not edit friend code. This is what the friend would change so Face_Regonize
and All-Jao share one GPU order with Voice (live voice answer first, background last).

The hub (our side, already built) hands out places on the shared GPU:

    POST http://127.0.0.1:8642/api/scheduler/acquire
         {"class": "live", "owner": "face", "wait": 20}      -> {"ok": true, "token": "L12"}
    POST http://127.0.0.1:8642/api/scheduler/release
         {"token": "L12"}                                      -> {"ok": true}

- Only from the same PC (loopback). A lease not released within 60 s is taken back.
- Classes (priority, lower first): `live` 0 (a person is waiting: face match for a greeting),
  `speech` 1, `normal` 5, `background` 9 (enrolling many photos, re-indexing, video tagging).
  The list is data in `config/scheduler.json`; ask us for a new class instead of inventing one.
- Fail open: if the call errors or answers 408, just run the work. Never block on the hub.
- Wrap only the GPU part (model forward pass), not the whole request, and keep it short:
  `acquire` -> run the model -> `release` in a `finally`.

Python helper they can copy (10 lines): `tools/jobsched.py` class `LeaseClient`
(`client.acquire("live")` returns a token or None; `client.release(token)`).

Expected effect: while a long enrolment or video tagging runs, a live face match or a spoken
answer waits at most one model call instead of the whole job.
