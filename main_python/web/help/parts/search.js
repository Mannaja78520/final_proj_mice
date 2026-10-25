(function(){
  // OOP MiceHelpNavigator (A48-17) - encapsulated topic navigation, live search, and dynamic routing
  class MiceHelpNavigator {
    constructor() {
      this.q = document.getElementById("q");
      this.none = document.getElementById("none");
      this.secs = Array.prototype.slice.call(document.querySelectorAll("main > section[id]"));
      this.links = Array.prototype.slice.call(document.querySelectorAll("nav a[href^='#']"));
      this.byId = {};
      this.topicText = new Map(this.secs.map(function(s){ return [s, s.textContent.toLowerCase()]; }));
      var self = this;
      this.links.forEach(function(a){ self.byId[a.getAttribute("href").slice(1)] = a; });
    }

    // 1. Build Next / Previous navigation at the foot of each section
    buildNav() {
      var secs = this.secs;
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
          aPrev.innerHTML = "<span class='sec-nav-lbl'>← ก่อนหน้า (Previous)</span><span class='sec-nav-title'>" + prevTitle + "</span>";
          nav.appendChild(aPrev);
        } else {
          var dummy = document.createElement("div");
          dummy.className = "sec-nav-spacer";
          nav.appendChild(dummy);
        }
        if (next) {
          var nextHead = next.querySelector(".shead h2");
          var nextTitle = (nextHead ? nextHead.textContent : next.id).replace(/^[—\s]+|[—\s]+$/g, "");
          var aNext = document.createElement("a");
          aNext.className = "sec-nav-btn sec-nav-next";
          aNext.href = "#" + next.id;
          aNext.innerHTML = "<span class='sec-nav-lbl'>ถัดไป (Next) →</span><span class='sec-nav-title'>" + nextTitle + "</span>";
          nav.appendChild(aNext);
        }
        s.appendChild(nav);
      });
    }

    // 2. Topic-by-Topic mode: display only the chosen section when not searching
    showTopic(id) {
      var searching = this.q && this.q.value.trim().length > 0;
      var secs = this.secs, links = this.links;
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

    search(term) {
      term = (term || "").trim().toLowerCase();
      var any = false, secs = this.secs, topicText = this.topicText;
      if (!term) {
        this.showTopic(location.hash.slice(1));
        if (this.none) this.none.style.display = "none";
        return;
      }
      secs.forEach(function(s){
        s.classList.remove("pv-off");
        var keep = topicText.get(s).indexOf(term) >= 0;
        s.style.display = keep ? "" : "none";
        if (keep) any = true;
      });
      if (this.none) this.none.style.display = any ? "none" : "block";
    }

    init() {
      this.buildNav();
      var self = this;
      window.addEventListener("hashchange", function(){
        self.showTopic(location.hash.slice(1));
      });
      if (this.q) {
        this.q.addEventListener("input", function(){
          self.search(self.q.value);
        });
      }
      this.showTopic(location.hash.slice(1));
    }
  }

  window.MiceHelpNavigator = MiceHelpNavigator;
  window.miceHelp = new MiceHelpNavigator();
  window.miceHelp.init();
})();
