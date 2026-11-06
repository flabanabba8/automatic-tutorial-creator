"""Higgs TTS3 narration placed on an existing video's measured timeline."""
import hashlib
import json
import ipaddress
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
import uuid

from .core import Director, number, probe, run, write_json
from .loopback import LoopbackHTTPHandler
from .reference_paths import resolve_reference

CREDIT = "This audio was created with Boson AI's Higgs Audio — https://www.boson.ai/higgs-audio"


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def loopback_host(host):
    if host == 'localhost': return True
    try: return ipaddress.ip_address(host).is_loopback
    except (TypeError, ValueError): return False


def endpoint(base):
    parsed = urlsplit(base)
    if parsed.scheme != 'http' or not loopback_host(parsed.hostname) or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('', '/'):
        raise ValueError('Configure a loopback Higgs server origin, for example http://localhost:8000')
    return base.rstrip('/') + '/v1/audio/speech'


def synthesize(base, model, text, voice, reference_audio='', reference_text=''):
    url = endpoint(base)
    payload = {'model': model, 'input': text, 'voice': voice, 'response_format': 'wav', 'stream': False,
               'temperature': .8, 'top_k': 50, 'top_p': .8, 'max_new_tokens': 2048}
    if reference_audio:
        # The user's local server owns reference access; no voice files are bundled
        # or read by this client. Server-side allowlisting remains in force.
        payload['references'] = [{'audio_path': reference_audio, 'text': reference_text}]
    opener = build_opener(ProxyHandler({}), NoRedirect(), LoopbackHTTPHandler())
    try:
        with opener.open(Request(url, data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'}), timeout=120) as response:
            data = response.read(32 * 1024 * 1024 + 1)
    except HTTPError as exc:
        raise RuntimeError(f'Higgs returned HTTP {exc.code}; no automatic retry was made') from None
    except (URLError, TimeoutError):
        raise RuntimeError('Local Higgs server unavailable or timed out; start your configured server and retry explicitly') from None
    if len(data) > 32 * 1024 * 1024 or data[:4] != b'RIFF' or data[8:12] != b'WAVE':
        raise RuntimeError('Higgs did not return a bounded WAV file')
    return data


def validate_cues(cues, duration):
    if not isinstance(cues, list) or not 1 <= len(cues) <= 20:
        raise ValueError('Provide 1–20 timestamped narration cues')
    previous_end = 0
    total_text = 0
    for cue in cues:
        if not isinstance(cue, dict) or set(cue) != {'start', 'end', 'text'}:
            raise ValueError('Each cue needs exactly start, end and text')
        start = number(cue['start'], 0, duration, 'cue start')
        end = number(cue['end'], .1, duration, 'cue end')
        if start < previous_end or end <= start:
            raise ValueError('Cues must be ordered, non-overlapping and have positive duration')
        text = cue['text']
        if not isinstance(text, str) or not text.strip() or len(text) > 300 or len(text.split()) > 60:
            raise ValueError('Each Higgs cue must contain 1–300 characters and at most60 words')
        if '<|reset|>' in text or any(ord(c) < 32 and c not in '\n\t' for c in text):
            raise ValueError('Unsupported control text in narration')
        total_text += len(text)
        previous_end = end
    if total_text > 4000:
        raise ValueError('Narration script exceeds4000 characters')


def srt_time(seconds):
    ms = round(seconds * 1000)
    return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'


def narrate(root, job_id, export_name, cues, settings):
    director = Director(root)
    timeline = director.timeline(job_id, export_name)
    validate_cues(cues, timeline['seconds'])
    folder = director.job(job_id)
    base = settings.get('higgs_url', 'http://localhost:8000')
    endpoint(base)
    model = settings.get('higgs_model', 'bosonai/higgs-tts-3-4b')
    voice = settings.get('higgs_voice', 'default')
    reference_audio = settings.get('higgs_reference_audio', '')
    reference_text = settings.get('higgs_reference_text', '')
    reference_digest = ''
    if reference_audio:
        reference = resolve_reference(reference_audio, root)
        if reference.suffix.lower() not in ('.wav', '.flac', '.mp3') or not reference.is_file() or reference.stat().st_size > 20 * 1024 * 1024:
            raise ValueError('Choose a local WAV/FLAC/MP3 voice reference of at most20 MiB')
        if not any(s['codec_type'] == 'audio' for s in probe(reference)['streams']):
            raise ValueError('Voice reference has no audio stream')
        reference_audio = str(reference)
        reference_digest = hashlib.sha256(reference.read_bytes()).hexdigest()
    cache = folder / 'narration-cache'
    cache.mkdir(exist_ok=True, mode=0o700)
    rendered, problems = [], []
    for i, cue in enumerate(cues):
        key = hashlib.sha256(json.dumps([base, model, settings.get('higgs_revision', ''), voice, cue['text'], reference_audio, reference_digest, reference_text], ensure_ascii=False).encode()).hexdigest()
        audio = cache / (key + '.wav')
        reused = audio.exists()
        if not reused:
            data = synthesize(base, model, cue['text'], voice, reference_audio, reference_text)
            temporary = cache / (uuid.uuid4().hex + '.tmp')
            temporary.write_bytes(data)
            temporary.chmod(0o600)
            temporary.replace(audio)
        measured = float(probe(audio)['format']['duration'])
        available = cue['end'] - cue['start']
        rendered.append({'cue': i, 'start': cue['start'], 'end': cue['end'], 'text': cue['text'],
                         'measured_seconds': measured, 'cache_reused': reused, 'path': str(audio)})
        if measured > available + .02:
            problems.append({'cue': i, 'available_seconds': available, 'measured_seconds': measured,
                             'correction': 'Shorten this cue or allocate more time; speech was not cut or sped up.'})
    if problems:
        return {'state': 'needs_timing_revision', 'problems': problems,
                'cues': [{k: v for k, v in r.items() if k != 'path'} for r in rendered]}
    video = folder / export_name
    info = probe(video)
    has_audio = any(s['codec_type'] == 'audio' for s in info['streams'])
    output = folder / ('narrated-' + uuid.uuid4().hex + '.mp4')
    command = ['ffmpeg', '-v', 'error', '-nostdin', '-n', '-i', str(video)]
    filters, inputs = [], []
    for i, clip in enumerate(rendered, 1):
        command += ['-i', clip['path']]
        delay = round(clip['start'] * 1000)
        filters.append(f'[{i}:a]aresample=48000,adelay={delay}:all=1[n{i}]')
        inputs.append(f'[n{i}]')
    filters.append(''.join(inputs) + f'amix=inputs={len(inputs)}:normalize=0,apad,atrim=duration={timeline["seconds"]}[narration]')
    if has_audio:
        # Duck the application under narration and retain it between spoken cues.
        filters += ['[narration]asplit=2[voice][key]',
                    '[0:a][key]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=300[app]',
                    '[app][voice]amix=inputs=2:normalize=0,alimiter=limit=0.95:latency=1[a]']
    else:
        filters += ['[narration]alimiter=limit=0.95:latency=1[a]']
    command += ['-filter_complex', ';'.join(filters), '-map', '0:v:0', '-map', '[a]', '-map_metadata', '-1',
                '-c:v', 'copy', '-c:a', 'aac', '-b:a', '128k', '-t', str(timeline['seconds']), '-movflags', '+faststart', str(output)]
    try:
        run(command, timeout=240)
        final = probe(output)
        if float(final['format']['duration']) >= 90:
            raise RuntimeError('Narrated export exceeded the contest duration limit')
        run(['ffmpeg', '-v', 'error', '-xerror', '-nostdin', '-i', str(output), '-f', 'null', '-'], timeout=120)
    except Exception:
        output.unlink(missing_ok=True)
        raise
    captions = output.with_suffix('.srt')
    caption_lines = []
    for i, clip in enumerate(rendered, 1):
        text = re.sub(r'<\|[^|]+\|>', '', clip['text']).strip().replace('-->', '→')
        caption_lines.append(f'{i}\n{srt_time(clip["start"])} --> {srt_time(clip["start"] + clip["measured_seconds"])}\n{text}\n')
    captions.write_text('\n'.join(caption_lines), encoding='utf-8')
    result = {'state': 'complete', 'path': str(output), 'captions': str(captions), 'caption_timing': 'segment-level, measured audio duration; not word alignment',
              'seconds': float(final['format']['duration']), 'credit': CREDIT,
              'cues': [{k: v for k, v in r.items() if k != 'path'} for r in rendered]}
    write_json(output.with_suffix('.json'), result)
    output.with_suffix('.credit.txt').write_text(CREDIT + '\n', encoding='utf-8')
    return result
