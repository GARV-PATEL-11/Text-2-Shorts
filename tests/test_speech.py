from app.narration import case_pairs, phrase_times, speakable, speakable_ssml, ssml_problems, ssml_words, to_plain
from schemas.requirements import Brief


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


def test_planned_ssml_is_checked_and_made_speakable():
    planned = '<speak>Look at `c` &amp; more. <break time="700ms"/> <emphasis>Now</emphasis> [pause] done.</speak>'
    assert ssml_problems(planned) == []
    assert ssml_words(planned) == ["Look", "at", "`c`", "&", "more.", "Now", "[pause]", "done."]
    assert speakable_ssml(planned) == (
        '<speak>Look at see &amp; more. <break time="700ms"/> '
        '<emphasis>Now</emphasis> <break time="600ms"/> done.</speak>'
    )
    assert any("well-formed" in problem for problem in ssml_problems("<speak>Look <break></speak>"))
    assert any("audio" in problem for problem in ssml_problems('<speak><audio src="x"/>Hi</speak>'))
    assert any("<speak>" in problem for problem in ssml_problems("<p>Hi</p>"))
    assert to_plain('<speak>Look at this. <break time="600ms"/> Now see &amp; more.</speak>') == (
        "Look at this. … Now see & more."
    )


def test_phrase_times_follow_word_marks_in_order():
    marks = [
        (word, i * 0.4)
        for i, word in enumerate(["the", "legs", "are", "ay", "and", "bee", "the", "long", "side", "is", "see"])
    ]
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
    ssml = '<speak>Look <emphasis>here</emphasis>. <break time="600ms"/> Done.</speak>'
    audio, marks = narration.create_polly_synthesizer("Matthew", "neural")(ssml)
    assert audio == b"mp3" and marks == [("Look", 0.0), ("here", 0.45)]
    assert calls[0]["Text"] == '<speak>Look here. <break time="600ms"/> Done.</speak>'  # neural: no <emphasis>
    assert calls[1]["Text"] == "Look here. … Done."  # the engine rejected the SSML → plain text
    assert calls[2]["SpeechMarkTypes"] == ["word"] and calls[2]["TextType"] == "ssml"


def test_marked_ssml_for_google_timepoints():
    from app.narration import mark_words

    ssml, words = mark_words('<speak>Hi &amp; bye. <break time="600ms"/> <prosody rate="90%">See</prosody></speak>')
    assert words == ["Hi", "&", "bye.", "See"]
    assert ssml == (
        '<speak><mark name="0"/>Hi <mark name="1"/>&amp; <mark name="2"/>bye. <break time="600ms"/> '
        '<prosody rate="90%"><mark name="3"/>See</prosody></speak>'
    )


def test_google_maps_timepoints_to_words_and_falls_back_to_text(monkeypatch):
    from types import SimpleNamespace as Namespace

    from app import narration
    from google.api_core.exceptions import InvalidArgument
    from google.cloud import texttospeech_v1beta1 as gtts

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
    audio, marks = narration.create_google_synthesizer("en-US-Neural2-D")("<speak>Look at see</speak>")
    assert (audio, marks) == (b"mp3", [("Look", 0.0), ("see", 0.7)])
    assert requests[0]["voice"] == {"language_code": "en-US", "name": "en-US-Neural2-D"}
    assert narration.create_google_synthesizer("en-US-Chirp3-HD-Aoede")(
        '<speak>Hi <break time="600ms"/> there</speak>'
    ) == (b"mp3", None)
    assert requests[-1]["input"] == {"text": "Hi … there"}
    assert narration.create_speech_synthesizer(
        Brief(requirement="topic", tts="google", voice="en-US-Neural2-D", engine="neural")
    ).__qualname__.startswith("create_google_synthesizer")
