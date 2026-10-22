// A WIN IN A FRIEND'S GAME GIVES A PRIZE (A47-6).
// The hub serves the friend's game folder at /play/<partner>/ and adds this
// script to the page as it is sent: their files are never changed (hard rule:
// their repo, read only). What to watch is DATA, the "play.watch" list of
// that partner in config/partners.json, put on the page as window.MICE_PLAY:
//   {game, key, list, id, result, person}  a localStorage record list: every NEW
//                                          record (by id) is a win
//   {game, text, match, result}            an element's text starting to match
//   {event, game?, result, person, id}     a window event the game fires itself
//                                          (asked of the friend: "alljao:win";
//                                          detail.game names the game)
// Each win goes to POST /api/gacha/game; the hub's "games" rules (Prize
// machines page) decide which kind, and the answer says where to collect it.
(function () {
  const P = window.MICE_PLAY || {};
  const seen = {};                          // watcher index -> ids already known

  function pick(obj, path) {
    return String(path || "").split(".").filter(Boolean)
      .reduce((o, k) => (o == null ? o : o[k]), obj);
  }
  function records(w, raw) {
    try {
      const list = pick(JSON.parse(raw || "null"), w.list);
      return Array.isArray(list) ? list : [];
    } catch (e) { return []; }
  }

  function show(text) {
    if (!text) return;
    let box = document.getElementById("mice-prize-note");
    if (!box) {
      box = document.createElement("div");
      box.id = "mice-prize-note";
      box.setAttribute("role", "status");
      box.style.cssText = "position:fixed;left:50%;bottom:24px;transform:translateX(-50%);z-index:99999;" +
        "max-width:90vw;padding:14px 20px;border-radius:14px;background:#1f2a24;color:#fff;" +
        "font:600 18px/1.4 system-ui,sans-serif;box-shadow:0 6px 24px rgba(0,0,0,.3)";
      document.body.appendChild(box);
    }
    box.textContent = text;
    box.hidden = false;
    clearTimeout(show.t);
    show.t = setTimeout(() => { box.hidden = true; }, 12000);
  }

  async function won(w, result, person, ref) {
    const body = {game: w.game, result: String(result == null ? "" : result),
                  person: person || w.defaultPerson || "", ref: String(ref || Date.now())};
    try {
      const r = await fetch(P.api || "/api/gacha/game", {method: "POST",
        headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)});
      const a = await r.json().catch(() => ({}));
      show(a.message);
      window.dispatchEvent(new CustomEvent("mice-prize", {detail: a}));
    } catch (e) { /* the hub is away: the game itself goes on */ }
  }

  // Record lists in localStorage: wrap setItem so this page sees its own writes.
  const lists = (P.watch || []).map((w, i) => [w, i]).filter(([w]) => w.key);
  lists.forEach(([w, i]) => {
    let raw = null;
    try { raw = localStorage.getItem(w.key); } catch (e) {}
    seen[i] = new Set(records(w, raw).map(r => pick(r, w.id || "id")));
  });
  if (lists.length && window.Storage) {
    const setItem = Storage.prototype.setItem;
    Storage.prototype.setItem = function (k, v) {
      setItem.apply(this, arguments);
      if (this !== window.localStorage) return;
      lists.forEach(([w, i]) => {
        if (k !== w.key) return;
        records(w, v).forEach(r => {
          const id = pick(r, w.id || "id");
          if (id == null || seen[i].has(id)) return;
          seen[i].add(id);
          won(w, pick(r, w.result), w.person ? pick(r, w.person) : "", id);
        });
      });
    };
  }

  // A status text that starts to say "you won".
  function watchText(w) {
    const el = document.getElementById(w.text);
    if (!el) return;
    let re;
    try { re = new RegExp(w.match || ".", "i"); } catch (e) { return; }
    let was = re.test(el.textContent || "");
    new MutationObserver(() => {
      const now = re.test(el.textContent || "");
      if (now && !was) won(w, w.result || el.textContent, "", w.game + "-" + Date.now());
      was = now;
    }).observe(el, {childList: true, characterData: true, subtree: true});
  }
  // An event the game itself fires: the steadiest link, once the friend adds it.
  (P.watch || []).filter(w => w.event).forEach(w => {
    const done = new Set();
    window.addEventListener(w.event, e => {
      const d = (e && e.detail) || {};
      const id = pick(d, w.id || "id");
      if (id != null && done.has(id)) return;
      if (id != null) done.add(id);
      won(Object.assign({}, w, {game: w.game || d.game || "game"}), pick(d, w.result || "result"),
          pick(d, w.person || "person"), id);
    });
  });

  const texts = (P.watch || []).filter(w => w.text);
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => texts.forEach(watchText));
  } else {
    texts.forEach(watchText);
  }
})();
