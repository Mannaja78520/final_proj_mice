# Apps as extensions: `mice-app.json`

Asked 2026-10-27 (A51-2): the hub is the centre. Each PC has only the apps it
needs, and an app can be added, removed or updated at any time without changing
the hub's code. Code: `main_python/extensions.py` (class `Extensions`), routes in
`main_python/hub_api_extensions.py`, check `check_extensions`.

## How the hub knows what a folder is

When you add a folder (Tools > **แอปในเครื่องนี้** > เพิ่มแอป, or an installer
running `tools/add_app.py <folder>`), the hub looks for these, in order:

1. **`mice-app.json`** inside the folder: the app's own file. It always wins.
2. **`app.json`**: the same format, used by the apps inside our `apps/` folder.
3. **A template we keep**: an entry in `config/partners.json` whose `detect`
   files all exist in the folder. This is how we recognise a friend's app
   without writing anything into their repo.

This PC's list is `main_python/extensions.json`: what was added and where it
lives, plus which shipped apps were removed. Git never stores it and a promote
never copies it. Removing an app only hides it on this PC and deletes nothing.

## `mice-app.json`

```jsonc
{
  "id": "lucky-draw",            // unique; the hub serves it at /app/lucky-draw/
  "name": "Lucky draw",
  "kind": "app",                 // "app" = a web page the hub serves from this folder
                                 // "partner" = a program with its own server (below)
  "icon": "🎲",
  "blurb": "One line saying what it is for",
  "entry": "index.html",         // the page, relative to the folder (or to "root")
  "root": "",                    // a subfolder holding the page, if any
  "order": 50,                   // position in the Tools list
  "help": "",                    // section on the help page, if any
  "needs": "",                   // a partner id it needs; hidden where that is missing
  "update": ["git", "pull", "--ff-only"]   // how the hub's Update button updates it
}
```

If `update` is missing, a git folder is updated with `git pull --ff-only`.
Every field can change later. The hub reads the file again on every request.

## A program with its own server (a "partner")

Face_Regonize, Photobooth and All-Jao run their own servers. The hub opens
them, asks whether they are up, and links to them. Their settings live in
`config/partners.json` (open, api, health, start/launch, login, events). Two
fields were added by A51-2:

- `folder` may start with `{parent}`, meaning the folder the hub's tree sits in
  (e.g. `{parent}/Face_Regonize`), or `{data}`, meaning the hub's own tree. Then
  moving or renaming the tree (`code` to `mice_system`) does not break the path.
  A folder this PC picked in Tools > Add app always wins.
- `detect`: the files that identify the app's folder.

An app with `"needs": "<partner id>"` (for example `apps/faces` needs
`reconize`) is listed only on a PC where that partner's folder exists.

### When a friend's app wants to be "official"

Once they add a `mice-app.json` to their repo, the hub reads theirs instead of
our template. Example for Face_Regonize (its fields are the same as its
`config/partners.json` entry today):

```jsonc
{
  "id": "reconize", "name": "Reconize", "kind": "partner",
  "open": "http://localhost:5173", "api": "http://127.0.0.1:8000",
  "health": "/api/health", "start": "start.bat",
  "update": ["git", "pull", "--ff-only"]
}
```

## Installers

An app's installer copies the app, then runs
`python tools/add_app.py "<its folder>"` (add `--wait` to keep trying until
the hub starts). That is the same call as the Add app button. A program on
this PC needs no hub login, but a web page from another site is refused. If
no hub is installed yet, nothing breaks: the hub offers the app under
"เจอในเครื่องนี้" when it starts, provided the app sits beside the hub's
folder.
