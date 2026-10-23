/* Help, one topic at a time (A47-17 trial, user 2026-10-23: "help ... ถ้าทำแยกตาม
   หัวข้อจะดีไหม"). The sidebar links already carry #topic; this shows only the
   topic they point at instead of scrolling to it. Typing in the search box
   brings every topic back so the search (parts/search.js) can filter them all. */
(function () {
  function start() {
    const secs = [...document.querySelectorAll("main > section[id]")];
    const links = [...document.querySelectorAll("nav a[href^='#']")];
    const q = document.getElementById("q");
    if (!secs.length) return;
    function show(id) {
      if (!secs.some(s => s.id === id)) id = secs[0].id;
      const searching = q && q.value.trim();
      secs.forEach(s => s.classList.toggle("pv-off", !searching && s.id !== id));
      links.forEach(a => a.classList.toggle("on", a.getAttribute("href") === "#" + id));
      if (!searching) window.scrollTo(0, 0);
    }
    window.addEventListener("hashchange", () => show(location.hash.slice(1)));
    if (q) q.addEventListener("input", () => show(location.hash.slice(1)));
    show(location.hash.slice(1));
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
