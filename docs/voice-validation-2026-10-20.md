# Voice validation — 2026-10-20

Measured on the venue Windows PC and RTX 5070 Ti Laptop GPU. Audio inputs are synthetic speech, including the existing Thai corpus; microphone/room tests and real robot audio remain for the user. Timings are observations, not a network latency guarantee.

## Recording and replies

- Speech may last up to 30 seconds after onset. Waiting for speech has its own 10-second limit; empty recordings are discarded. A turn ends after 1.5 seconds of elapsed quiet.
- Stop cancels owned capture/playback and invalidates delayed robot work. Rapid Stop/Start cannot let an old callback change the next session.
- Conversation remains turn-taking. It waits while its answer or the rig is speaking; this does not establish simultaneous interruption or acoustic echo cancellation in a room.
- Saved social answers may require a whole short question, preventing a greeting inside a technical question from triggering a greeting move. Multilingual hours paraphrases use stored hours.

## Recognition

Production HTTP measurements: 76 requests over 19 clips, two repeats, fixed language and automatic detection. Nine English/Japanese/Chinese questions range from 1.92 to 10.39 seconds. Thai clean clips are 3, 5.016, 10 and 30 seconds, plus two noisy 15-second clips and silence at 0, 1, 5 and 30 seconds. All 36 multilingual hours answers selected the saved answer in the requested language. All 16 silence requests returned no words.

| Language / clean set | Fixed language median | Automatic median | Character error rate |
| --- | ---: | ---: | ---: |
| th | 0.953 s | 1.077 s | 0.88% |
| en | 0.387 s | 0.456 s | 0.00% |
| ja | 0.205 s | 0.320 s | 10.96% |
| zh | 0.236 s | 0.310 s | 4.00% |

Character error rate normalizes case, punctuation and whitespace, retaining Unicode marks. It includes Japanese kana/kanji and Chinese simplified/traditional differences; these are not human-adjudicated phonetic scores. These scripted samples do not establish general speech accuracy.

Thai 30-second recognition retained the tail: about 0.56% character errors versus 25% in the earlier single-window baseline. Ten-second batches and vocabulary context improved that case. English medium with repeat penalties disabled preserved repeated phrases; Japanese and Chinese retained the faster general model after comparison.

## Sound-ready HTTP pipeline

Sequential transcription → saved answer → complete audio response, one question per language. First and second requests below use the same answer. This excludes endpoint silence, browser transfer/playback start and speaker acoustics. Models are loaded.

| Language | First request | Cached request |
| --- | ---: | ---: |
| th | 1.593 s | 0.444 s |
| en | 1.161 s | 0.338 s |
| ja | 2.667 s | 0.270 s |
| zh | 1.414 s | 0.185 s |

Adding the configured 1.5-second endpoint pause gives an estimate of 1.69–1.94 seconds after speech ends for these cached examples, before browser playback overhead. Cold model startup and new network synthesis can be longer; the earlier cold pipeline was 5.47 seconds.

The visible fast device voice option races cached/server audio with an installed same-language voice after 650 ms. It preserves explicit/scenario/mixed voice choices and only uses the selected local provider. This PC exposes local English and Thai voices; Japanese and Chinese continue through the configured service. Real Edge browser smoke tests emitted start/end events for English and Thai, with about 0.62 seconds from the native speak call to onstart. The 650 ms selection timer alone is not time to audible speech.

All four complete MP3 replies were nonempty and survived speech-to-text round-trip in the requested language. Round-trip recognition had Thai ป้าย→ป้า and Japanese 日→び orthographic errors; without a human listening assessment these cannot identify a synthesizer defect.

## Regression evidence

Permanent checks cover deferred recorder stop, pauses, full 30-second capture, silence, microphone denial/loss, rapid restart, bounded status calls, stale robot speech/movement, one winning voice, selected overrides, mixed scripts, native failures/hangs, actual specialist CPU recovery, batch-memory fallback, model unload and synthesis concurrency. `tools/sabotage.py` deliberately removes fixes and restores them. Quick/full gate results are recorded in the pull request.
