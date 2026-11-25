# F1 batch embedding: raw data and scripts (2026-11-26)

Report for the friend: `docs/friend/face_f1_batch_embedding_2026-11-26.md`. Nothing here changes the friend's code.
Run on the PC (RTX 5070 Ti Laptop), holding the PC-wide QC lock (`mice_qc_run.lock`) with `scripts/locked.py`.

| File | What |
|---|---|
| `scripts/bench_rec.py` | recognition model alone, batch-size patterns, three cuDNN settings, pad fixes (data: `data/rec.json`; its "random 1-8" row is invalid, a seeding bug made it constant 6, use `rec2.json`) |
| `scripts/bench2.py` | per-frame embedding cost: loop / F1 / pad / hybrid on robot, crowd, random, fixed streams (`data/rec2.json`) |
| `scripts/e2e.py` | `/api/look` end to end, 10 req/s, modes switched by a file, two interleaved rounds (`data/e2e_copy.json`, `e2e_copy2.json`, `e2e_main8000.json`) |
| `scripts/sampler.py`, `res_an.py` | GPU / CPU / RAM samples per mode window (`data/res_p1.json`, `res_p2.json`; pass 1 CPU is 0, sampler bug fixed for pass 2) |
| `scripts/cold.py` | first call of every new batch size on a fresh session (`data/cold.json`): 40-120 ms each, not seconds |
| `scripts/acc.py` | embedding cosine between loop, batch and padded batch |
| `scripts/master.py`, `master2.py`, `locked.py`, `make_figs.py` | orchestration under the lock, figures |
| `f1_modes_engine.patch` | the only change in the scratch copy of the friend's `backend/app` (a mode file picks loop / batch / pad4 / pad8 / hybrid in `detect_faces`) |

The scratch copy runs on `:8011` with its own database and storage (`DATABASE_URL`, `STORAGE_PATH`). Hub and voice ran as usual, voice idle.
Figures: `docs/experiments/figures/2026-11-26_f1_*.png`.
