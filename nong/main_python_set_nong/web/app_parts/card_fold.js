// --- fold a side card to its title (A31-24) ---
// User 2026-09-24: *all card in the top right which tab is more than 1 card or
// hard to scroll down to setup can hide it like the POSE tab*. In a tab with
// two or more cards, the h2 folds its card. Setup starts folded (a list of
// titles); other tabs keep their first card open. The choice is kept per browser.
const FOLD_KEY = "nong_folded";
function initCardFold() {
  let saved = {};
  try { saved = JSON.parse(localStorage.getItem(FOLD_KEY)) || {}; } catch (e) {}
  const byTab = {};
  document.querySelectorAll("#side div.card[data-stab]").forEach(c => {
    (byTab[c.dataset.stab] = byTab[c.dataset.stab] || []).push(c);
  });
  Object.entries(byTab).forEach(([tab, cards]) => {
    if (cards.length < 2) return;
    cards.forEach((card, i) => {
      const h = card.querySelector(":scope > h2");
      if (!h) return;
      const key = tab + ":" + h.firstChild.textContent.trim();
      card.classList.add("foldable");
      h.tabIndex = 0;
      h.setAttribute("role", "button");
      const set = (folded, remember) => {
        card.classList.toggle("folded", folded);
        h.setAttribute("aria-expanded", String(!folded));
        if (!remember) return;
        saved[key] = folded;
        try { localStorage.setItem(FOLD_KEY, JSON.stringify(saved)); } catch (e) {}
      };
      set(key in saved ? saved[key] : (tab === "setup" || i > 0), false);
      const toggle = (e) => {
        // a switch inside the title (Robot link's technical-details box) is not a fold
        if (e.target.closest("label, input, button, select, a")) return;
        set(!card.classList.contains("folded"), true);
      };
      h.addEventListener("click", toggle);
      h.addEventListener("keydown", e => {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggle(e); }
      });
    });
  });
}
initCardFold();
