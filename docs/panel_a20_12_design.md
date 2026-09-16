# Panel review - 2026-08-24 01:34

**Question.** A20-12 pre-code brainstorm. Voice SETTINGS screens for a DESIGNER joining apps/voice/index.html. Data: config/voice.json has service url, faqThreshold 0.75, faqAskAgain 0.65, stt{enabled, model small, languages th/en each with bias words}, llm{enabled model maxTokens}, tts{enabled language voices}; qa_data.json has faqs[{questions[],answer,move?,module?(robot NAME)}]. Endpoints: hub proxies /api/voice/* to helper, GET /api/list kind=sequences lists yaml, GET /api/modules/all names robots, POST /api/voice/say speaks text aloud. Planned sections: Answers (add answer, ways people ask it, hear it, pick move and robot by clicking alone); Voice and language (on/off, voice pick with Try it, speech model as fast/balanced/most accurate); Words it gets wrong (one box, one Add); Advanced behind technical switch. Saving gated like /api/settings; changes reach the running helper with NO restart. QUESTIONS: 1) same page vs separate settings page - which serves a designer mid-event? 2) editing multi-question answers at 360px - what layout survives? 3) traps in a page writing voice.json through the helper? Answer in at most 14 lines.

**Files.** app.json, bench/cases.json, bench/run_bench.py, index.html, qa_data.json, service.py
**Cost.** 191951 tokens across 3 models

## The head reviewer (gemini-3.1-pro-high)

 - **real** `apps/voice/service.py:48` config read once, changes ignore NO restart requirement
 - **real** `apps/voice/service.py:115` STT instance cached, changing model ignores NO restart requirement
 - **real** `apps/voice/service.py:259` LLM instance cached, changing model ignores NO restart requirement
 - **fine** `apps/voice/service.py:517` fine

## What each model said

### gemini-3.1-pro-high  _(76.2s, 51451 tokens)_

 - **real** `apps/voice/service.py:49` config read only once, changes ignore NO restart requirement
 - **real** `apps/voice/service.py:115` STT instance cached, changing model ignores NO restart requirement
 - **real** `apps/voice/service.py:259` LLM instance cached, changing model ignores NO restart requirement
 - **real** `apps/voice/service.py:517` helper lacks password, saving here bypasses hub authentication

### gemini-3.7-flash-high  _(53.3s, 101671 tokens)_

 - **real** `E:/final_proj/mice/code/.staging/apps/voice/service.py:48` Brain.__init__ caches self.cfg once at startup; edits to config/voice.json never reach helper without reload
 - **real** `E:/final_proj/mice/code/.staging/apps/voice/service.py:116` _load_stt and _load_llm cache model instances; changing model requires explicit cache eviction
