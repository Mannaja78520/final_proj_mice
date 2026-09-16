# Panel review - 2026-08-23 14:32

**Question.** ANSWER STYLE. Follow exactly. Going over budget is a failure, not thoroughness.

Terse. All technical substance stays, only fluff dies.

Drop: articles, filler (just/really/basically/simply), pleasantries (sure,
certainly, happy to, great question), hedging, praise, and every sentence that
says what you are about to do. No preamble. No restating my question. No summary
at the end. No headings, no tables, no emoji.

Fragments fine. Short synonyms: big not extensive, fix not implement a solution
for. Pattern: thing, action, reason. Then next step.

Keep exact and unchanged: file paths, line numbers, code, identifiers, CLI
commands, error strings, token and property names.

Never invent an abbreviation. Standard ones are fine: DB, API, HTTP, CSS, UART.

Every sentence must parse on the first read. Keep the subject when dropping it
makes the target unclear. Compression is for filler, never for meaning. Do not
write broken grammar: it costs the same and reads worse.

One finding per line: file:line, what is wrong, why it matters. If a thing is
fine, say fine in three words and move on. Do not list what you checked.

HARD LIMIT. The line budget in the question is a limit, not a target. Answers
over it are trimmed before anyone reads them, so anything past the budget is
work thrown away. Findings first, always: if you are cut off, the cut must land
on padding.

No plan, no checklist, no artifact file. Answer directly in the reply.
Say I do not know rather than guessing. Mark any assumption ASSUME.

WHEN YOU PROPOSE CODE:
Nothing hardcoded. A list belongs in data a person can edit, not in a source
file. If a fact is needed twice, one place reads it from the other. A new thing
should cost one new entry or one new file, never a new branch inside something
long. Prefer plain and obvious over clever: no layer that exists only to be a
layer. Say which file a person edits to add the next one.
Review FINISHED work in .staging before promotion - the voice app shell (A20-5). New files: apps/voice/app.json, apps/voice/index.html, apps/voice/service.py, apps/voice/qa_data.json, config/voice.json, qc/checks/check_voice.py. Edited: main_python/main.py (voice_service_url() resolves the config path PER CALL - env MICE_VOICE_CONFIG or asset config/voice.json - then reads it fresh; Handler.voice_proxy forwards /api/verb-free /api/voice/* with urllib, passes helper errors through unchanged, 503 naming service.py when nothing listens), main_python/hub_auth.py (POST /api/voice/ask added to GATED_POST), main_python/web/help.html (section id=voice plus a bytask link). service.py grows from llm/test.py: FAQ fuzzy match over qa_data.json answers instantly, only a miss lazily imports torch+transformers under a lock; endpoints GET /health and POST /ask on 127.0.0.1. check_voice.py boots the REAL helper as a subprocess in FAQ-only mode and asserts: 503 with the start command when off, health and a VERBATIM saved answer pass through the hub, asking logged out gives 401 need_login, a miss with model off says so honestly. Claim: the hub never imports torch; the helper answers only on loopback; asking sits behind the same login gate as any robot command; a first question may hold one hub thread up to 180 s while the model loads. Check what is NOT true: header and body passthrough on the proxy, the Brain lock around the lazy load, health when qa_data.json is missing or broken JSON, the page states on a 360 px screen, whether page labels match the parts dict the service sends, the 180 s hold on a pooled hub thread, and the malformed-voice.json path. Answer directly, no plan. At most 15 lines.

**Files.** app.json, index.html, qa_data.json, service.py
**Cost.** 434387 tokens across 3 models

## The head reviewer (gemini-3.1-pro-high)

 - **real** `apps/voice/service.py:84` `_load_llm()` ignores `llm.enabled=false`, attempts torch import despite config.
 - **real** `apps/voice/service.py:54` `faqs()` swallows `OSError` and `ValueError`, masks broken `qa_data.json` as empty.
 - **real** `main_python/main.py:146` `voice_service_url()` swallows `Exception`, masks broken config as missing address.
 - **real** `apps/voice/index.html:94` UI prepends 'Saved answers: ' to `parts.faq`, renders duplicate label text.
 - **maybe** `main_python/main.py:4208` `ThreadingHTTPServer` is unpooled, 180 s proxy timeout holds thread.
 - **fine** `main_python/main.py:3048` It is fine.
 - **fine** `main_python/main.py:3050` It is fine.
 - **fine** `apps/voice/index.html:1` It is fine.

## What each model said

### gemini-3.1-pro-high  _(396.0s, 135423 tokens)_

 - **unchecked** `:` main_python/main.py:3050, proxy copies Content-Type only, header passthrough is false.
 - **unchecked** `:` main_python/main.py:4208, ThreadingHTTPServer creates unbounded threads, hub threads are unpooled.

### gemini-3.7-flash-high  _(298.2s, 225345 tokens)_

 - **unchecked** `:` [main_python/main.py:3048](file:///E:/final_proj/mice/code/.staging/main_python/main.py#L3048-L3054) - Proxy forwards only `Content-Type` and POST body; other request headers, methods, and helper response headers are dropped.
 - **unchecked** `:` [apps/voice/service.py:84](file:///E:/final_proj/mice/code/.staging/apps/voice/service.py#L84-L100) - `_load_llm()` runs under `_lock` but ignores `llm.enabled=false`, attempting torch import on every miss.
 - **unchecked** `:` [apps/voice/service.py:54](file:///E:/final_proj/mice/code/.staging/apps/voice/service.py#L54-L56) - `faqs()` swallows `OSError` and `ValueError`, making `health()` return `ok: true` on missing or malformed `qa_data.json`.
 - **unchecked** `:` [apps/voice/index.html](file:///E:/final_proj/mice/code/.staging/apps/voice/index.html) - Fine on 360px.
 - **unchecked** `:` [apps/voice/index.html:94](file:///E:/final_proj/mice/code/.staging/apps/voice/index.html#L94) - UI prepends `"Saved answers: "` to `parts.faq` which already contains `"saved answers"`, rendering duplicate label text.
 - **unchecked** `:` [main_python/main.py:4208](file:///E:/final_proj/mice/code/.staging/main_python/main.py#L4208) - Hub uses unpooled `ThreadingHTTPServer`; 180 s proxy timeout holds transient thread, not pooled worker.
 - **unchecked** `:` [main_python/main.py:146](file:///E:/final_proj/mice/code/.staging/main_python/main.py#L146-L147) - `voice_service_url()` swallows `Exception`, causing `voice_proxy()` at [main_python/main.py:3039](file:///E:/final_proj/mice/code/.staging/main_python/main.py#L3039-L3041) to report missing address in
 - **unchecked** `:` [main_python/main.py:3048](file:///E:/final_proj/mice/code/.staging/main_python/main.py#L3048-L3054) - Proxy forwards only `Content-Type` and POST body; other request headers, methods, and helper response headers are dropped.
