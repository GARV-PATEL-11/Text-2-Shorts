"""
narration.py - turn English narration into audio + per-word timings with Amazon Polly or Google Cloud TTS.

NARRATION_ENGINE (default "silent"):
    silent  no audio; word timings estimated from the speaking speed (fast layout previews, no credentials)
    polly   Amazon Polly via boto3. Standard AWS credentials; AWS_REGION (default us-east-1).
            POLLY_ENGINE=neural (default, exact word timings from speech marks) | generative (estimated timings)
    google  Google Cloud TTS via google-cloud-texttospeech (v1beta1 API). Application Default Credentials.
            GOOGLE_VOICE_TIER=neural2 (default, exact timings from SSML marks) | chirp3_hd (estimated timings)

Results are cached by content hash in NARRATION_CACHE (default ./narration_cache).
Verify every voice id against your accounts with:  python narration.py --check-voices
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import wave
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape


@dataclass
class Word:
    text: str
    start: float
    end: float


@dataclass
class Clip:
    text: str
    duration: float
    words: list[Word]
    audio: str | None = None
    exact_timings: bool = False


@dataclass
class Chunk:
    lines: list[list[int]]          # word indices per line
    start: float
    end: float

    @property
    def indices(self):
        return [i for line in self.lines for i in line]


SENTENCE_END = re.compile(r"[.!?]+[\"')\]]*$")
CLAUSE_END = re.compile(r"[,;:\u2014-]$")


def tokens(text: str) -> list[str]:
    return text.split()


# --------------------------------------------------------------------------- voice resolution

SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


class Voice:
    def __init__(self, t: dict):
        v, spd, tone = t["voice"], t["speaking_speed"], t["narration_tone"]
        self.id, self.language_code = v["id"], v["language_code"]
        self.polly_id, self.polly_newscaster = v["polly"]["voice_id"], v["polly"]["newscaster"] and tone["polly_newscaster"]
        self.google = v["google"]
        self.rate = spd["rate"]
        self.wpm = spd["base_wpm"] * spd["rate"]
        self.pause = spd["sentence_pause_ms"] / 1000

    def _sentences(self, text):
        return [s for s in SENTENCE_SPLIT.split(text.strip()) if s]

    def polly_ssml(self, text: str, engine: str) -> str:
        brk = f'<break time="{int(self.pause * 1000)}ms"/>'
        body = brk.join(escape(s) for s in self._sentences(text))
        body = f'<prosody rate="{round(self.rate * 100)}%">{body}</prosody>'
        if self.polly_newscaster and engine == "neural":
            body = f'<amazon:domain name="news">{body}</amazon:domain>'
        return f"<speak>{body}</speak>"

    def google_ssml(self, text: str) -> str:
        """One <mark> before every whitespace token, so timepoints give each word's start."""
        out, i = [], 0
        brk = f'<break time="{int(self.pause * 1000)}ms"/>'
        for si, sent in enumerate(self._sentences(text)):
            words = []
            for w in sent.split():
                words.append(f'<mark name="w{i}"/>{escape(w)}')
                i += 1
            out.append(" ".join(words))
        return "<speak>" + brk.join(out) + "</speak>"


# --------------------------------------------------------------------------- timing helpers

def estimate_words(text: str, voice: Voice) -> tuple[list[Word], float]:
    """Spread words over time by length, with pauses at clause and sentence ends."""
    toks = tokens(text)
    if not toks:
        return [], 0.0
    sec_per_word = 60.0 / voice.wpm
    avg_len = sum(len(w) for w in toks) / len(toks)
    words, t = [], 0.15
    for w in toks:
        dur = sec_per_word * (0.55 + 0.45 * len(w) / avg_len)
        words.append(Word(w, t, t + dur))
        t += dur
        if SENTENCE_END.search(w):
            t += voice.pause
        elif CLAUSE_END.search(w):
            t += voice.pause * 0.4
    return words, t + 0.1


def fit_to_duration(words: list[Word], est: float, actual: float) -> list[Word]:
    k = actual / est if est else 1.0
    return [Word(w.text, w.start * k, w.end * k) for w in words]


def _norm(s: str) -> str:
    return re.sub(r"[\W_]+", "", s.lower())


