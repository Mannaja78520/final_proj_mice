// --- the head's status line (A41-4) ---
// Whether the moves on screen are on disk, in the one status line every hub
// page has (Mice.Status, docs/web_style.md). Save and load still write their
// detail to the timeline's own line; this says only saved / not saved.
// Read once a second: isDirty() is one string compare, and the line is only
// rewritten when its words change, so a screen reader is not told every tick.
const headStat = new Mice.Status("stat");
let headSaid = "";
function showSaveState() {
  let kind, says, tech = "";
  if (savedSig === null) { kind = "loading"; says = "opening…"; }
  else if (isDirty()) { kind = "warn"; says = "not saved"; }
  else if (savedName) {
    kind = "ready"; says = "saved";
    tech = savedName + ".json + " + savedName + ".yaml";
  } else { kind = "empty"; says = keys.length > 1 ? "not saved" : "nothing to save yet"; }
  const now = kind + says + tech;
  if (now === headSaid) return;
  headSaid = now;
  headStat[kind](says, tech);
}
showSaveState();
setInterval(showSaveState, 1000);
