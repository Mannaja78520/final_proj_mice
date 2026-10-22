"""Named local characters preserve defaults, reload edits and own sound/move files (A45-27).

Uses temporary stores and the real helper/hub HTTP boundary. No user's saved
settings, audio, motion or default snapshot is touched.
"""
import base64
import concurrent.futures
import importlib.util
import io
import json
import os
import tempfile
import threading
import urllib.error
import urllib.request
import wave
from http.server import ThreadingHTTPServer
from pathlib import Path

import qc as F

AREA = "tools"
TITLE = "character folders keep defaults and other characters safe"


def run(t):
    spec = importlib.util.spec_from_file_location("qc_profile_service", F.CODE / "apps/voice/service.py")
    svc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(svc)
    with tempfile.TemporaryDirectory(prefix="qc_profiles_") as folder:
        root = Path(folder)
        config, faq = root / "voice.json", root / "qa.json"
        config.write_text(json.dumps({"tts": {"enabled": False, "style": "friendly"},
                                      "stt": {"enabled": False}, "llm": {"enabled": False},
                                      "face": {"on": False}, "presence": {"on": False}}), encoding="utf-8")
        faq.write_text('{"faqs": [{"questions": ["hello"], "answer": "Welcome"}]}', encoding="utf-8")
        before = config.read_bytes(), faq.read_bytes()
        brain = svc.Brain(config, faq)
        handler = type("ProfileHandler", (svc.VoiceHandler,), {"brain": brain, "log_message": lambda *args: None})
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = "http://127.0.0.1:%d" % server.server_port

        def request(path, data=None):
            req = urllib.request.Request(url + path, data=None if data is None else json.dumps(data).encode(),
                                         headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=10) as response:
                    raw = response.read()
                    return response.status, json.loads(raw) if "json" in response.headers.get_content_type() else raw
            except urllib.error.HTTPError as error:
                return error.code, json.loads(error.read())

        try:
            _, view = request("/profiles")
            store = brain.profiles
            t.eq(view["active"], "current", "existing work starts in an editable character")
            t.eq(sorted(view["names"]), ["current", "default"], "original snapshot and current copy exist")
            default = {name: (store.root / "default" / name).read_bytes() for name in store.FILES}
            rev = view["revision"]
            status, saved = request("/config", {"config": {"tts": {"pitch": "+5Hz"}}, "revision": rev})
            t.eq(status, 200, "settings save to the active character")
            t.eq(brain.cfg["tts"]["pitch"], "+5Hz", "the running helper picks up saved settings immediately")
            t.eq(request("/config", {"config": {"tts": {"pitch": "+9Hz"}}, "revision": rev})[0], 409,
                 "a stale tab cannot overwrite a later save")
            _, created = request("/profiles", {"action": "create", "name": "เจ๊ใจดี", "revision": saved["revision"]})
            t.eq(created["active"], "เจ๊ใจดี", "Thai character names get their own folder")
            t.ok((store.root / "เจ๊ใจดี/audio").is_dir() and (store.root / "เจ๊ใจดี/motions").is_dir(),
                 "each copy has sound and motion folders")
            # An editor changing the files on disk is a first-class save path.
            data = json.loads(brain.cfg_path.read_text(encoding="utf-8"))
            data["tts"]["pitch"] = "-5Hz"
            store.write(brain.cfg_path, data)
            _, loaded = request("/config")
            t.eq(loaded["config"]["tts"]["pitch"], "-5Hz", "local file edits apply without restarting")
            data["googleApiKey"] = "qc-private-key"
            store.write(brain.cfg_path, data)
            _, private = request("/profiles")
            t.ok("googleApiKey" not in private["config"], "profile snapshots never expose a legacy key edited on disk")
            t.ok("googleApiKey" not in request("/config")[1]["config"], "the ordinary settings read also hides a legacy key")
            t.eq(request("/faq", {"faqs": [], "revision": created["revision"]})[0], 409,
                 "an external edit also invalidates old tab saves")
            styles = json.loads(brain.styles_path.read_text(encoding="utf-8"))
            styles["styles"]["friendly"]["instruct"] = "a warm storyteller"
            store.write(brain.styles_path, styles)
            t.eq(brain.styles()["styles"]["friendly"]["instruct"], "a warm storyteller",
                 "each character's own manner file reloads immediately")
            _, loaded = request("/config")
            revision = loaded["revision"]
            wav = io.BytesIO()
            with wave.open(wav, "wb") as output:
                output.setnchannels(1); output.setsampwidth(2); output.setframerate(16000)
                output.writeframes(b"\x01\x00" * 1600)
            sound = wav.getvalue()
            made = []
            def make_sound():
                made.append(True)
                return sound, None
            t.eq(brain._spoken("profile-test", "first line", "", "", make_sound)[0], sound,
                 "a fresh character can generate its first sound and cache it")
            t.eq(brain._spoken("profile-test", "first line", "", "", make_sound)[0], sound,
                 "the character replays its generated audio")
            t.eq(len(made), 1, "the second line uses the character's actual cache")
            upload = {"action": "upload", "kind": "audio", "name": "hello.wav",
                      "data": base64.b64encode(sound).decode(), "revision": revision}
            status, uploaded = request("/profiles", upload)
            t.eq(status, 200, "a recording uploads only into this character")
            t.eq(request("/profiles", upload)[0], 409, "uploading never silently replaces a recording")
            t.eq(request("/say", {"text": "Welcome", "clip": "hello.wav", "profile": "เจ๊ใจดี"})[1], sound,
                 "the sound player returns the actual chosen recording")
            move = "steps:\n  - pose: 90 90 90 90 90 90 90 90 90 90 T 500\n  - pose: 80 90 90 90 90 90 90 90 90 90 T 800\n"
            status, _ = request("/profiles", {"action": "upload", "kind": "motions", "name": "wave.yaml",
                                 "data": base64.b64encode(move.encode()).decode(), "revision": revision})
            t.eq(status, 200, "a Studio motion has its own character copy")
            t.eq(request("/profiles?kind=motions&name=wave.yaml&profile=เจ๊ใจดี".replace("เจ๊ใจดี", "%E0%B9%80%E0%B8%88%E0%B9%8A%E0%B9%83%E0%B8%88%E0%B8%94%E0%B8%B5"))[1]["text"], move,
                 "playback reads the local character motion bytes")
            for name in ("../bad", "C:\\bad", "default", "CON", "..", "bad."):
                status, _ = request("/profiles", {"action": "create", "name": name, "revision": revision})
                t.eq(status, 409, "unsafe or existing character name is refused: " + name)
            status, _ = request("/profiles", dict(upload, name="../outside.wav"))
            t.eq(status, 409, "an upload cannot escape the character folder")
            # Two writers with the same old revision: exactly one may publish.
            with concurrent.futures.ThreadPoolExecutor(2) as pool:
                results = list(pool.map(lambda pitch: request("/config", {
                    "config": {"tts": {"pitch": pitch}}, "revision": revision})[0], ("+1Hz", "+2Hz")))
            t.eq(sorted(results), [200, 409], "concurrent saves cannot both overwrite the same revision")
            _, view = request("/profiles")
            status, view = request("/profiles", {"action": "select", "name": "default", "revision": view["revision"]})
            t.eq(status, 200, "the original snapshot can be selected")
            t.eq(request("/config", {"config": {}, "revision": view["revision"]})[0], 409, "default settings are protected")
            t.eq(request("/faq", {"faqs": [], "revision": view["revision"]})[0], 409, "default answers are protected")
            t.eq(request("/profiles", dict(upload, revision=view["revision"]))[0], 409, "default sounds are protected")
            try:
                brain.write_store(brain.faq_path, {"faqs": []})
                protected = False
            except PermissionError:
                protected = True
            t.ok(protected, "automatic saves cannot bypass default protection")
            t.eq({name: (store.root / "default" / name).read_bytes() for name in store.FILES}, default,
                 "all original defaults remain byte-for-byte unchanged")
            t.eq((config.read_bytes(), faq.read_bytes()), before, "the shared original stores were never rewritten")
            restarted = svc.Brain(config, faq)
            restarted.enable_profiles()
            t.eq(restarted.profiles.active, "default", "the chosen character survives a new helper instance")
            t.eq(restarted._cache_path("edge", "hello"), brain._cache_path("edge", "hello"),
                 "cache identity survives restart in the same character")
            store.select("current"); store.bind(brain); brain.maybe_reload()
            t.eq(brain.cfg["tts"]["pitch"], "+5Hz", "switching back restores the other character's own settings")
            t.ok(brain._cache_path("edge", "hello") != restarted._cache_path("edge", "hello"),
                 "characters do not share derived audio folders")
            for name in ("default", "current", "เจ๊ใจดี"):
                (store.root / name / "gestures.json").unlink()
            old_settings = brain.cfg_path.read_bytes()
            migrated = svc.Brain(config, faq); migrated.enable_profiles()
            t.ok(all((store.root / name / "gestures.json").is_file() for name in ("default", "current", "เจ๊ใจดี")),
                 "older characters gain only their missing gesture file")
            t.eq(brain.cfg_path.read_bytes(), old_settings, "gesture migration preserves existing settings exactly")
            _hub(t, url, config, move, sound)
        finally:
            server.shutdown(); server.server_close(); thread.join(timeout=5)


