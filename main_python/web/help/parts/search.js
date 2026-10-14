(function(){
  // Filter: hide any feature card or table row that does not match, then hide
  // a section once nothing inside it is left.
  var q = document.getElementById("q"), none = document.getElementById("none");
  var secs = Array.prototype.slice.call(document.querySelectorAll("section"));
  q.addEventListener("input", function(){
    var term = q.value.trim().toLowerCase(), any = false;
    secs.forEach(function(s){
      // Decide about the HEADING first. Searching "camera" matches the Camera
      // section's own title, and every card inside it is then relevant — but
      // the rows were filtered on their own text first, so a section kept for
      // its heading rendered as a title with nothing underneath it. Looking
      // like the page has no answer is worse than not matching at all.
      var head = s.querySelector(".shead").textContent.toLowerCase();
      var headHit = !!term && head.indexOf(term) >= 0;
      var hits = 0;
      s.querySelectorAll(".f, tbody tr").forEach(function(el){
        var show = !term || headHit ||
                   el.textContent.toLowerCase().indexOf(term) >= 0;
        el.style.display = show ? "" : "none";
        if (show) hits++;
      });
      var keep = hits > 0 || headHit;
      s.style.display = keep ? "" : "none";
      // group labels and empty tables would otherwise float alone
      s.querySelectorAll(".scroll").forEach(function(box){
        var rows = box.querySelectorAll("tbody tr");
        var live = Array.prototype.filter.call(rows, function(r){
          return r.style.display !== "none"; }).length;
        box.style.display = live ? "" : "none";
      });
      if (keep) any = true;
    });
    none.style.display = any ? "none" : "block";
  });

  // Sidebar follows the section you are reading.
  var links = Array.prototype.slice.call(document.querySelectorAll("nav a"));
  var byId = {};
  links.forEach(function(a){ byId[a.getAttribute("href").slice(1)] = a; });
  if ("IntersectionObserver" in window) {
    var seen = {};
    var io = new IntersectionObserver(function(entries){
      entries.forEach(function(e){ seen[e.target.id] = e.isIntersecting; });
      var current = null;
      secs.forEach(function(s){ if (seen[s.id] && !current) current = s.id; });
      links.forEach(function(a){ a.classList.remove("on"); });
      if (current && byId[current]) byId[current].classList.add("on");
    }, { rootMargin: "-10% 0px -75% 0px" });
    secs.forEach(function(s){ io.observe(s); });
  }
})();
