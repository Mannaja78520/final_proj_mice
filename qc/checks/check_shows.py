"""A show plays saved sequences one after another, and is just a list of names.

Asked 2026-09-17: *mix and match* sequences - greeting, then byebye - without
copying them. Asserted on the WIRE: greeting's poses reach the robot, then
byebye's, in that order, with the pause between them; the show file holds only
names; a missing sequence refuses to start instead of playing half a show.
Then the Shows tab in a real browser builds, saves and reopens one.
"""
import json
import time

import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "a show plays saved sequences in series, by name"
SLOW = True

GREET = ("name: qc_greet\nkeys:\n"
         "  - pose: 41 90 90 90 90 90 90 90 90 90 T 150\n"
         "  - pose: 42 90 90 90 90 90 90 90 90 90 T 150\n")
BYE = ("name: qc_bye\nkeys:\n"
       "  - pose: 51 90 90 90 90 90 90 90 90 90 T 150\n"
       "  - pose: 52 90 90 90 90 90 90 90 90 90 T 150\n")

DRIVER = '''
window.addEventListener('load', async function(){
  try {
    await qcWaitFor(() => typeof refreshShows === 'function', 6000);
    showTab('shows');
    await refreshShows();
    const add = document.getElementById('showAddSeq');
    await qcMark('offered-' + [].some.call(add.options, o => o.value === 'qc_greet.yaml'));
    newShow();
    add.value = 'qc_bye.yaml'; addShowItem();
    add.value = 'qc_greet.yaml'; addShowItem();
    moveShowItem(1, -1);                                   // greet first now
    document.getElementById('showName').value = 'qc_ui_show';
    await saveShow();
    await refreshShows();
    document.getElementById('showList').value = 'qc_ui_show';
    showDraft = {name: '', loop: false, items: []};
    await openShow();
    await qcMark('reopened-' + showDraft.items.map(i => i.seq).join('+'));
    await qcMark('visible-' + (document.querySelector('[data-stab=shows]').style.display !== 'none'));
  } catch (e) { await qcFail(e); }
  await qcMark('done');
});
'''


def run(t):
    fake_serial.reset()
    base, main = F.start_hub()
    F.login(base)
    seq = main.SEQUENCES
    seq.mkdir(exist_ok=True)
    made = [seq / "qc_greet.yaml", seq / "qc_bye.yaml"]
    made[0].write_text(GREET, encoding="utf-8")
    made[1].write_text(BYE, encoding="utf-8")
    folder = main.SHOWS.folder
    try:
        show = {"name": "qc_welcome", "loop": False,
                "items": [{"seq": "qc_greet.yaml", "hold": 300}, {"seq": "qc_bye.yaml"}]}
        s, b = F.post(base + "/api/show/save", json.dumps({"show": show}).encode())
        t.eq(s, 200, "a show saves")
        # The real FILE, not the answer. save() writes a .tmp and renames it,
        # so dropping the rename leaves a 200 and nothing saved.
        if not t.ok((folder / "qc_welcome.json").is_file(),
                    "and there is a file to show for it", sorted(p.name for p in folder.glob("*"))):
            return
        saved = json.loads((folder / "qc_welcome.json").read_text(encoding="utf-8"))
        t.eq([i["seq"] for i in saved["items"]], ["qc_greet.yaml", "qc_bye.yaml"],
             "the file holds the sequence names in order, nothing copied")
        s, b = F.get(base + "/api/shows")
        t.contains(b, "qc_welcome", "and is listed")

        steps = main.SHOWS.steps(saved, main.seq_steps)
        t.eq([int(x["pose"][0]) for x in steps], [41, 42, 51, 52],
             "its steps are greeting then byebye")
        t.eq(steps[1]["hold"], 300, "with the pause after greeting")

        s, b = F.post(base + "/api/show/play",
                      json.dumps({"dev": "usb:COM99", "name": "qc_welcome"}).encode())
        t.eq(s, 200, "the hub starts the show on the robot", )
        deadline = time.time() + 8
        time.sleep(0.3)
        while time.time() < deadline and main.show.status().get("running"):
            time.sleep(0.2)
        time.sleep(0.3)
        leads = [int(float(c.split()[1])) for _, c in fake_serial.wire
                 if c.upper().startswith("POSE ")]
        order = [v for v in leads if v in (41, 42, 51, 52)]
        t.eq(order, [41, 42, 51, 52], "the robot got greeting's poses, then byebye's")

        bad = dict(show, items=[{"seq": "qc_greet.yaml"}, {"seq": "qc_missing.yaml"}])
        s, b = F.post(base + "/api/show/play",
                      json.dumps({"dev": "usb:COM99", "show": bad}).encode())
        # The WORDING is the assertion, not merely a non-200. Dropping the
        # is_file() guard still refuses - read_text raises - but the person
        # gets a Windows path and an OSError instead of "step 2: no saved
        # sequence called qc_missing.yaml". That sabotage went unnoticed
        # 2026-09-18, which is why the step number and the plain sentence are
        # both asserted here.
        t.ok(s != 200 and "step 2" in b and "no saved sequence called qc_missing.yaml" in b,
             "a show naming a missing sequence refuses to start, and says which step and which file", b)

        empty = {"name": "qc_empty", "loop": False, "items": []}
        s, b = F.post(base + "/api/show/play",
                      json.dumps({"dev": "usb:COM99", "show": empty}).encode())
        t.ok(s != 200 and "no sequences" in b,
             "an empty show says so instead of starting a run with nothing in it", b)

        F.logout_qc()
        s, _ = F.post(base + "/api/show/play",
                      json.dumps({"dev": "usb:COM99", "name": "qc_welcome"}).encode())
        t.eq(s, 401, "running a show needs a login")
        F.login(base)
        s, b = F.post(base + "/api/show/delete", json.dumps({"name": "qc_welcome"}).encode())
        t.ok(s == 200 and not (folder / "qc_welcome.json").exists()
             and list((folder / ".deleted").glob("*_qc_welcome.json")),
             "deleting a show keeps it aside in shows/.deleted", b)

        if not browser.available():
            t.give_up("headless Edge unavailable - the hub half above still ran")
        browser.page(DRIVER, query=base + "/studio/_qcdriver.html", seconds=25)
        m = fake_serial.qc_marks
        t.contains(m, "done", "the Shows tab ran to the end")
        t.contains(m, "offered-true", "the tab offers the saved sequences")
        t.contains(m, "reopened-qc_greet.yaml+qc_bye.yaml",
                   "a show built, reordered and saved in the tab reopens in that order")
        t.contains(m, "visible-true", "the Shows tab shows its card")
    finally:
        for p in made + [folder / "qc_welcome.json", folder / "qc_ui_show.json"]:
            try:
                p.unlink()
            except OSError:
                pass
        for p in (folder / ".deleted").glob("*_qc_*.json") if (folder / ".deleted").is_dir() else []:
            try:
                p.unlink()
            except OSError:
                pass
