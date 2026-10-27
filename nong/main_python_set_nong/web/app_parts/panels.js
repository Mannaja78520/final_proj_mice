// --- take a side card out to its own window (A49-3) ---
// User 2026-10-23: Studio's tabs back on top in their own area, and the cards
// "ปิดเปิดได้หรือลากออกไปด้านนอก" - fold (card_fold.js) or drag out. ⧉ in a
// card's title floats it over the page (position:fixed, still inside #side so
// every rule and id keeps working); drag its title to move it, its corner to
// size it, ⇲ puts it back. Where each one floats is kept per browser under
// PANEL_KEY, by the same tab:title key card_fold uses. Desk screens only: on a
// phone the page is one column and a window over it would hide the rest.
const PANEL_KEY = "nong_panels";
const PANEL_DESK = "(min-width:861px)";
let panelSaved = {};

function panelKey(card) {
  const h = card.querySelector(":scope > h2");
  return card.dataset.stab + ":" + (h ? h.firstChild.textContent.trim() : card.id);
}
function panelKeep() {
  try { localStorage.setItem(PANEL_KEY, JSON.stringify(panelSaved)); } catch (e) {}
}
// a window never ends up where its title cannot be grabbed again
function panelClamp(card) {
  if (!card.offsetWidth) return;     // hidden (another tab, no login): it measures 0 x 0
  const r = card.getBoundingClientRect();
  const x = Math.min(Math.max(0, r.left), Math.max(0, innerWidth - 120));
  const y = Math.min(Math.max(0, r.top), Math.max(0, innerHeight - 40));
  card.style.left = x + "px";
  card.style.top = y + "px";
}
function panelFloat(card, at, remember) {
  const r = card.getBoundingClientRect();
  at = at || {x: r.left - 40, y: r.top + 20, w: r.width};
  card.classList.add("floating");
  card.style.left = at.x + "px";
  card.style.top = at.y + "px";
  card.style.width = (at.w || r.width) + "px";
  if (at.h) card.style.height = at.h + "px";
  showTab(sideTab);                  // a floating card shows on every tab: measure it shown
  panelClamp(card);
  card.querySelector(".popout").textContent = "⇲";
  card.querySelector(".popout").title = "Put this panel back in the side panel";
  if (remember) { panelSaved[panelKey(card)] = panelWhere(card); panelKeep(); }
}
function panelDock(card) {
  card.classList.remove("floating");
  ["left", "top", "width", "height"].forEach(k => card.style[k] = "");
  card.querySelector(".popout").textContent = "⧉";
  card.querySelector(".popout").title = "Take this panel out: drag it anywhere, it stays open on every tab";
  delete panelSaved[panelKey(card)];
  panelKeep();
  showTab(sideTab);
}
function panelWhere(card) {
  const r = card.getBoundingClientRect();
  return {x: Math.round(r.left), y: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height)};
}
function panelDrag(card, h) {
  let start = null, moved = false;
  h.addEventListener("pointerdown", e => {
    if (!card.classList.contains("floating") || e.target.closest("label, input, button, select, a")) return;
    const r = card.getBoundingClientRect();
    start = {x: e.clientX - r.left, y: e.clientY - r.top, cx: e.clientX, cy: e.clientY};
    moved = false;
    try { h.setPointerCapture(e.pointerId); } catch (err) {}   // keeps the drag when the pointer outruns the title
  });
  h.addEventListener("pointermove", e => {
    if (!start) return;
    if (Math.abs(e.clientX - start.cx) + Math.abs(e.clientY - start.cy) > 4) moved = true;
    card.style.left = (e.clientX - start.x) + "px";
    card.style.top = (e.clientY - start.y) + "px";
  });
  h.addEventListener("pointerup", () => {
    if (!start) return;
    start = null;
    panelClamp(card);
    panelSaved[panelKey(card)] = panelWhere(card);
    panelKeep();
  });
  // a drag is not a click: the title would fold the card as it is let go
  card.addEventListener("click", e => {
    if (moved && e.target.closest(":scope > h2")) { e.stopPropagation(); moved = false; }
  }, true);
}

function initPanels() {
  try { panelSaved = JSON.parse(localStorage.getItem(PANEL_KEY)) || {}; } catch (e) {}
  const desk = window.matchMedia(PANEL_DESK);
  document.querySelectorAll("#side div.card[data-stab]").forEach(card => {
    const h = card.querySelector(":scope > h2");
    if (!h || card.dataset.stab === "login" || card.id === "userManageCard") return;
    const b = document.createElement("button");
    b.type = "button";
    b.className = "popout";
    b.textContent = "⧉";
    b.title = "Take this panel out: drag it anywhere, it stays open on every tab";
    b.addEventListener("click", e => {
      e.stopPropagation();
      if (card.classList.contains("floating")) panelDock(card);
      else panelFloat(card, null, true);
    });
    h.appendChild(b);
    panelDrag(card, h);
    const at = panelSaved[panelKey(card)];
    if (at && desk.matches) panelFloat(card, at, false);
  });
  // the size is the window's own corner (CSS resize): keep it when let go
  if ("ResizeObserver" in window) {
    let soon = null;
    const ro = new ResizeObserver(() => {
      clearTimeout(soon);
      soon = setTimeout(() => {
        // a hidden window measures 0 x 0: keep where it was instead
        document.querySelectorAll("#side .card.floating").forEach(c => {
          if (c.offsetWidth) panelSaved[panelKey(c)] = panelWhere(c);
        });
        panelKeep();
      }, 300);
    });
    document.querySelectorAll("#side div.card[data-stab]").forEach(c => ro.observe(c));
  }
  // a phone-narrow window docks every floating card back (nothing is forgotten)
  desk.addEventListener("change", () => {
    document.querySelectorAll("#side .card.floating").forEach(c => {
      c.classList.remove("floating");
      ["left", "top", "width", "height"].forEach(k => c.style[k] = "");
    });
    if (desk.matches) document.querySelectorAll("#side div.card[data-stab]").forEach(c => {
      const at = panelSaved[panelKey(c)];
      if (at && c.querySelector(".popout")) panelFloat(c, at, false);
    });
    showTab(sideTab);
  });
  window.addEventListener("resize", () => document.querySelectorAll("#side .card.floating").forEach(panelClamp));
  // the tab row: three across when the panel is narrow, all six when there is room
  const tabs = $("sideTabs"), side = $("side");
  if (tabs && side && "ResizeObserver" in window)
    new ResizeObserver(() => tabs.classList.toggle("narrow", side.clientWidth < 420)).observe(side);
}
initPanels();