def _hub(t, url, config, move, sound):
    # The same parser used by Studio plays uploaded moves; no second timing formula.
    cfg = json.loads(config.read_text(encoding="utf-8")); cfg["service"] = url
    config.write_text(json.dumps(cfg), encoding="utf-8")
    old = os.environ.get("MICE_VOICE_CONFIG")
    old_gestures = os.environ.pop("MICE_GESTURES_MINE", None)
    os.environ["MICE_VOICE_CONFIG"] = str(config)
    try:
        base, main = F.start_hub()
        os.environ.pop("MICE_GESTURES_MINE", None)
        F.logout_qc()
        t.eq(F.post(base + "/api/voice/profiles", b'{}')[0], 401, "character writes require the hub login")
        F.login(base)
        status, raw = F.post(base + "/api/seqsteps", json.dumps({"text": move}).encode())
        parsed = json.loads(raw)
        t.ok(status == 200, "uploaded YAML reaches the hub's existing motion parser", raw[:200])
        t.eq([step["t"] for step in parsed["steps"]], [500, 800], "the actual parser preserves both move durations")
        t.eq(parsed["steps"][1]["pose"][0], 80.0, "the actual parser preserves the uploaded joint angle")
        _, raw = F.get(base + "/api/gestures")
        gesture = json.loads(raw)
        t.eq(gesture["character"], "current", "Studio uses the selected character's gesture folder")
        token = {k: gesture[k] for k in ("character", "gestureRevision")}
        status, raw = F.post(base + "/api/gestures", json.dumps({"on": False, **token}).encode())
        t.eq(status, 200, "Studio saves its moves in this character")
        profiles = config.parent / "voice_profiles"
        t.eq(json.loads((profiles / "current/gestures.json").read_text())["on"], False, "the character's actual gesture file changed")
        t.ok("on" not in json.loads((profiles / "default/gestures.json").read_text()), "the default gesture file did not change")
        t.eq(F.post(base + "/api/gestures", json.dumps({"on": True, **token}).encode())[0], 409, "old Studio saves cannot overwrite new gesture edits")
        pointer = profiles / "active.json"
        default_before = (profiles / "default/gestures.json").read_bytes()
        pointer.write_text('{"name":"default"}')
        default_view = json.loads(F.get(base + "/api/gestures")[1])
        default_token = {k: default_view[k] for k in ("character", "gestureRevision")}
        t.eq(F.post(base + "/api/gestures", json.dumps({"on": True, **default_token}).encode())[0], 409, "Studio cannot write default even with a current token")
        for bad in ("default.", "default ", "../default"):
            pointer.write_text(json.dumps({"name": bad}))
            status, _ = F.post(base + "/api/gestures", json.dumps({"on": True, **default_token, "character": bad}).encode())
            t.ok(status >= 400, "Windows aliases cannot bypass default protection: " + bad)
        pointer.write_text('{"name":"current"}')
        current_view = json.loads(F.get(base + "/api/gestures")[1])
        current_token = {k: current_view[k] for k in ("character", "gestureRevision")}
        import gestures
        original_merge = gestures.merge_mine
        def switch_during_save(mine, change):
            pointer.write_text('{"name":"default"}')
            return original_merge(mine, change)
        gestures.merge_mine = switch_during_save
        try:
            status, _ = F.post(base + "/api/gestures", json.dumps({"on": True, **current_token}).encode())
            t.eq(status, 200, "a concurrent selection keeps a save in its original character")
            t.eq(json.loads((profiles / "current/gestures.json").read_text())["on"], True, "the original character receives the edit")
            t.eq((profiles / "default/gestures.json").read_bytes(), default_before, "a concurrent selection cannot redirect the save into default")
        finally:
            gestures.merge_mine = original_merge
            pointer.write_text('{"name":"current"}')
        # A frozen module lives in an extraction folder; user data never does.
        frozen = config.parent / "frozen-layout"
        data = frozen / "data"
        bundle = frozen / "bundle"
        for parent in (data, bundle):
            (parent / "config").mkdir(parents=True)
            (parent / "config/voice_profiles.json").write_bytes((F.CODE / "config/voice_profiles.json").read_bytes())
        character = data / "config/voice_profiles/current"
        character.mkdir(parents=True)
        (character / "gestures.json").write_text("{}")
        (character.parent / "active.json").write_text('{"name":"current"}')
        previous_file, previous_config = gestures.__file__, os.environ.pop("MICE_VOICE_CONFIG", None)
        try:
            gestures.__file__ = str(bundle / "main_python/gestures.py")
            studio = data / "nong/main_python_set_nong"
            t.eq(gestures.profile_folder(studio), character, "a packaged hub finds the external character folder")
            t.eq(gestures.mine_path(studio), character / "gestures.json", "packaged saves target the character instead of the global store")
            t.ok(not (studio / "gestures.json").exists(), "packaged lookup leaves the global gesture store untouched")
        finally:
            gestures.__file__ = previous_file
            if previous_config is not None:
                os.environ["MICE_VOICE_CONFIG"] = previous_config
        _web(t, base, sound)
    finally:
        if old_gestures is not None:
            os.environ["MICE_GESTURES_MINE"] = old_gestures
        else:
            os.environ.pop("MICE_GESTURES_MINE", None)
        if old is None:
            os.environ.pop("MICE_VOICE_CONFIG", None)
        else:
            os.environ["MICE_VOICE_CONFIG"] = old


