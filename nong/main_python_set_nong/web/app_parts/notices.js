// --- notices ---
// A FAILURE HAS TO SURVIVE BEING LOOKED AWAY FROM. The per-card status lines
// are right for routine chatter and wrong for a failure, for two reasons that
// were both real in this file:
//
//   * the card belongs to ONE tab, so `USB disconnected` was written into the
//     Robot card while the operator was posing, and nobody saw it;
//   * the monitor loop rewrites robotStat on every poll, so even a message
//     somebody WAS looking at vanished within a second.
//
// So a failure also comes here: one line under the tab strip, visible on every
// tab, written only by this function and cleared only by hand or by the next
// notice. Routine status keeps going to the cards, because a line that shouts
// about everything is a line nobody reads.
// The SAME message, said again, is not news. The monitor loop polls every
// second and its failure branch says "monitor: no reply" every time, so
// without this a dismissed notice reappeared before the mouse had moved away -
// and a warning you cannot get rid of is one you learn to ignore. A DIFFERENT
// message always shows, dismissed or not: that is something new going wrong.
let noticeSaid = null;
function notice(text) {
  const box = $("notice"), t = $("noticeText");
  if (!box || !t || !text) return;
  if (text === noticeSaid && box.hidden) return;   // dismissed, and unchanged
  noticeSaid = text;
  t.textContent = text;
  box.hidden = false;
}

function clearNotice() {
  const box = $("notice");
  if (box) box.hidden = true;      // noticeSaid is kept: see notice()
}

function showTab(which) {
  if (which === "move") which = "pose";          // the old name
  if (!STAB_BTN[which]) which = "pose";
  sideTab = which;
  
  let renderWhich = which;
  if (!currentUser && (which === "robot" || which === "setup")) {
    renderWhich = "login";
  }
  
  // both old containers stay visible; the cards inside decide for themselves
  $("tabMove").style.display = "";
  $("tabSetup").style.display = "";
  document.querySelectorAll("[data-stab]").forEach(el => {
    el.style.display = el.dataset.stab === renderWhich ? "" : "none";
  });
  
  const userCard = $("userManageCard");
  if (userCard) {
    userCard.style.display = (currentUser === "super_admin" && renderWhich === "setup") ? "" : "none";
    if (userCard.style.display === "") populateUserList();
  }
  
  Object.keys(STAB_BTN).forEach(k => {
    const b = $(STAB_BTN[k]);
    if (b) b.classList.toggle("on", k === which);
  });
}

// THE TIMELINE HANDLE DRAGS TOO (user 2026-09-16: *timeline below has the
// drag but cannot drag to make it smaller or bigger ... like the right side,
// with a scroller*). #timeDrag had CSS and no code. Same rules as the side
// panel: remembered, keyboard, double-click resets; #timeline scrolls inside.
function initTimeDrag() {
  const tl = $("timeline"), handle = $("timeDrag");
  if (!tl || !handle) return;
  const MINH = 120, STEP = 24;
  const maxH = () => Math.max(MINH, Math.round(window.innerHeight * 0.8));
  handle.setAttribute("role", "separator");
  handle.setAttribute("aria-orientation", "horizontal");
  handle.setAttribute("aria-label", "Resize the timeline");
  handle.setAttribute("tabindex", "0");
  const setHeight = (h, remember) => {
    if (h === null) { tl.style.height = ""; localStorage.removeItem("nong_timeh"); }
    else tl.style.height = Math.min(maxH(), Math.max(MINH, Math.round(h))) + "px";
    handle.setAttribute("aria-valuenow", parseInt(tl.style.height) || 0);
    resize();                       // the 3D view gets the space back
    if (remember && h !== null) localStorage.setItem("nong_timeh", parseInt(tl.style.height));
  };
  const saved = +localStorage.getItem("nong_timeh");
  if (saved) setHeight(saved, false);
  const now = () => parseInt(tl.style.height) || tl.getBoundingClientRect().height;
  handle.addEventListener("keydown", (e) => {
    let h = null, hit = true;
    if (e.key === "ArrowUp") h = now() + STEP;        // timeline grows upwards
    else if (e.key === "ArrowDown") h = now() - STEP;
    else if (e.key === "PageUp") h = now() + STEP * 4;
    else if (e.key === "PageDown") h = now() - STEP * 4;
    else if (e.key === "Home") { setHeight(null, true); e.preventDefault(); return; }
    else hit = false;
    if (!hit) return;
    e.preventDefault();
    setHeight(h, true);
  });
  handle.addEventListener("dblclick", () => setHeight(null, true));
  let dragging = false, startY = 0, startH = 0;
  handle.addEventListener("pointerdown", (e) => {
    dragging = true; startY = e.clientY; startH = now();
    try { handle.setPointerCapture(e.pointerId); } catch (_) { /* pointer already gone */ }
  });
  handle.addEventListener("pointermove", (e) => {
    if (dragging) setHeight(startH + (startY - e.clientY), false);
  });
  handle.addEventListener("pointerup", () => {
    if (!dragging) return;
    dragging = false;
    if (tl.style.height) localStorage.setItem("nong_timeh", parseInt(tl.style.height));
  });
}

