# Tools page, dark (midnight) theme: model review, 2026-11-23

Question: do icons, tile backgrounds and palette look harmonious for non-engineer users? At most 10 CSS/design changes.
Not a screenshot review: no screenshot could be taken (no Playwright browser; `tools/ai_panel.py --ask` died silently with exit 255 after "asking 2 models", so models were called directly).
Both answers are a shortlist, not facts. Verify against the code.

## GPT Codex (gpt-6-astra, read-only, read the real files)
Icon family: fine. Palette pairing: fine.
1. style.css:153 tiles inherit `--sunk`, look recessed. Use a surface token between `--card` and `--btn`; define it in `shared/web/themes.css`.
2. style.css:158 lime/purple icon plates compete with the bright characters. Soften the baked-in backgrounds in `shared/web/img/apps/`; no filters that dull the whole icon.
3. style.css:155 descriptions inherit 13px address styling. Use `font-size:inherit`, keep `line-height:1.5`.
4. style.css:159 neutral Open buttons lose to colourful art. Use `var(--acc)` for button text, keep quiet fill.
5. parts/tools.js:31 emoji fallback has no matching 56px frame, breaks alignment. Same frame for both icon paths; new art goes in `image` of `apps/<id>/app.json`.

## Gemini (gemini-3.8-flash-high, CSS pasted in the prompt, no tools)
1. `.tool-pic`: `background:rgba(255,255,255,0.06);padding:6px;box-sizing:border-box` to soften the border clash.
2. `.tool-pic`: `border-radius:var(--r-md,14px)` instead of 14px.
3. `.tool-pic`: `filter:drop-shadow(0 2px 6px rgba(0,0,0,0.35))`.
4. `.mod.tool-tile`: `background:color-mix(in srgb,var(--card) 88%,#fff);border:1px solid var(--line);border-radius:var(--r-lg)` for a lifted surface.
5. `.mod.tool-tile`: `box-shadow:0 4px 12px rgba(0,0,0,0.25)`.
6. `.mod.tool-tile:hover`: `transform:translateY(-2px);border-color:var(--acc);transition:transform 120ms,border-color 120ms`.
7. `.tool-tile .nm`: `align-items:flex-start` so the name does not drift beside the 56px icon.
8. `.tool-tile .ip`: `color:var(--mut);font-size:0.9rem`.
9. `.tool-open`: `background:color-mix(in srgb,var(--acc) 14%,var(--btn))` for a stronger call to action.
10. `.tool-open:hover`: `background:var(--acc);color:var(--on-acc)`.

## Where they agree / conflict
- Agree: Open button needs more accent; tile surface needs a clearer step above the card; description text needs its own size.
- Conflict: Gemini adds a plate behind icons and a drop shadow; Codex says soften the plate already baked into the art and avoid filters. Box shadows also go against the "borders not shadows on dark" rule in the webapp-design skill, so Gemini 5 and 3 are doubtful.

## Round 2: real screenshots (Chrome, 1280x900, midnight and light), Codex and Gemini both given the images
Both said: plates are too saturated for the dark page; soften only the plate, keep glyph and outlines crisp, do not fade the whole icon.
Codex: lime -35..40% saturation, purple -20..25%, red -25..30% (midnight); less in light theme. Neutral tile, one quiet hover cue.
Gemini: lime -45%, purple -40%, red -42%; unify plate radius; widen tile gaps. (Larger numbers than Codex.)

## What changed
Image generation was not available (Codex out of quota earlier, no image tool), so the plates were recoloured with Pillow:
the flat plate region (flood fill from the border, tolerance 70) in the 8 icons studio, tv, camera, voice, gacha, faces, photobooth, alljao got saturation x0.65 capped at 0.38.
Characters, outlines, size (128x128), shape, filenames and webp format unchanged. help.webp untouched. Old files: `.local/backup/apps_2026-11-23/` (not in git).
Plate hue stays distinct per app (mint, teal, blue, coral, pink, purple, peach, lime), but voice, gacha and photobooth are now three similar pinks: tell me if one should move hue.
