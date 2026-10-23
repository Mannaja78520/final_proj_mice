/* Says plainly that this is a trial look and links the real page (A47-17).
   The real page's address comes from the script tag the hub added. */
(function () {
  const real = (document.currentScript && document.currentScript.dataset.real) || "/";
  function bar() {
    const b = document.createElement("div");
    b.className = "trial-bar";
    b.innerHTML = '🧪 Trial look (หน้าทดลอง) · <a href="' + real + '">open the real page</a>';
    document.body.appendChild(b);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", bar);
  else bar();
})();
