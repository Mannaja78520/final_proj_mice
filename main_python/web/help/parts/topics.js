// THE SIDEBAR, from data (A47-18, user 2026-10-23: "ทำ group ให้หน่อย ... โชว์ได้
// หรือเก็บได้ตาม group เผื่อมีแอพและอย่างอื่นเพิ่มในอนาคต"). Each group opens and
// closes and the page remembers which (localStorage); the open topic's group
// always opens. Runs before search.js, which reads these links and adds
// Previous / Next. Installed apps supply their own titles and group.
const HELP_GROUPS = [
  {id: "start", label: "Start here", topics: [["bytask", "Start with a task"]]},
  {id: "use", label: "Use it", topics: [
    ["hub", "MICE Hub"], ["modsite", "A module's own page"], ["accounts", "Accounts"]]},
  {id: "build", label: "Build and set up", topics: [
    ["firmware", "Board setup"], ["lift", "Lift module"], ["nong", "Nong module"]]},
  {id: "wrong", label: "When something is wrong", topics: [
    ["qc", "Check the system"], ["transports", "Connections"], ["commands", "Robot commands"],
    ["files", "Files & formats"]]},
];

function initHelpTopics(groups){
  var nav = document.getElementById("helpNav");
  if (!nav) return;
  var closed = {};
  var saved = null;
  try { saved = localStorage.getItem("help_groups_closed"); closed = JSON.parse(saved || "{}"); } catch (e) {}
  // First visit on a phone: only "Start here" is open, so the search box and the task cards show
  // without scrolling past 18 links (UX audit 2026-11-22, GPT and Gemini both).
  if (saved === null && window.innerWidth <= 860) {
    groups.forEach(function(g){ if (g.id !== "start") closed[g.id] = true; });
  }
  function keep(){ try { localStorage.setItem("help_groups_closed", JSON.stringify(closed)); } catch (e) {} }
  nav.innerHTML = groups.map(function(g){
    return '<div class="grp-box" data-grp="' + g.id + '"><button type="button" class="grp">' +
      g.label + '<span class="grp-n">' + g.topics.length + '</span></button><div class="grp-links">' +
      '</div></div>';
  }).join("");
  groups.forEach(function(g, i) {
    var container = nav.children[i].querySelector(".grp-links");
    g.topics.forEach(function(t) {
      var a = document.createElement("a");
      a.href = "#" + t[0];
      a.textContent = t[1];
      container.appendChild(a);
    });
  });
  function draw(){
    nav.querySelectorAll(".grp-box").forEach(function(box){
      var shut = !!closed[box.dataset.grp];
      box.classList.toggle("shut", shut);
      box.querySelector(".grp").setAttribute("aria-expanded", String(!shut));
    });
  }
  nav.querySelectorAll(".grp").forEach(function(b){
    b.addEventListener("click", function(){
      var id = b.parentNode.dataset.grp;
      closed[id] = !closed[id]; keep(); draw();
    });
  });
  function openFor(hash){
    var a = Array.from(nav.querySelectorAll("a")).find(link => link.hash === "#" + hash);
    var id = a && a.closest(".grp-box").dataset.grp;
    if (id && closed[id]) { closed[id] = false; keep(); draw(); }
  }
  window.addEventListener("hashchange", function(){ openFor(location.hash.slice(1)); });
  draw();
  openFor(location.hash.slice(1));
}
