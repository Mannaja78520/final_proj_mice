(function(){
  // Topic-by-topic presentation with Next / Previous navigation, plus live search.
  var q = document.getElementById("q"), none = document.getElementById("none");
  var secs = Array.prototype.slice.call(document.querySelectorAll("main > section[id]"));
  var links = Array.prototype.slice.call(document.querySelectorAll("nav a[href^='#']"));
  var byId = {};
  links.forEach(function(a){ byId[a.getAttribute("href").slice(1)] = a; });

  // 1. Build Next / Previous navigation at the foot of each section
  secs.forEach(function(s, idx){
    if (s.querySelector(".sec-nav")) return;
    var nav = document.createElement("div");
    nav.className = "sec-nav";
    var prev = secs[idx - 1];
    var next = secs[idx + 1];
    if (prev) {
      var prevHead = prev.querySelector(".shead h2");
      var prevTitle = (prevHead ? prevHead.textContent : prev.id).replace(/^[—\s]+|[—\s]+$/g, "");
      var aPrev = document.createElement("a");
      aPrev.className = "sec-nav-btn sec-nav-prev";
      aPrev.href = "#" + prev.id;
      aPrev.innerHTML = "← ก่อนหน้า: " + prevTitle;
      nav.appendChild(aPrev);
    }
    if (next) {
      var nextHead = next.querySelector(".shead h2");
      var nextTitle = (nextHead ? nextHead.textContent : next.id).replace(/^[—\s]+|[—\s]+$/g, "");
      var aNext = document.createElement("a");
      aNext.className = "sec-nav-btn sec-nav-next";
      aNext.href = "#" + next.id;
      aNext.innerHTML = "ถัดไป: " + nextTitle + " →";
      nav.appendChild(aNext);
    }
    s.appendChild(nav);
  });

  // 2. Topic-by-Topic mode: display only the chosen section when not searching
  function showTopic(id){
    var searching = q && q.value.trim().length > 0;
    if (!searching) {
      if (!id || !secs.some(function(s){ return s.id === id; })) {
        id = secs.length ? secs[0].id : "";
      }
      secs.forEach(function(s){
        var active = s.id === id;
        s.classList.toggle("pv-off", !active);
        if (active) {
          s.style.display = "";
          s.querySelectorAll(".f, tbody tr, .scroll").forEach(function(el){
            el.style.display = "";
          });
        }
      });
      links.forEach(function(a){
        a.classList.toggle("on", a.getAttribute("href") === "#" + id);
      });
      window.scrollTo(0, 0);
    } else {
      secs.forEach(function(s){
        s.classList.remove("pv-off");
      });
    }
  }

  window.addEventListener("hashchange", function(){
    showTopic(location.hash.slice(1));
  });

  // 3. Search: reveal all sections to filter matches, or return to topic view when cleared
  if (q) {
    q.addEventListener("input", function(){
      var term = q.value.trim().toLowerCase(), any = false;
      if (!term) {
        showTopic(location.hash.slice(1));
        if (none) none.style.display = "none";
        return;
      }
      secs.forEach(function(s){
        s.classList.remove("pv-off");
        var head = s.querySelector(".shead") ? s.querySelector(".shead").textContent.toLowerCase() : "";
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
        s.querySelectorAll(".scroll").forEach(function(box){
          var rows = box.querySelectorAll("tbody tr");
          var live = Array.prototype.filter.call(rows, function(r){
            return r.style.display !== "none"; }).length;
          box.style.display = live ? "" : "none";
        });
        if (keep) any = true;
      });
      if (none) none.style.display = any ? "none" : "block";
    });
  }

  // Initial show on load
  showTopic(location.hash.slice(1));
})();
