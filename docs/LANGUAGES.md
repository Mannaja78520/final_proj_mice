# Adding a language to the hub pages

The pages (Home, Tools, Studio, Voice, Prize machines, Help, ...) have a language
picker beside "Show technical details". Thai is the default; English and any
other pack appear in the picker by themselves. **Adding a language = adding one
file.** No code change, no rebuild of the pages.

1. `python tools/lang.py new fr "Français"` creates `shared/web/lang/fr.json`
   with every text the pages carry, each empty.
2. Fill in the values (or hand `python tools/lang.py missing fr` to a translator).
   An empty or missing entry just keeps the page's own text, so a half-finished
   pack never breaks a page; texts that are not in the pack stay as written.
3. `python tools/lang.py list` shows how complete each pack is;
   `python tools/lang.py check` validates them (QC runs the same checks).
4. Reload the hub page: the new language is in the picker. The choice is kept in
   that browser. `MICE_LANG=<code>` (environment) sets which language a PC
   offers first (default `th`; `off` shows the pages exactly as written, used by QC).

Keys are the page's own text, exactly (spacing does not matter). The Thai
texts pages carry are keys of `en.json`, so every pack can turn them too.
Not covered: the friend's apps (Reconize, Photobooth, All-Jao), which have their own text.
A new page text is a new key; add it to `th.json` (and `en.json` if it is Thai).
