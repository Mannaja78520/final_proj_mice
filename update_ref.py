import json

with open('docs/ref.html', 'r', encoding='utf-8') as f:
    content = f.read()

if 'ref_sources.js' not in content:
    content = content.replace('<script src="ref_data.js"></script>', '<script src="ref_data.js"></script>\n<script src="ref_sources.js"></script>')

script_to_add = """
function drawSources() {
  var sList = document.getElementById("sources_list");
  if (!sList) {
    sList = document.createElement("div");
    sList.id = "sources_list";
    list.parentNode.appendChild(sList);
  }
  sList.innerHTML = "<h2 style='margin-top: 40px; border-top: 1px solid var(--line); padding-top: 20px;'>Bibliography / References</h2>";
  (window.REF_SOURCES || []).forEach(function(s) {
    var item = document.createElement("div");
    item.className = "card";
    item.style.fontSize = "14px";
    
    // IEEE Scholar links
    var scholarLink = "https://scholar.google.com/scholar?q=" + encodeURIComponent(s.title);
    
    var html = "<b>[" + s.number + "] " + esc(s.author) + "</b> (" + esc(s.year) + "). <i>" + esc(s.title) + "</i>.";
    if (s.locator) html += " " + esc(s.locator) + ".";
    html += "<br><div style='margin-top: 8px;'>";
    if (s.doi) html += "<a href='https://doi.org/" + esc(s.doi) + "' target='_blank' style='margin-right: 15px;'>[DOI]</a>";
    if (s.url) html += "<a href='" + esc(s.url) + "' target='_blank' style='margin-right: 15px;'>[Original Link]</a>";
    html += "<a href='" + scholarLink + "' target='_blank'>[Google Scholar]</a>";
    html += "</div><div style='color:var(--mut); margin-top: 8px;'>" + esc(s.scope) + "</div>";
    item.innerHTML = html;
    sList.appendChild(item);
  });
}
"""

if 'drawSources()' not in content:
    content = content.replace('q.addEventListener("input", function () { draw(q.value); });\ndraw("");', script_to_add + '\nq.addEventListener("input", function () { draw(q.value); });\ndraw("");\ndrawSources();')

with open('docs/ref.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated docs/ref.html")

