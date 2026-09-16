# Panel review - 2026-08-25 11:41

**Question.** Post-QC review of A21-8 report translation BEFORE promotion. QC green 2676/0 at 2026-08-25 02:01. Claims: 1) staging main_python/main.py /api/report translates report text to English via voice app POST http://127.0.0.1:8767/translate timeout 10, stores text_en beside the untouched original text, failure keeps original silently; 2) new staging tools/reports.py prints open reports in English for a work session, ASCII-only text skips translation, unreachable service prints translation-unavailable rather than guessing; 3) staging main_python/web/hub.html report list previews text_en when present, detail shows Original plus English blocks, closeReport re-enables Send button. Files are in the STAGING tree named .staging - read them there, not the main tree. What is NOT true, what breaks, what did we miss? Numbered findings only.

**Files.** main.py, reports.py, hub.html
**Cost.** 357005 tokens across 3 models

## The head reviewer (gemini-3.1-pro-high)

 - **real** `main_python/main.py:3847` GET /api/reports translates sequentially, 10s timeout per report hangs UI when voice service is down
 - **real** `main_python/main.py:3806` POST /api/report omits translation, forces GET /api/reports to re-translate every report
 - **real** `main_python/main.py:3899` saves status using f.write_text, risks file corruption instead of using safe write_atomic
 - **real** `main_python/main.py:3860` assigns (translation unavailable) on failure, UI list preview shows error string instead of original text
 - **real** `main_python/main.py:3850` hardcodes http://127.0.0.1:8767/translate instead of calling voice_service_url(), breaks if config/voice.json changes
 - **real** `tools/reports.py:15` hardcodes http://127.0.0.1:8767/translate, breaks if config/voice.json changes
 - **real** `main_python/web/hub.html:1066` duplicates closeReport definition, hoisted second function silently overrides line 900
 - **real** `main_python/web/hub.html:1011` overrides reportTitle, closeReport skips resetting it for new reports

## What each model said

### gemini-3.1-pro-high  _(221.6s, 129497 tokens)_

 - **real** `main_python/main.py:3795` POST /api/report lacks translation logic, breaks claim that translation happens at submission
 - **real** `main_python/main.py:3847` computes text_en during GET, wastes compute because it never stores result beside original text
 - **real** `main_python/main.py:3860` assigns (translation unavailable) on failure, exposes failure instead of keeping original text silently
 - **maybe** `main_python/main.py:3899` saves status using f.write_text, risks file corruption instead of using safe write_atomic
 - **fine** `tools/reports.py:1` It is fine.
 - **real** `main_python/web/hub.html:1011` overrides reportTitle, breaks UI because closeReport skips resetting it for new reports
 - **maybe** `main_python/web/hub.html:1066` duplicates closeReport definition, overwrites line 900 logic silently

### gemini-3.7-flash-high  _(154.6s, 157823 tokens)_

 - **unchecked** `:` 1. [`main.py:3806-3831`](file:///E:/final_proj/mice/code/.staging/main_python/main.py#L3806-L3831): `POST /api/report` does not call translation or save `text_en` to report JSON; claim 1 is false.
 - **unchecked** `:` 2. [`main.py:3846-3857`](file:///E:/final_proj/mice/code/.staging/main_python/main.py#L3846-L3857): `GET /api/reports` translates each report sequentially on every request; 10s timeout per report hangs complaints UI when voice service is down.
 - **unchecked** `:` 3. [`main.py:3859-3860`](file:///E:/final_proj/mice/code/.staging/main_python/main.py#L3859-L3860): `GET /api/reports` sets `text_en` to `"(translation unavailable)"` on failure instead of keeping original text; causes `hub.html:992` list preview to show the error string instead of report text.
 - **unchecked** `:` 4. [`main.py:3850`](file:///E:/final_proj/mice/code/.staging/main_python/main.py#L3850) and [`reports.py:15`](file:///E:/final_proj/mice/code/.staging/tools/reports.py#L15): hardcode `http://127.0.0.1:8767/translate` instead of calling `voice_service_url()`; breaks if port or host in `config/voice.j
 - **unchecked** `:` 5. [`main.py:3846`](file:///E:/final_proj/mice/code/.staging/main_python/main.py#L3846): `GET /api/reports` lacks ASCII check; translates English text unnecessarily and times out on unreachable voice service.
 - **unchecked** `:` 6. [`reports.py:67`](file:///E:/final_proj/mice/code/.staging/tools/reports.py#L67): re-translates `text` on every run instead of reading existing `text_en`; causes repeated slow translation calls.
 - **unchecked** `:` 7. [`hub.html:900`](file:///E:/final_proj/mice/code/.staging/main_python/web/hub.html#L900) and [`hub.html:1066`](file:///E:/final_proj/mice/code/.staging/main_python/web/hub.html#L1066): duplicate `closeReport()` function definition; hoisted second definition overrides first.
 - **unchecked** `:` 8. [`hub.html:1011`](file:///E:/final_proj/mice/code/.staging/main_python/web/hub.html#L1011) and [`hub.html:1066`](file:///E:/final_proj/mice/code/.staging/main_python/web/hub.html#L1066): `openComplaintDetail()` sets modal title to `📋 Complaint detail` and `closeReport()` never restores it; subseq
