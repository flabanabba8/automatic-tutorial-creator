"""Hermes tools for controlled local demonstration recording."""
import json
import os
import threading
from pathlib import Path
from .core import Director, sources
from .narration import narrate


_step_lock = threading.Lock()

TOOLS = {
    'capture_sources': ('List local X11 windows and application audio streams. Native Wayland windows are not supported.', {
        'display': {'type': 'string', 'description': 'Optional local X11 display, such as :0.'}}, []),
    'capture_start': ('Start recording one selected visible X11 window. Optionally route ONE explicitly selected audio stream into a temporary recording sink; playback is muted until recording stops. Recording stops automatically at max_seconds.', {
        'window_id': {'type': 'string', 'description': 'Hex window ID returned by capture_sources.'},
        'display': {'type': 'string'}, 'max_seconds': {'type': 'number', 'minimum': 1, 'maximum': 600},
        'audio_stream': {'type': 'integer', 'minimum': 0, 'description': 'Optional exact audio stream ID returned by capture_sources; omitted means silent video.'}}, ['window_id']),
    'capture_status': ('Read recording state, media duration and step markers.', {'job_id': {'type': 'string'}}, ['job_id']),
    'capture_mark': ('Mark a demonstration step on the current media timeline, approximately half-second precision.', {
        'job_id': {'type': 'string'}, 'label': {'type': 'string', 'maxLength': 160}}, ['job_id', 'label']),
    'capture_stop': ('Stop this plugin-owned recording and restore its selected audio route.', {'job_id': {'type': 'string'}}, ['job_id']),
    'capture_export': ('Cut ordered segments from a completed recording into a checked H.264 MP4, at most 89 seconds. Original recording is preserved.', {
        'job_id': {'type': 'string'}, 'segments': {'type': 'array', 'minItems': 1, 'maxItems': 20, 'items': {
            'type': 'object', 'properties': {'start': {'type': 'number', 'minimum': 0}, 'duration': {'type': 'number', 'minimum': .1}},
            'required': ['start', 'duration'], 'additionalProperties': False}}}, ['job_id', 'segments']),
    'tutorial_timeline': ('Read source-video or exported-video timestamps, including the mapping of recorded step markers through the chosen cuts.', {
        'job_id': {'type': 'string'}, 'export_name': {'type': 'string'}}, ['job_id']),
    'tutorial_frame': ('Decode a frame at a requested export timestamp so the agent can inspect what actually appears before writing narration. Returns a local PNG path; no image model is called.', {
        'job_id': {'type': 'string'}, 'export_name': {'type': 'string'}, 'seconds': {'type': 'number', 'minimum': 0}}, ['job_id', 'export_name', 'seconds']),
    'tutorial_narrate': ('Generate timestamped narration with your configured, already-running local Higgs TTS3 server and mix it into a completed export. Measures every clip, refuses overruns without speeding/cutting speech, caches unchanged cues, and writes segment captions plus the Boson credit. Does not start or install a model.', {
        'job_id': {'type': 'string'}, 'export_name': {'type': 'string'}, 'cues': {'type': 'array', 'minItems': 1, 'maxItems': 20,
            'items': {'type': 'object', 'properties': {'start': {'type': 'number'}, 'end': {'type': 'number'}, 'text': {'type': 'string', 'maxLength': 300}},
                      'required': ['start', 'end', 'text'], 'additionalProperties': False}}}, ['job_id', 'export_name', 'cues']),
    'tutorial_step': ('Perform ONE computer-use action through Hermes\'s native tool, with its approvals unchanged, while a take is recording. Mark the attempt on the media timeline and return a fresh capture for verification. A tool acknowledgment is not proof the intended UI result occurred. Use only for the user-authorized tutorial task and the selected app.', {
        'job_id': {'type': 'string'}, 'label': {'type': 'string', 'maxLength': 160},
        'action': {'type': 'object', 'description': 'Arguments for the existing computer_use tool; use its current schema and a freshly observed target.'},
        'observe': {'type': 'object', 'description': 'Explicit app and window_id matching the recording; optional pid and capture mode.'}}, ['job_id', 'label', 'action', 'observe']),
}


def invoke(name, args, ctx=None, **kwargs):
    from plugins.plugin_storage import plugin_data_dir
    try:
        if name == 'capture_sources':
            result = sources(**args)
        elif name == 'tutorial_narrate':
            result = narrate(plugin_data_dir('automatic-tutorial-creator'), **args, settings=ctx.get_config() or {})
        elif name == 'tutorial_step':
            return step(ctx, Director(plugin_data_dir('automatic-tutorial-creator')), **args, **kwargs)
        else:
            director = Director(plugin_data_dir('automatic-tutorial-creator'))
            method = {'tutorial_timeline': 'timeline', 'tutorial_frame': 'frame'}.get(name, name.removeprefix('capture_'))
            result = getattr(director, method)(**args)
        return json.dumps(result)
    except (ValueError, TypeError, RuntimeError, OSError) as exc:
        return json.dumps({'error': str(exc)})


def step(ctx, director, job_id, label, action, observe, **kwargs):
    if not _step_lock.acquire(blocking=False):
        raise RuntimeError('Another tutorial step is in progress; wait for it to finish')
    try:
        return _step(ctx, director, job_id, label, action, observe, **kwargs)
    finally:
        _step_lock.release()