def align_boundaries(toks: list[str], events: list[tuple[str, float, float]]) -> list[Word] | None:
    """Map engine word-boundary events (text, start, duration) onto our whitespace tokens, in order."""
    out, ei = [], 0
    for tok in toks:
        target = _norm(tok)
        if not target:      # pure punctuation token: attach to previous word's end
            prev = out[-1].end if out else 0.0
            out.append(Word(tok, prev, prev))
            continue
        got, start, end = "", None, None
        while ei < len(events) and len(got) < len(target):
            txt, s, d = events[ei]
            ei += 1
            if not _norm(txt):
                continue
            start = s if start is None else start
            end = s + d
            got += _norm(txt)
        if start is None:
            return None
        out.append(Word(tok, start, end))
    return out


def wav_duration(path: str) -> float:
    with wave.open(path) as w:
        return w.getnframes() / float(w.getframerate())


def audio_duration(path: str) -> float:
    if path.endswith(".wav"):
        return wav_duration(path)
    from pydub import AudioSegment
    return len(AudioSegment.from_file(path)) / 1000.0


# --------------------------------------------------------------------------- engines

def _ends_from_starts(toks, starts, duration):
    """Engines give word start times; a word ends when the next starts (capped for pauses)."""
    words = []
    for i, (tok, s) in enumerate(zip(toks, starts)):
        nxt = starts[i + 1] if i + 1 < len(starts) else duration
        words.append(Word(tok, s, min(nxt, s + 0.25 + 0.09 * len(tok))))
    return words


class Narrator:
    def __init__(self, t: dict, engine: str | None = None, cache_dir: str | None = None):
        self.t = t
        self.voice = Voice(t)
        self.engine = (engine or os.environ.get("NARRATION_ENGINE", "silent")).lower()
        if self.engine not in ("silent", "polly", "google"):
            raise ValueError(f"NARRATION_ENGINE must be silent, polly or google (got '{self.engine}')")
        self.polly_engine = os.environ.get("POLLY_ENGINE", "neural")
        self.google_tier = os.environ.get("GOOGLE_VOICE_TIER", "neural2")
        self.cache = Path(cache_dir or os.environ.get("NARRATION_CACHE", "narration_cache"))

    def _key(self, text: str) -> str:
        v = self.voice
        raw = json.dumps([self.engine, self.polly_engine, self.google_tier, v.id, v.rate, v.pause,
                          v.polly_newscaster, text])
        return hashlib.sha1(raw.encode()).hexdigest()[:16]

    def speak(self, text: str) -> Clip:
        key = self._key(text)
        meta = self.cache / f"{key}.json"
        if meta.exists():
            d = json.loads(meta.read_text(encoding="utf-8"))
            if d["audio"] is None or Path(d["audio"]).exists():
                return Clip(d["text"], d["duration"], [Word(**w) for w in d["words"]], d["audio"], d["exact"])
        self.cache.mkdir(parents=True, exist_ok=True)
        clip = getattr(self, f"_{self.engine}")(text, self.cache / key)
        meta.write_text(json.dumps({"text": clip.text, "duration": clip.duration, "audio": clip.audio,
                                    "exact": clip.exact_timings, "words": [w.__dict__ for w in clip.words]}),
                        encoding="utf-8")
        return clip

    def _estimated(self, text, audio_path, duration=None) -> Clip:
        words, est = estimate_words(text, self.voice)
        if duration is not None:
            words = fit_to_duration(words, est, duration)
        return Clip(text, duration if duration is not None else est, words, audio_path, False)

    def _silent(self, text, stem) -> Clip:
        return self._estimated(text, None)

    # -- Amazon Polly
    def _polly(self, text, stem) -> Clip:
        import boto3
        v, engine = self.voice, self.polly_engine
        client = boto3.client("polly", region_name=os.environ.get("AWS_REGION", "us-east-1"))
        ssml = v.polly_ssml(text, engine)
        common = dict(Text=ssml, TextType="ssml", VoiceId=v.polly_id, Engine=engine, LanguageCode=v.language_code)
        out = f"{stem}.mp3"
        audio = client.synthesize_speech(OutputFormat="mp3", SampleRate="24000", **common)
        Path(out).write_bytes(audio["AudioStream"].read())
        duration = audio_duration(out)
        path = str(Path(out).resolve())
        if engine == "generative":          # speech marks are not offered for generative voices
            return self._estimated(text, path, duration)
        marks = client.synthesize_speech(OutputFormat="json", SpeechMarkTypes=["word"], **common)
        events = [json.loads(line) for line in marks["AudioStream"].read().decode("utf-8").splitlines() if line.strip()]
        starts = [e["time"] / 1000 for e in events if e.get("type") == "word"]
        texts = [e["value"] for e in events if e.get("type") == "word"]
        evs = [(txt, s, 0.0) for txt, s in zip(texts, starts)]
        words = align_boundaries(tokens(text), evs)
        if words is None:
            return self._estimated(text, path, duration)
        return Clip(text, duration, _ends_from_starts([w.text for w in words], [w.start for w in words], duration), path, True)

    # -- Google Cloud TTS
    def _google(self, text, stem) -> Clip:
        from google.cloud import texttospeech_v1beta1 as tts
        v, tier = self.voice, self.google_tier
        client = tts.TextToSpeechClient()
        name = v.google[tier]
        exact = tier == "neural2"
        synth_input = tts.SynthesisInput(ssml=v.google_ssml(text)) if exact else tts.SynthesisInput(text=text)
        request = tts.SynthesizeSpeechRequest(
            input=synth_input,
            voice=tts.VoiceSelectionParams(language_code=v.language_code, name=name),
            audio_config=tts.AudioConfig(audio_encoding=tts.AudioEncoding.MP3, speaking_rate=v.rate),
            enable_time_pointing=[tts.SynthesizeSpeechRequest.TimepointType.SSML_MARK] if exact else [])
        resp = client.synthesize_speech(request=request)
        out = f"{stem}.mp3"
        Path(out).write_bytes(resp.audio_content)
        duration = audio_duration(out)
        path = str(Path(out).resolve())
        toks = tokens(text)
        marks = {tp.mark_name: tp.time_seconds for tp in resp.timepoints}
        if not exact or len(marks) < len(toks):
            return self._estimated(text, path, duration)
        starts = [marks[f"w{i}"] for i in range(len(toks))]
        return Clip(text, duration, _ends_from_starts(toks, starts, duration), path, True)


