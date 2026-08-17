# Patch 0024

- **when:** 2026-08-04 02:49
- **change:** Plane views are now really flat: Front/Back/Left/Right/Top/Bottom switch to an OrthographicCamera so parallel edges stay parallel and dragging in a plane matches what you see; iso/free keeps perspective. activeCam() routes raycasting, OrbitControls and rendering to whichever camera is live, and the ortho frustum tracks the viewport aspect so switching never jumps.
- **files:** app.js, index.html, style.css

Restore this exact version with:  `python save_patch.py --restore 24`
