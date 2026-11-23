// Extension Help is documentation. Rebuild a safe fragment from the allowed
// elements, so installed HTML cannot run Hub actions or load external resources.
class HelpApps {
  constructor() {
    this.tasks = document.getElementById("installedHelpLinks");
    this.status = document.getElementById("appHelpStatus");
    this.shots = [];
    this.tags = new Set(("section h2 h3 h4 h5 p div span a img figure figcaption " +
      "b strong i em small code pre br hr ul ol li table caption thead tbody tr th td " +
      "details summary kbd dl dt dd").split(" "));
  }

  safeCopy(node, context) {
    if (node.nodeType === Node.TEXT_NODE) return document.createTextNode(node.data);
    if (node.nodeType !== Node.ELEMENT_NODE) return null;
    if (node.namespaceURI === "http://www.w3.org/2000/svg") return this.safeSvg(node, context);
    if (!this.tags.has(node.localName)) return null;
    var copy = document.createElement(node.localName);
    ["class", "title", "alt", "colspan", "rowspan", "scope"].forEach(function(attr) {
      if (node.hasAttribute(attr)) copy.setAttribute(attr, node.getAttribute(attr));
    });
    if (node.localName === "a") {
      var href = node.getAttribute("href") || "";
      if (/^#[\w-]+$/.test(href) || /^\/(?![\/\\])[^\\\s]*$/.test(href)) {
        copy.setAttribute("href", href);
      }
    }
    if (node.localName === "img") {
      copy.loading = "lazy";
      copy.decoding = "async";
      var shot = node.getAttribute("data-shot");
      var legacy = node.getAttribute("src") || "";
      if (shot && /^[a-z0-9][a-z0-9_-]*$/.test(shot)) {
        this.shots.push({img: copy, base: context.url + "img/" + context.lang + "-", shot: shot});
      } else if (/^\/(docs\/shots|img\/help)\/[\w.-]+\.(png|webp)$/.test(legacy)) {
        copy.src = legacy;
      } else {
        return null;
      }
    }
    for (var child of node.childNodes) {
      var safe = this.safeCopy(child, context);
      if (safe) copy.appendChild(safe);
    }
    return copy;
  }

  safeSvg(node, context) {
    if (!["svg", "g", "title", "desc", "circle", "rect", "text"].includes(node.localName)) return null;
    var copy = document.createElementNS(node.namespaceURI, node.localName);
    var numeric = ["viewBox", "stroke-width", "cx", "cy", "r", "x", "y",
      "width", "height", "rx", "font-size", "font-weight"];
    numeric.forEach(function(attr) {
      var val = node.getAttribute(attr);
      if (val && /^[-0-9. ]+$/.test(val)) copy.setAttribute(attr, val);
    });
    ["fill", "stroke"].forEach(function(attr) {
      var val = node.getAttribute(attr);
      if (val && /^(none|currentColor|var\(--[a-z-]+\))$/.test(val)) copy.setAttribute(attr, val);
    });
    if (node.getAttribute("text-anchor") === "middle") copy.setAttribute("text-anchor", "middle");
    if (node.localName === "svg") copy.setAttribute("role", "img");
    for (var child of node.childNodes) {
      if (child.nodeType !== Node.TEXT_NODE && child.namespaceURI !== node.namespaceURI) continue;
      var safe = this.safeCopy(child, context);
      if (safe) copy.appendChild(safe);
    }
    return copy;
  }

  addTask(app, lang) {
    var li = document.createElement("li");
    var link = document.createElement("a");
    link.href = "#" + app.anchor;
    link.textContent = app.title[lang];
    li.append(link, document.createTextNode(" — " + app.summary[lang]));
    this.tasks.appendChild(li);
    this.tasks.parentNode.hidden = false;
  }

  updateShots() {
    var theme = document.documentElement.dataset.mode === "dark" ? "dark" : "light";
    this.shots.forEach(function(s) { s.img.src = s.base + theme + "-" + s.shot + ".webp"; });
  }

  async language() {
    var saved;
    try { saved = localStorage.getItem("mice.lang"); } catch (e) {}
    if (!saved) {
      try {
        var response = await fetch("/lang/index.json");
        if (response.ok) saved = (await response.json()).default;
      } catch (e) {}
    }
    return ["th", "en", "zh", "ja"].includes(saved) ? saved : "en";
  }

  async section(app, lang) {
    var url = "/api/help/apps/" + encodeURIComponent(app.id) + "/";
    var response = await fetch(url + lang + ".html");
    if (!response.ok) throw new Error("Help section unavailable");
    var template = document.createElement("template");
    template.innerHTML = await response.text();
    var section = template.content.firstElementChild;
    if (!section || section.localName !== "section" || section.id !== app.anchor) {
      throw new Error("Invalid Help section");
    }
    var safe = this.safeCopy(section, {url: url, lang: lang});
    safe.id = app.anchor;
    safe.lang = lang;
    return safe;
  }

  async load() {
    var groups = HELP_GROUPS.map(g => ({id: g.id, label: g.label, topics: g.topics.slice()}));
    try {
      var response = await fetch("/api/help/apps", {cache: "no-store"});
      if (!response.ok) throw new Error("Help list unavailable");
      var result = await response.json();
      var lang = await this.language();
      var sections = await Promise.all(result.apps.map(async app => {
        try { return await this.section(app, lang); }
        catch (e) { return null; }
      }));
      result.apps.forEach((app, i) => {
        var section = sections[i], group = groups.find(g => g.id === app.group);
        if (!section || !group) { this.status.hidden = false; return; }
        if (document.getElementById(app.anchor)) return;
        var slot = document.querySelector('[data-help-group="' + group.id + '"]');
        slot.parentNode.insertBefore(section, slot);
        this.addTask(app, lang);
        group.topics.push([app.anchor, app.title[lang]]);
      });
      this.updateShots();
      document.addEventListener("micemode", () => this.updateShots());
    } catch (e) {
      this.status.hidden = false;
    }
    return groups;
  }
}

(async function(){
  var groups = await new HelpApps().load();
  initHelpTopics(groups);
  window.miceHelp = new window.MiceHelpNavigator();
  window.miceHelp.init();
})();