def check_voices(library_path=None) -> int:
    """Confirm every voice id in elements.json exists on Polly and Google with your credentials."""
    lib = json.loads(Path(library_path or Path(__file__).with_name("elements.json")).read_text())
    voices = lib["elements"]["voice"]["variants"]
    bad = 0
    try:
        import boto3
        polly = boto3.client("polly", region_name=os.environ.get("AWS_REGION", "us-east-1"))
        for v in voices:
            avail = {x["Id"]: x["SupportedEngines"] for x in
                     polly.describe_voices(LanguageCode=v["language_code"])["Voices"]}
            ok = "neural" in avail.get(v["polly"]["voice_id"], [])
            gen = "generative" in avail.get(v["polly"]["voice_id"], [])
            print(f"polly  {v['id']:18} {v['polly']['voice_id']:8} neural={'yes' if ok else 'NO'} generative={'yes' if gen else 'no'}")
            bad += not ok
    except Exception as e:
        print(f"polly  skipped: {e}")
    try:
        from google.cloud import texttospeech_v1beta1 as tts
        client = tts.TextToSpeechClient()
        cache = {}
        for v in voices:
            lc = v["language_code"]
            if lc not in cache:
                cache[lc] = {x.name for x in client.list_voices(language_code=lc).voices}
            for tier, name in v["google"].items():
                ok = name in cache[lc]
                print(f"google {v['id']:18} {name:26} {'ok' if ok else 'MISSING'}")
                bad += not ok
    except Exception as e:
        print(f"google skipped: {e}")
    return 1 if bad else 0


# --------------------------------------------------------------------------- subtitle chunking

def chunk_words(words: list[Word], max_chars: int, max_lines: int) -> list[Chunk]:
    """Greedy line filling; a chunk ends when full or at a sentence end once it is at least half full."""
    chunks, lines, line, line_len = [], [], [], 0

    def close_chunk():
        nonlocal lines
        if lines:
            idx = [i for ln in lines for i in ln]
            chunks.append(Chunk(lines, words[idx[0]].start, words[idx[-1]].end))
            lines = []

    for i, w in enumerate(words):
        add = len(w.text) + (1 if line else 0)
        if line and line_len + add > max_chars:
            lines.append(line)
            line, line_len = [], 0
            if len(lines) >= max_lines:
                close_chunk()
            add = len(w.text)
        line.append(i)
        line_len += add
        full_enough = (len(lines) * max_chars + line_len) >= 0.5 * max_chars * max_lines
        if SENTENCE_END.search(w.text) and full_enough:
            lines.append(line)
            line, line_len = [], 0
            close_chunk()
    if line:
        lines.append(line)
    close_chunk()
    for a, b in zip(chunks, chunks[1:]):   # hold each chunk until the next begins (no flicker)
        a.end = b.start
    return chunks


if __name__ == "__main__":
    if "--check-voices" in sys.argv:
        sys.exit(check_voices())
    print(__doc__)
