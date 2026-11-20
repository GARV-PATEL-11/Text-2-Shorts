from app.narration import case_pairs, phrase_times, speakable, to_plain, to_ssml


def test_symbols_units_abbreviations_and_case():
    texts = ["The Sun's mass `M` pulls the planet's mass `m`.", "Here `a` and `b` meet `c`."]
    pairs = case_pairs(texts)
    assert pairs == {"m"}
    assert speakable(texts[0], pairs) == "The Sun's mass capital em pulls the planet's mass small em."
    assert speakable(texts[1], pairs) == "Here ay and bee meet see."
    assert (
        speakable("Earth is 1 AU away, e.g. 150 km/h or 9.8 m/s².")
        == "Earth is 1 astronomical units away, for example 150 kilometers per hour or 9.8 meters per second squared."
    )
    assert speakable("`r_1` + `θ` ≈ 3.14 and 5-2 = 3") == "ar 1 plus theta approximately 3.14 and 5 minus 2 equals 3"
    assert speakable("at 90° and 50%") == "at 90 degrees and 50 percent"


def test_pause_markers_become_ssml_breaks_or_ellipses():
    spoken = speakable("Look at this. [pause] Now `c` & more.")
    assert to_ssml(spoken) == '<speak>Look at this. <break time="600ms"/> Now see &amp; more.</speak>'
    assert to_plain(spoken) == "Look at this. … Now see & more."


def test_phrase_times_follow_word_marks_in_order():
    marks = [(word, i * 0.4) for i, word in enumerate("the legs are ay and bee the long side is see".split())]
    beats = ['"the legs" → legs glow', '"`a` and `b`" → labels', '"the long side" → c pulses', '"missing" → x']
    assert phrase_times(marks, beats) == [0.0, 1.2, 2.4, None]


def test_polly_sends_ssml_falls_back_to_text_and_returns_word_marks(monkeypatch):
    import io
    import json
    import boto3
    from app import narration

    calls = []

    class Invalid(Exception):
        pass

    class FakePolly:
        exceptions = type("E", (), {"InvalidSsmlException": Invalid})

        def synthesize_speech(self, **request):
            calls.append(request)
            if request.get("TextType") == "ssml" and request["OutputFormat"] == "mp3":
                raise Invalid()  # e.g. an engine that rejects a tag → retry as plain text
            body = (
                b"mp3"
                if request["OutputFormat"] == "mp3"
                else "\n".join(
                    json.dumps({"type": "word", "time": time_ms, "value": word})
                    for time_ms, word in [(0, "Look"), (450, "here")]
                ).encode()
            )
            return {"AudioStream": io.BytesIO(body)}

    monkeypatch.setattr(boto3, "client", lambda name: FakePolly())
    audio, marks = narration.create_polly_synthesizer("Matthew", "neural")("Look here. [pause] Done.")
    assert audio == b"mp3" and marks == [("Look", 0.0), ("here", 0.45)]
    assert calls[0]["Text"].startswith("<speak>") and calls[1]["Text"] == "Look here. … Done."
    assert calls[2]["SpeechMarkTypes"] == ["word"] and calls[2]["TextType"] == "ssml"


def test_marked_ssml_for_google_timepoints():
    from app.narration import to_ssml_marked

    ssml, words = to_ssml_marked("Hi & bye. [pause] See")
    assert words == ["Hi", "&", "bye.", "See"]
    assert ssml == (
        '<speak><mark name="0"/>Hi <mark name="1"/>&amp; <mark name="2"/>bye. <break time="600ms"/> '
        '<mark name="3"/>See</speak>'
    )


def test_google_maps_timepoints_to_words_and_falls_back_to_text(monkeypatch):
    from types import SimpleNamespace as Namespace
    from google.api_core.exceptions import InvalidArgument
    from google.cloud import texttospeech_v1beta1 as gtts
    from app import narration

    requests = []

    class FakeClient:
        def synthesize_speech(self, request):
            requests.append(request)
            if "ssml" in request["input"] and request["voice"]["name"].startswith("en-US-Chirp3"):
                raise InvalidArgument("SSML not supported")
            timepoints = (
                [Namespace(mark_name="0", time_seconds=0.0), Namespace(mark_name="2", time_seconds=0.7)]
                if "ssml" in request["input"]
                else []
            )
            return Namespace(audio_content=b"mp3", timepoints=timepoints)

    monkeypatch.setattr(gtts, "TextToSpeechClient", FakeClient)
    audio, marks = narration.create_google_synthesizer("en-US-Neural2-D")("Look at see")
    assert (audio, marks) == (b"mp3", [("Look", 0.0), ("see", 0.7)])
    assert requests[0]["voice"] == {"language_code": "en-US", "name": "en-US-Neural2-D"}
    assert narration.create_google_synthesizer("en-US-Chirp3-HD-Aoede")("Hi [pause] there") == (b"mp3", None)
    assert requests[-1]["input"] == {"text": "Hi … there"}
    assert narration.create_speech_synthesizer(
        {"tts": "google", "voice": "en-US-Neural2-D", "engine": "neural"}
    ).__qualname__.startswith("create_google_synthesizer")
