"""The user's own recorded voice, as two switches (config/voice_clips.json).

  * reference: a speaker for the feeling voice made from the user's clips
    (apps/voice/tts_spark/speaker.py writes <voice folder>/speaker.json). When
    `reference.enabled` it is listed as the voice "person:user-voice", like the
    saved voices in config/voice_people.json. Off = nothing changes.
  * events: an event name -> a clip played as it is, instead of the speak
    voice. A name with no file, or `events.enabled` false = the speak voice.

The clips, speaker.json and transcripts live in the character's `voice/` folder
(config/voice_profiles.json assets.voice) under the data folder: never in Git.
"""
import json
from pathlib import Path

import registry

PERSON = "user-voice"


class UserVoice:
    def __init__(self, config_path):
        self.config_path = Path(config_path)

    def settings(self):
        try:
            return registry.load(self.config_path)
        except (OSError, ValueError):
            return {}

    @staticmethod
    def plain(name):
        """A file name inside the folder: no path parts, a wav."""
        name = str(name or "")
        return name if name and Path(name).name == name and name.lower().endswith(".wav") else ""

    def event_clip(self, folder, event):
        """The recorded clip for an event, or None (events off, no entry, no file)."""
        events = self.settings().get("events") or {}
        if not events.get("enabled") or folder is None:
            return None
        name = self.plain((events.get("clips") or {}).get(str(event or "")))
        path = Path(folder) / name if name else None
        return path if path and path.is_file() else None

    def person(self, folder):
        """The saved-voice entry for the reference set, or None (off, or no speaker.json yet)."""
        ref = self.settings().get("reference") or {}
        if not ref.get("enabled") or folder is None:
            return None
        try:
            tokens = json.loads((Path(folder) / "speaker.json").read_text(encoding="utf-8"))["speaker"]
        except (OSError, ValueError, KeyError):
            return None
        entry = {"says": ref.get("says") or "Own voice (recorded)", "languages": ["th"],
                 "speaker": tokens, "backup": ref.get("backup") or ""}
        if ref.get("gender"):
            entry["gender"] = ref["gender"]
        return entry
