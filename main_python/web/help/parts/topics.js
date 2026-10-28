// THE SIDEBAR, from data (A47-18, user 2026-10-23: "ทำ group ให้หน่อย ... โชว์ได้
// หรือเก็บได้ตาม group เผื่อมีแอพและอย่างอื่นเพิ่มในอนาคต"). Each group opens and
// closes and the page remembers which (localStorage); the open topic's group
// always opens. Runs before search.js, which reads these links and adds
// Previous / Next. A new app = one [id, words] line here + its part file.
const HELP_GROUPS = [
  {id: "start", label: "Start here", topics: [["bytask", "Start with a task"]]},
  {id: "use", label: "Use it", topics: [
    ["hub", "Mice Hub"], ["modsite", "A module's own page"], ["studio", "Nong Studio"],
    ["tv", "TV Remote"], ["camera", "Cameras"], ["voice", "Voice"], ["faces", "Reconize"],
    ["gacha", "Prize machines"], ["all-jao", "All-Jao Games"], ["accounts", "Accounts"]]},
  {id: "build", label: "Build and set up", topics: [
    ["firmware", "Board setup"], ["lift", "Lift module"], ["nong", "Nong module"]]},
  {id: "wrong", label: "When something is wrong", topics: [
    ["qc", "QC suite"], ["transports", "Transports"], ["commands", "Command language"],
    ["files", "Files &amp; formats"]]},
];

(function(){
  var nav = document.getElementById("helpNav");
  if (!nav) return;
  var closed = {};
  try { closed = JSON.parse(localStorage.getItem("help_groups_closed") || "{}"); } catch (e) {}
  function keep(){ try { localStorage.setItem("help_groups_closed", JSON.stringify(closed)); } catch (e) {} }
  nav.innerHTML = HELP_GROUPS.map(function(g){
    return '<div class="grp-box" data-grp="' + g.id + '"><button type="button" class="grp">' +
      g.label + '<span class="grp-n">' + g.topics.length + '</span></button><div class="grp-links">' +
      g.topics.map(function(t){ return '<a href="#' + t[0] + '">' + t[1] + '</a>'; }).join("") + '</div></div>';
  }).join("");
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
    var a = nav.querySelector('a[href="#' + hash + '"]');
    var id = a && a.closest(".grp-box").dataset.grp;
    if (id && closed[id]) { closed[id] = false; keep(); draw(); }
  }
  window.addEventListener("hashchange", function(){ openFor(location.hash.slice(1)); });
  draw();
  openFor(location.hash.slice(1));
})();
