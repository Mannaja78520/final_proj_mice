/* Moves Studio's tab row into its own rail beside the side panel (A47-17
   trial). The buttons keep their own onclick (showTab), so Studio works
   exactly as before; only where the row sits changes. Desk screens only. */
(function () {
  function rail() {
    const tabs = document.getElementById("sideTabs"), side = document.getElementById("side");
    if (!tabs || !side || !window.matchMedia("(min-width:861px)").matches) return;
    const r = document.createElement("nav");
    r.id = "pvRail";
    r.setAttribute("aria-label", "Studio sections");
    side.parentNode.insertBefore(r, side.nextSibling);
    r.appendChild(tabs);
    window.dispatchEvent(new Event("resize"));   // the 3D view re-fits its narrower space
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", rail);
  else rail();
})();
