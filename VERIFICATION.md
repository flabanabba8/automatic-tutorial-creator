# Automatic Tutorial Creator verification

Development checks on2026-11-05. Nothing published or installed into a user's
active Hermes profile. No Windows/native-Wayland support claim.

## Passed

- Mixed-case protected-directory fixtures passed on Linux; no real credentials were used. This is not a full platform or publication audit.

- Catalog validation for the capture/timeline/narration/computer-use tool package:
  manifest, isolated registration, declared tools, security and no core overrides.
- Real isolated Xvfb application capture using original animated video and a sine
  tone: selected window recorded; selected audio stream captured; marker timestamp
  advanced; recording stopped; the original audio route was restored; exported
  video and audio decoded. No desktop contents or other app audio were recorded.
- Invalid duration/display/ID boundaries and cue overlap/length rejection.
- Multi-cut export with markers mapped onto the edited timeline and a decoded
  timestamp frame. Frame-rate and approximately0.5-second marker quantization apply.
- Native computer-use dispatch fixture: a denied action stays denied, host context
  is forwarded, a successful action gets a fresh observation, and the returned
  observation still requires review. This is not a live desktop-control test.
- Additional private Katz, podcast and video rehearsals were captured and
  exported on isolated X11 displays with no host audio selected. Sampled frames
  were inspected; this did not exercise live Hermes computer-use actions or
  constitute complete visual or listening review.
- Local HTTP TTS fixture: requests, WAV duration checks, audio mixing/ducking,
  timed segment SRT, cache reuse and overrun rejection.
- Real local Higgs TTS3 at revision239f63fb7b02b1aa085f98d9efae5e35cc5523e8:
  one original narration sentence produced5.16 seconds of audio, placed at1.0s in
  a13.0-second synthetic test video. Complete export decoded and captions/credit
  were generated. Speech/export stage took2.4s after server readiness.
- The temporary Higgs server used existing cached weights, offline mode, the
  existing GPU lock, an11GiB RAM ceiling, no swap, and a10-minute lifetime cap.
  It stopped after synthesis. No other model service was adopted or stopped.

- Independent cached Whisper large-v3-turbo transcription matched the original
  narration sentence exactly. It ran after Higgs stopped, with a4GiB RAM cap;
  this is an ASR check, not a human listening-quality judgment. The first ASR
  invocation used an unavailable `whisper` package; the successful check used
  the already-installed Transformers pipeline documented by the source project.

## Remaining

- Full end-to-end tutorial of an actual application driven through a running
  Hermes computer-use backend, plus human/visual review of the finished demo.
- Subjective narration quality and more voices/languages. One short synthesis is
  not a guarantee against dropped/repeated words; captions are not word-aligned.
- Native Wayland and Windows capture. The existing Windows recorder is a research
  foundation, not a shipped or tested backend. Legion Go access is unresolved.
- Interruptions by power loss/SIGKILL can leave an MKV and require audio-route
  recovery. Graceful stop is covered; hard-kill recovery is not automated.
- Public content/history audit, install documentation review, demo publication,
  catalog submission and contest form.

Local receipts and synthetic media are in the contest workspace's ignored
evidence directory; they are not part of the plugin distribution.
