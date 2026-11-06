# Automatic Tutorial Creator

Record one application window, mark the useful steps, and cut a checked demo
under 90 seconds. Each take keeps its original recording and timestamp markers.

Development build. Linux X11/XWayland is the first implemented capture backend;
native Wayland and Windows capture are not yet implemented or verified.
Higgs TTS3 narration and native computer-use step dispatch are implemented;
see VERIFICATION.md for tested scope and remaining checks.

## Workflow

1. Ask Hermes to list capture sources. Select the exact application window and,
   optionally, one application audio stream.
2. Start a bounded take, then mark steps while demonstrating the application.
3. Stop the take. Select start/duration ranges from its timeline.
4. Export: the tool creates a new H.264/yuv420p MP4, measures its duration, and
   decodes it fully to check for errors. Combined clips may total at most89 seconds.
5. Read the exported timeline. Recorded markers are mapped through the cuts;
   sample frames at relevant timestamps and inspect them before describing a step.
6. Supply narration cues with `start`, `end`, and `text` in **export seconds**.
   Higgs generates each short cue; actual audio duration must fit its allotted
   interval. An overrun returns a timing-revision report without cutting or
   accelerating the voice. Unchanged cues are cached across revisions.
7. The narrated MP4 retains application audio, ducking it under speech. It includes
   separate SRT captions and a credit file. Captions are timed by speech segment;
   the local Higgs adapter does not claim word-level alignment.

`tutorial_step` invokes one `computer_use` action through Hermes's public dispatch,
after recapturing the exact recorded window in the same Hermes session and X11 display, then returns a fresh capture. Host approvals remain in force, and denied actions are returned without claiming success. Supply the recording window ID in `observe`. Element-index actions are not supported after recapture; use coordinates from a fresh observation. The plugin rejects overlapping tutorial steps in its own process. Coordinate other computer-use calls and processes separately: the host target is sticky and the preflight plus action are not atomic. The model must inspect the resulting state before narrating success.
The step label records an attempt, not an independently verified UI outcome.

Keep the window visible and uncovered: X11 capture is not an occlusion-safe GPU
capture mechanism. Native Wayland windows do not appear in the X11 inventory.
Window resizing/minimizing during capture is unsupported. Markers use FFmpeg's
media clock, refreshed approximately twice per second; they are not frame-exact.

Optional audio captures one selected PulseAudio/PipeWire playback stream. It is
temporarily routed to a private null sink and restored afterwards. You will not
hear that stream during recording. New/replaced streams are not automatically
included. The plugin never selects the microphone or system monitor by default.

## Requirements and installation

Python3.11+, FFmpeg with x11grab/libx264, ffprobe, xwininfo. Application audio also
requires pactl and a working PulseAudio-compatible server. Install these with
your normal package manager. The plugin downloads nothing.

Install this directory through Hermes's normal local plugin installation flow.
No API key is required for capture and editing. Persistent takes live in the
active profile's plugin-data/automatic-tutorial-creator directory. Only one take per profile
may run at once; the worker auto-stops within ten minutes plus bounded shutdown.

## Higgs setup

Use your existing local SGLang-Omni Higgs TTS3 service. In plugin settings, set
`higgs_url` to its loopback origin, `higgs_model` to the served model ID, and
optionally a voice name. The plugin never starts the service, downloads weights
or reads provider credentials. The API adapter requests a bounded WAV response
from `/v1/audio/speech`; remote origins and redirects are refused.

Each cue is limited to300 characters and60 words because earlier local Higgs
evaluation found unreliable long-turn synthesis. Those limits reduce exposure;
they do not prove the spoken transcript is correct. Listen before publishing.

An optional user-selected local WAV/FLAC/MP3 reference and transcript may be
configured; it must be allowed by the server too. Reference bytes are hashed so
changes invalidate cached speech. Set `higgs_revision` to the model revision and
change it when replacing the server weights. No reference clips are shipped.

Higgs model licensing is separate from this plugin's code. The published model's
Creator Use Grant permits qualifying creator content with Boson attribution;
other uses may require a separate license. Every narrated export writes the
credit alongside the video for its description. See the
[model card and license](https://huggingface.co/bosonai/higgs-tts-3-4b).

## Disclosure

Runs local xwininfo, FFmpeg, ffprobe and optional pactl commands, without a shell.
Reads window titles, window pixels, and only the audio stream explicitly selected.
Starts one bounded background recording worker per take. Stores video, audio,
markers and process receipts locally. Narration sends the supplied script and
optional reference-file path/transcript to the configured loopback Higgs server;
the reference file is read to hash and validate it. Computer-use steps invoke the
host's existing tool and can change the selected application as requested.
No telemetry, external service calls, self-update, credential access or automatic
publication. Abrupt SIGKILL/power loss may leave an
unfinished MKV and audio routing requiring manual recovery; status reports this.
Recorded private content must be reviewed before any publication.

GPL-3.0-or-later. See LICENSE. Other applications and codecs keep their own licenses.
