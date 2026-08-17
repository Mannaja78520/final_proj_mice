# Patch 0008

- **when:** 2026-07-27 18:05
- **change:** Revert servo frame rate default to 50Hz everywhere (was 330 on shoulders): 330Hz over-currented a marginal L_SH_R on moves and tripped it; 50Hz is the pre-update rate that worked. 330 still available via RATE / Hz box
- **files:** app.js, index.html, style.css

Restore this exact version with:  `python save_patch.py --restore 8`
