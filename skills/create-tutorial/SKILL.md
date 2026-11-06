---
name: create-tutorial
description: Create a short recorded application tutorial using actual computer-use actions, timestamped step markers, local Higgs narration and checked video export.
---

Use Automatic Tutorial Creator's executable tools to demonstrate the user's
requested task in a real application. Choose a small, useful task that can be
shown clearly within89 seconds of edited footage.

1. Identify the application, intended outcome, allowed edits, and safe demo data.
   Use existing user authorization. Keep approval requirements for consequential
   app actions; recording does not authorize purchases, publication or messages.
2. Inspect the application with native computer use. Call `capture_sources` and
   select its exact visible X11/XWayland window. If audio is wanted, select only
   that application's listed audio stream. Explain that the stream is temporarily
   muted while captured. Native Wayland and Windows are not supported yet.
3. Start a bounded take. For each step, use the current `computer_use` schema and
   a freshly observed target in `tutorial_step`. Supply the same explicit app
   name and the exact recorded `window_id` for observation. Use fresh coordinates,
   not element indices, because the preflight recaptures the window. Run computer-use
   calls sequentially: target selection and action are not atomic. Read the returned
   fresh screen/tree before concluding that the action succeeded. A timestamp label records an attempt.
4. If a step fails or is blocked, preserve that outcome. Stop or correct the
   demonstration within the authorized task; never narrate success over a failure.
   Use `capture_mark` for meaningful manually demonstrated steps too.
5. Stop the take. Read its timeline and choose a concise sequence of actual
   source segments. Export with `capture_export`, totaling at most89 seconds.
   Disclose any compressed waiting or discontinuity that changes the impression
   of speed. Do not fabricate application results or pass fixtures off as live work.
6. Read `tutorial_timeline` for the exported video. Use `tutorial_frame` to sample
   relevant timestamps and inspect frames directly with native vision. Use the
   export clock for all narration; source-recording times change after cuts.
7. Write concise narration about the observed actions. Give `tutorial_narrate`
   ordered, non-overlapping cues with `start`, `end`, and `text`. The already-running
   local Higgs server is configured through plugin settings. Do not install models,
   start unrelated GPU jobs, or fall back to a paid provider automatically.
8. If a cue overruns, shorten that cue or revise its allocated interval. Reuse
   unchanged cached speech. Do not cut off or accelerate speech to hide an overrun.
   Listen/check the resulting narration; duration checks do not prove word accuracy.
9. Report the verified duration and file paths, caption timing limitations, and
   Boson credit file. The captions are measured segments, not word alignment.
   Review captured personal information before sharing. Publish only when the
   user has explicitly instructed publication to the particular destination.
