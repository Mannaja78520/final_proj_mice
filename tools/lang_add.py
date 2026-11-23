"""Append entries to a language pack WITHOUT re-formatting the file (a whole-file dump made a 4000-line diff).
  python tools/lang_add.py shared/web/lang/en.json '{"ไทย": "Thai"}'
Entries that already exist are left alone (use tools/lang.py to review)."""
import json, re, sys
path, add = sys.argv[1], json.loads(sys.argv[2])
raw = open(path, encoding="utf-8", newline="").read()
have = json.loads(raw)["strings"]
new = {k: v for k, v in add.items() if k not in have}
m = re.search(r"(\r?\n[ \t]*\})([ \t\r\n]*\}[ \t\r\n]*)$", raw)
nl = "\r\n" if "\r\n" in raw else "\n"
body = "".join(",%s  %s: %s" % (nl, json.dumps(k, ensure_ascii=False), json.dumps(v, ensure_ascii=False)) for k, v in new.items())
raw = raw[:m.start()] + body + raw[m.start():]
json.loads(raw)
open(path, "w", encoding="utf-8", newline="").write(raw)
print(path, "added", len(new))