def _step(ctx, director, job_id, label, action, observe, **kwargs):
    if not isinstance(action, dict) or action.get('action') not in {'click', 'double_click', 'right_click', 'middle_click', 'drag', 'scroll', 'type', 'key', 'wait'}:
        raise ValueError('Choose one supported computer-use action')
    if any(action.get(k) is not None for k in ('element', 'from_element', 'to_element')):
        raise ValueError('Element-index actions are unsupported after target recapture; use freshly observed coordinates')
    if not isinstance(observe, dict) or not isinstance(observe.get('app'), str) or not observe['app'].strip():
        raise ValueError('Supply the explicit application name for the verification capture')
    if observe['app'].strip().lower() in ('screen', 'desktop'):
        raise ValueError('Observe the selected application, not the entire desktop')
    if action.get('app', observe['app']) != observe['app']:
        raise ValueError('The action and observation must target the same application')
    session_id = kwargs.get('session_id') or getattr(kwargs.get('parent_agent'), 'session_id', None)
    if not isinstance(session_id, str) or not session_id:
        raise ValueError('A Hermes session ID is required for isolated computer use')
    if director.status(job_id).get('state') != 'recording':
        raise ValueError('A recording must be active before a tutorial action')
    request = json.loads((director.job(job_id) / 'request.json').read_text())
    if request.get('display') != os.environ.get('DISPLAY'):
        raise ValueError('The recording and computer-use session must use the same X11 display')
    selected = request.get('window_id')
    supplied = observe.get('window_id')
    if isinstance(supplied, str):
        try: supplied = int(supplied, 0)
        except ValueError: raise ValueError('Use the recording window ID') from None
    if isinstance(supplied, bool) or not isinstance(supplied, int) or supplied != selected:
        raise ValueError('Observation window ID must match the recorded window')
    if action.get('window_id', selected) != selected:
        raise ValueError('Action window ID must match the recorded window')
    if observe.get('pid') is not None and (type(observe['pid']) is not int or observe['pid'] < 1):
        raise ValueError('PID must be a positive integer')
    target = {'app': observe['app'], 'window_id': selected}
    if observe.get('pid') is not None: target['pid'] = observe['pid']
    context = {k: kwargs[k] for k in ('parent_agent', 'task_id') if k in kwargs}
    context['session_id'] = session_id
    # Hermes input is delivered to a sticky target. Recapture the exact window
    # in the same session before dispatch; callers must avoid concurrent CUA calls.
    preflight = ctx.dispatch_tool('computer_use', {**target, 'action': 'capture', 'mode': 'ax'}, **context)
    try: captured = json.loads(preflight) if isinstance(preflight, str) else preflight
    except (TypeError, ValueError): return preflight
    if not isinstance(captured, dict) or captured.get('error') or captured.get('ok') is False or captured.get('mode') != 'ax':
        return preflight
    marker = director.mark(job_id, label)
    outcome = ctx.dispatch_tool('computer_use', {**action, 'app': observe['app']}, **context)
    try:
        result = json.loads(outcome) if isinstance(outcome, str) else outcome
    except (TypeError, ValueError):
        return outcome
    if not isinstance(result, dict): return outcome
    verdict = result.get('action_result') if isinstance(result.get('action_result'), dict) else result
    if verdict.get('error') or verdict.get('ok') is False or verdict.get('success') is False or verdict.get('status') in ('blocked', 'denied', 'cancelled', 'error'):
        return outcome
    if verdict.get('ok') is not True and verdict.get('success') is not True and verdict.get('status') not in ('success', 'completed', 'ok'):
        return outcome
    if result.get('_multimodal') is True and isinstance(result.get('content'), list):
        # The host already captured a frame after the action; preserve it without a second capture.
        note = {'marker': marker, 'action_acknowledged': True, 'verification': 'Review this fresh observation before narrating success'}
        summary = json.dumps({'tutorial_step': note})
        return {**result, 'content': [*result['content'], {'type': 'text', 'text': summary}],
                'text_summary': (str(result.get('text_summary') or '') + '\n' + summary).strip()}
    followup = {**target, 'action': 'capture'}
    if 'mode' in observe: followup['mode'] = observe['mode']
    capture = ctx.dispatch_tool('computer_use', followup, **context)
    try:
        observed = json.loads(capture) if isinstance(capture, str) else capture
    except (TypeError, ValueError):
        return capture
    if isinstance(observed, dict):
        note = {'marker': marker, 'action_acknowledged': True, 'verification': 'Review this fresh observation before narrating success'}
        if observed.get('_multimodal') is True and isinstance(observed.get('content'), list):
            # Keep native image blocks structured; never stringify image data into text.
            summary = json.dumps({'tutorial_step': note})
            return {**observed, 'content': [*observed['content'], {'type': 'text', 'text': summary}],
                    'text_summary': (str(observed.get('text_summary') or '') + '\n' + summary).strip()}
        observed['tutorial_step'] = note
        return json.dumps(observed)
    return capture


def register(ctx):
    ctx.register_skill('create-tutorial', Path(__file__).parent / 'skills/create-tutorial/SKILL.md')
    for name, (description, properties, required) in TOOLS.items():
        schema = {'name': name, 'description': description, 'parameters': {
            'type': 'object', 'properties': properties, 'required': required, 'additionalProperties': False}}
        ctx.register_tool(name=name, toolset='tutorial_creator', schema=schema,
                          handler=lambda args, _name=name, **kwargs: invoke(_name, args, ctx, **kwargs))
