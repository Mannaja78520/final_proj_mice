// App categorization config (A48-17)
const TOOL_GROUPS = [
  {
    id: "motion",
    title: "🤖 หุ่นยนต์และการแสดง (Robot & Motion Control)",
    match: ["studio", "tv"]
  },
  {
    id: "ai",
    title: "👁️ ระบบรู้จำ เสียง และกล้อง (AI, Vision & Voice)",
    match: ["voice", "faces", "camera", "photobooth"]
  },
  {
    id: "games",
    title: "🎮 มินิเกมและของรางวัล (Games & Prizes)",
    match: ["gacha", "all-jao"]
  },
  {
    id: "docs",
    title: "📖 คู่มือและเอกสารอ้างอิงระบบ (System Help & Documentation)",
    match: ["help"]
  }
];

function renderCategorizedApps(box, apps) {
  box.innerHTML = "";
  const assigned = new Set();
  TOOL_GROUPS.forEach(g => {
    const groupApps = apps.filter(a => {
      const id = (a.id || a.path || a.name || "").toLowerCase();
      return g.match.some(m => id.includes(m));
    });
    if (!groupApps.length) return;
    groupApps.forEach(a => assigned.add(a));

    const gDiv = document.createElement("div");
    gDiv.style.marginBottom = "var(--sp-4)";
    const h = document.createElement("h3");
    h.style.fontSize = "14.5px";
    h.style.fontWeight = "700";
    h.style.margin = "0 0 var(--sp-2) 0";
    h.style.color = "var(--txt)";
    h.textContent = g.title;
    gDiv.appendChild(h);

    const grid = document.createElement("div");
    grid.className = "tool-grid";
    grid.style.display = "grid";
    grid.style.gridTemplateColumns = "repeat(auto-fit, minmax(280px, 1fr))";
    grid.style.gap = "var(--sp-2)";
    groupApps.forEach(a => grid.appendChild(toolRow(a)));
    gDiv.appendChild(grid);
    box.appendChild(gDiv);
  });

  const otherApps = apps.filter(a => !assigned.has(a));
  if (otherApps.length) {
    const gDiv = document.createElement("div");
    gDiv.style.marginBottom = "var(--sp-4)";
    const h = document.createElement("h3");
    h.style.fontSize = "14.5px";
    h.style.fontWeight = "700";
    h.style.margin = "0 0 var(--sp-2) 0";
    h.textContent = "🛠️ เครื่องมือเพิ่มเติม (Other Tools)";
    gDiv.appendChild(h);
    const grid = document.createElement("div");
    grid.className = "tool-grid";
    grid.style.display = "grid";
    grid.style.gridTemplateColumns = "repeat(auto-fit, minmax(280px, 1fr))";
    grid.style.gap = "var(--sp-2)";
    otherApps.forEach(a => grid.appendChild(toolRow(a)));
    gDiv.appendChild(grid);
    box.appendChild(gDiv);
  }
}
function esc(t){ return String(t==null?'':t).replace(/[&<>"]/g,function(c){
  return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); }

// The tool list comes from the app registry (code/apps/*/app.json), so a new
// web app appears here by dropping a folder in — no button to hand-write.
// Drawn into EVERY tools container - the Tools tab and the card on Home -
// from one answer, so the two lists cannot say different things.
function toolBoxes(){
  return [].slice.call(document.querySelectorAll('.js-tools'));
}
function toolsSay(html){
  toolBoxes().forEach(function(b){ b.innerHTML = html; });
}
// One row for one tool.
//
// A TOOL IS NOT A MODULE. This was copied from the module list and still read
// `m.type` - but the loop variable is `a`, and an app has no module type at
// all. `m` was undefined, the exception left loadApps half-finished, and the
// Tools list rendered NOTHING. It looked like there were no tools rather than
// like a broken page, which is why it survived: an empty list is a plausible
// state. The user met the same exception again on 2026-08-21 from an exe built
// nine hours before the fix.
function toolRow(a){
  const d=document.createElement('div');
  d.className='mod tool-tile';
  d.innerHTML='<span class="nm">'+(a.icon?a.icon+' ':'')+esc(a.name||'?')+'</span>'+
              '<span class="ip">'+esc(a.blurb||'')+'</span>';
  const b=document.createElement('button');b.textContent='Open';
  b.title='open '+(a.name||'this tool')+' in a new tab';
  b.onclick=()=>window.open(a.path,'_blank');
  d.appendChild(b);
  // Help about THIS tool, when the tool says which section is about it
  // (app.json -> help). No section, no link: one pointing at the top of the
  // help page is not help, it is a thousand lines and a scrollbar.
  if(a.help){
    const h=document.createElement('a');
    h.className='tab tab-link'; h.href='/help#'+encodeURIComponent(a.help);
    h.textContent='Help ↗'; h.title='Help about '+a.name;
    d.appendChild(h);
  }
  return d;
}
async function loadApps(){
  try{
    const r=await fetch('/api/apps').then(r=>r.json());
    const apps=r.apps||[];
    // BROKEN IS NOT EMPTY. When the registry cannot be read the hub answers
    // 200 with {ok:false, apps:[], error:...} - so this never reached the
    // catch below, and the page told the operator to go and ADD a tool when
    // the truth was that the list could not be read at all. Wrong advice, and
    // it hid a real fault behind a tidy empty state.
    if(r.ok===false||r.error){
      toolsSay('<span class="mini">The tool list could not be read. Your tools are still there. '
        +'Try again; if it keeps happening, restart the hub on this PC. '
        +'<span class="tech">'+esc(String(r.error||'unknown'))+' — check '
        +'<code>code/apps/*/app.json</code> in the hub window.</span></span> '
        +'<button onclick="loadApps()">Try again</button>');
      return;
    }
    // An empty state teaches: say what goes here and how one gets here. It is
    // only reached when the hub really did read the registry and found none.
    if(!apps.length){toolsSay('<div class="empty-state"><b>No tools yet.</b>'
      +'Open Help to get started, or try again after adding your tools. '
      +'<a href="/help">Open Help</a> '
      +'<button onclick="loadApps()">Try again</button>'
      +'<span class="tech">Tools live in code/apps/, each with an app.json.</span></div>');return;}
    toolsSay('');
    // A FRESH row per list, never a clone: cloneNode copies the markup and
    // drops every handler, so the copy on Home would have looked identical and
    // done nothing when pressed.
    toolBoxes().forEach(function(box){
      renderCategorizedApps(box, apps);
    });
  }catch(e){
    // An error says what to DO, and offers the control that does it - and
    // WHICH BUILD said it. On 2026-08-21 this exact box read "m is not
    // defined": a ReferenceError fixed nine hours before the exe that was
    // running had been built. Without the build date the message sends people
    // to look for a bug in code that was already correct.
    toolsSay('<span class="mini">Could not read the tool list. Check the hub is still '
      +'running on this PC, then try again. <span class="tech">'+esc(String(e.message||e))
      +(window.HUB_BUILT?' — hub build '+esc(window.HUB_BUILT):'')+'</span></span> '
      +'<button onclick="loadApps()">Try again</button>');
  }
}
loadApps();

