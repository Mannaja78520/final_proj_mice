/* Says plainly that this is a trial look and links the real page (A47-17).
   The real page's address comes from the script tag the hub added. */
(function () {
  const real = (document.currentScript && document.currentScript.dataset.real) || "/";
  function bar() {
    const b = document.createElement("div");
    b.className = "trial-bar";
    b.innerHTML = '🧪 <span class="trial-words">Trial look (หน้าทดลอง) ·</span> <a href="' + real +
      '">real page</a><button type="button" title="hide this" aria-label="hide this">✕</button>';
    b.querySelector("button").onclick = () => b.remove();
    document.body.appendChild(b);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", bar);
  else bar();
})();