def _web(t, base, sound):
    import browser
    import fake_serial
    t.ok(browser.available(), "Edge is available for the character editor journey")
    page = (F.CODE / "apps/voice/index.html").read_text(encoding="utf-8")
    driver = r"""
<script>
(async () => {
  const report = async (name, value) => qcMark("PROFILE " + name + "=" + (value ? "yes" : "no"));
  try {
    if (!await qcWaitFor(() => window.voiceApp?.initialized && document.getElementById('profilePick')))
      throw new Error('character editor did not become ready');
    await fetch('/api/login', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({password: PASSWORD})});
    const app = window.voiceApp;
    await app.loadStores();
    app.showTab('who');
    app.$('profileName').value = 'Web happy';
    await report('copy', await app.profileAction('create') && app.profileInfo.active === 'Web happy');
    const data = new DataTransfer();
    data.items.add(new File([Uint8Array.from(atob(SOUND), c => c.charCodeAt(0))], 'web.wav', {type:'audio/wav'}));
    app.$('profileFile').files = data.files;
    app.$('profileKind').value = 'audio';
    await app.uploadProfileAsset();
    await report('upload', app.profileInfo.assets.audio.includes('web.wav'));
    const row = app.sheet[0];
    row.item.answer_en = 'Welcome'; row.item.answer_ja = 'ようこそ'; row.item.answer_zh = '欢迎';
    row.audioPick.value = 'web.wav'; row.audioPick.dispatchEvent(new Event('change', {bubbles:true}));
    const input = document.querySelector('#ansRows textarea');
    input.dispatchEvent(new Event('input', {bubbles:true}));
    await report('faqsave', await app.saveAnswers());
    app.$('ansFind').dispatchEvent(new Event('input', {bubbles:true}));
    app.$('profilePick').value = 'current';
    await report('switch', await app.profileAction('select') && app.profileInfo.active === 'current');
    app.$('profilePick').value = 'Web happy';
    await report('restore', await app.profileAction('select') && app.sheet[0].item.audio === 'web.wav');
    const cfg = await fetch('/api/voice/config').then(r => r.json());
    await report('active', cfg.profile === 'Web happy');
    // Width through an IFRAME, which has its own viewport. Setting <html>'s
    // width never narrowed 360 and made 1280 overflow any window under 1280
    // px (cloud headless 780 px), so it measured the browser, not the page.
    for (const width of [360, 1280]) {
      const frame = document.createElement('iframe');
      frame.style.cssText = 'width:' + width + 'px;height:800px;border:0';
      frame.src = '/app/voice/';
      document.body.appendChild(frame);
      const ready = await qcWaitFor(() => frame.contentWindow?.voiceApp?.initialized, 15000);
      const doc = frame.contentDocument;
      await report('layout' + width, ready && doc.documentElement.scrollWidth <= doc.documentElement.clientWidth + 1);
      frame.remove();
    }
  } catch (error) { await qcMark('PROFILE error=' + String(error).replace(/[^a-zA-Z0-9]/g, '_').slice(0,100)); }
  finally { await qcMark('done'); }
})();
</script>
""".replace("PASSWORD", json.dumps(F.HUB_PASSWORD)).replace("SOUND", json.dumps(base64.b64encode(sound).decode()))
    start = len(fake_serial.qc_marks)
    try:
        # A real desktop window: headless opens 800 wide (cloud 2026-10-22: html set
        # to 1280 overflowed a 765 px body, a frame no screen ever shows).
        browser.raw_page(page + driver, base, seconds=35, flags=("--window-size=1366,900",))
        marks = [str(m) for m in fake_serial.qc_marks[start:] if "PROFILE " in str(m)]
        for name in ("copy", "upload", "faqsave", "switch", "restore", "active", "layout360", "layout1280"):
            t.ok(any("PROFILE " + name + "=yes" in m for m in marks),
                 "real character editor: " + name, " | ".join(marks))
    finally:
        browser.kill()