// draggable divider: make the side panel wider or narrower (remembered)
function initSideDrag() {
  const side = $("side"), handle = $("sideDrag");
  const saved = +localStorage.getItem("nong_sidew");
  if (saved) side.style.width = Math.min(640, Math.max(240, saved)) + "px";
  // The panel has a width, so SAY so — a separator that announces its
  // position is one a screen reader can report and a keyboard can move.
  const MINW = 240, MAXW = 640, STEP = 16;
  handle.setAttribute("role", "separator");
  handle.setAttribute("aria-orientation", "vertical");
  handle.setAttribute("aria-label", "Resize the side panel");
  handle.setAttribute("tabindex", "0");
  const announce = () => {
    handle.setAttribute("aria-valuenow", parseInt(side.style.width) || 320);
    handle.setAttribute("aria-valuemin", MINW);
    handle.setAttribute("aria-valuemax", MAXW);
  };
  const setWidth = (w, remember) => {
    side.style.width = Math.min(MAXW, Math.max(MINW, w)) + "px";
    announce();
    resize();                       // keep the 3D canvas matched to the viewport
    if (remember) localStorage.setItem("nong_sidew", parseInt(side.style.width) || 320);
  };
  announce();

  // ARROW KEYS. Without this, someone who cannot hit the handle cannot resize
  // the panel at all — which is exactly what was reported on a laptop
  // touchpad. Home returns it to the default, so a panel dragged off-screen
  // is always recoverable.
  handle.addEventListener("keydown", (e) => {
    const now = parseInt(side.style.width) || 320;
    let w = null;
    if (e.key === "ArrowLeft")  w = now + STEP;     // panel grows leftwards
    else if (e.key === "ArrowRight") w = now - STEP;
    else if (e.key === "Home")  w = 320;            // the default
    else if (e.key === "PageUp") w = now + STEP * 4;
    else if (e.key === "PageDown") w = now - STEP * 4;
    if (w === null) return;
    e.preventDefault();
    setWidth(w, true);
  });

  // Double-click resets it, the shortcut people try first on a splitter.
  handle.addEventListener("dblclick", () => setWidth(320, true));

  let dragging = false;
  handle.addEventListener("pointerdown", (e) => {
    dragging = true;
    handle.setPointerCapture(e.pointerId);
  });
  handle.addEventListener("pointermove", (e) => {
    if (!dragging) return;
    setWidth(window.innerWidth - e.clientX, false);
  });
  handle.addEventListener("pointerup", () => {
    dragging = false;
    localStorage.setItem("nong_sidew", parseInt(side.style.width) || 320);
  });
}
