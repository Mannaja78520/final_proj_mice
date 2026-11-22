// --- colour theme picker ---
// Studio already wears whichever theme the hub chose (shared/web/mice.js reads the
// same saved choice), but it had no picker of its own: a person who opened Studio
// first could not get a dark page. The picker is the shared one, so a theme added
// to themes.css shows up here without touching this file.
if (window.miceTheme) miceTheme.picker($("themePick"));
// The 3D view's backdrop is painted by three.js, not CSS, so it is re-read when the theme changes.
if (window.miceTheme) miceTheme.onChange(() => {
  scene.background = new THREE.Color(getComputedStyle(document.body).getPropertyValue("--bg").trim());
  markDirty3d();
});
