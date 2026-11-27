"""Voices: any English Amazon Polly voice and engine as the narrator (a custom value on top of the curated voices), the
voice list from Polly, and spoken previews from one template filled with the chosen agent, speed and engine.
Polly itself is replaced here; the real service was checked by hand (2026-11-27)."""

import pytest
from app.web import voices
from test_web import ORIGIN, signed_in, web  # noqa: F401  (fixture)

POLLY = [
    {"Id": "Danielle", "Name": "Danielle", "Gender": "Female", "LanguageCode": "en-US", "LanguageName": "US English",
     "SupportedEngines": ["generative", "long-form", "neural"]},
    {"Id": "Matthew", "Name": "Matthew", "Gender": "Male", "LanguageCode": "en-US", "LanguageName": "US English",
     "SupportedEngines": ["generative", "neural", "standard"]},
    {"Id": "Kajal", "Name": "Kajal", "Gender": "Female", "LanguageCode": "en-IN", "LanguageName": "Indian English",
     "SupportedEngines": ["generative", "neural"]},
    {"Id": "Hans", "Name": "Hans", "Gender": "Male", "LanguageCode": "de-DE", "LanguageName": "German",
     "SupportedEngines": ["standard"]},
]  # fmt: skip


def test_any_polly_voice_and_engine_can_narrate_as_a_custom_voice():
    import audio_settings
    import video_settings
    from app.workflow.templates import build_template

    template = build_template("obsidian", {}, {"voice": "Danielle:generative"}, {})
    assert audio_settings.voice(template, "polly") == {"voice": "Danielle", "engine": "generative"}
    assert video_settings.problems(template) == []
    assert video_settings.custom_value("voice", template["overrides"]["voice"], "dark") == "Danielle:generative"
    bad = build_template("obsidian", {}, {"voice": "Danielle:turbo"}, {})
    assert any("voice" in problem for problem in video_settings.problems(bad))


def test_a_voice_saved_before_engines_were_chosen_still_reads():
    import audio_settings
    from app.workflow.templates import build_template

    template = build_template("obsidian", {}, {}, {})
    template["overrides"] = {"voice": {"polly": {"voice_id": "Joanna"}, "google": {"neural2": "Joanna"}}}  # 0.35
    assert audio_settings.voice(template, "polly")["voice"] == "Joanna"


@pytest.fixture
def polly(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(voices, "describe_voices", lambda: POLLY)
    monkeypatch.setattr(voices, "PREVIEWS", tmp_path / "previews")

    def synthesize(voice, engine, ssml):
        calls.append((voice, engine, ssml))
        return b"ID3 fake mp3"

    monkeypatch.setattr(voices, "synthesize", synthesize)
    voices.voice_list.cache_clear()
    return calls


def test_the_voice_list_is_polly_english_voices_with_their_engines(web, polly):  # noqa: F811
    _, client = web
    assert client.get("/api/voices").status_code == 401
    signed_in(client)
    listed = client.get("/api/voices").json()
    assert [voice["id"] for voice in listed["voices"]] == ["Danielle", "Kajal", "Matthew"]  # English only, by name
    danielle = listed["voices"][0]
    assert danielle["engines"] == ["generative", "long-form", "neural"] and danielle["language"] == "US English"
    assert listed["provider"] == "Amazon Polly" and listed["template"].startswith("Hello! I'm {agent}")
    assert listed["curated"]["Joanna:neural"] == "us_female_warm"  # the template's own options, recognised


def test_a_preview_speaks_the_template_with_the_chosen_agent_and_speed_once(web, polly):  # noqa: F811
    _, client = web
    signed_in(client)
    asked = {"voice": "Danielle", "engine": "generative", "speed": "brisk"}  # no speaking style for now
    first = client.post("/api/voices/preview", json=asked, headers=ORIGIN)
    assert (
        first.status_code == 200 and first.headers["content-type"] == "audio/mpeg" and first.content == b"ID3 fake mp3"
    )
    ((voice, engine, ssml),) = polly
    assert (voice, engine) == ("Danielle", "generative")
    assert "Danielle" in ssml and "Brisk" in ssml and 'rate="108%"' in ssml and "tone" not in ssml
    again = client.post("/api/voices/preview", json=asked, headers=ORIGIN)
    assert again.content == first.content and len(polly) == 1  # cached: Polly is asked once per combination


def test_a_preview_refuses_an_engine_the_voice_does_not_have(web, polly):  # noqa: F811
    _, client = web
    signed_in(client)
    refused = client.post("/api/voices/preview", json={"voice": "Kajal", "engine": "long-form", "speed": "natural",
                                                       "tone": "documentary"}, headers=ORIGIN)  # fmt: skip
    assert refused.status_code == 400 and polly == []
    assert client.post("/api/voices/preview", json={"voice": "Hans", "engine": "standard", "speed": "natural",
                                                    "tone": "documentary"}, headers=ORIGIN).status_code == 400  # fmt: skip


def test_polly_unreachable_is_a_plain_answer(web, monkeypatch):  # noqa: F811
    _, client = web
    signed_in(client)

    def unreachable():
        raise voices.VoicesUnavailable("Amazon Polly did not answer. Check the AWS credentials in .env.")

    monkeypatch.setattr(voices, "describe_voices", unreachable)
    voices.voice_list.cache_clear()
    answer = client.get("/api/voices")
    assert answer.status_code == 503 and "AWS credentials" in answer.json()["error"]


def test_a_run_saves_a_custom_voice_and_shows_it_again(web):  # noqa: F811
    import audio_settings
    from app.workflow.templates import current_template
    from test_web import run_at_cp1

    runs, client = web
    signed_in(client)
    run = run_at_cp1(runs)
    look = {"template": "obsidian", "elements": {"speaking_speed": "brisk"}, "custom": {"voice": "Danielle:generative"}}
    saved = client.post(f"/api/runs/{run.name}/look", json=look, headers=ORIGIN)
    assert saved.status_code == 200, saved.text
    assert saved.json()["custom"]["voice"] == "Danielle:generative"  # the page shows the same voice after a reload
    assert audio_settings.voice(current_template(run), "polly") == {"voice": "Danielle", "engine": "generative"}
    bad = client.post(
        f"/api/runs/{run.name}/look", json={**look, "custom": {"voice": "danielle; rm -rf"}}, headers=ORIGIN
    )
    assert bad.status_code == 409  # never anything but a Polly voice name and engine


def test_credentials_without_polly_speech_get_a_plain_answer(web, monkeypatch, tmp_path):  # noqa: F811
    import botocore.exceptions
    from app import narration

    _, client = web
    signed_in(client)
    monkeypatch.setattr(voices, "describe_voices", lambda: POLLY)
    monkeypatch.setattr(voices, "PREVIEWS", tmp_path / "previews")
    voices.voice_list.cache_clear()

    def refuse(voice, engine):
        def call(ssml):
            raise botocore.exceptions.ClientError({"Error": {"Code": "AccessDeniedException"}}, "SynthesizeSpeech")

        return call

    monkeypatch.setattr(narration, "create_polly_synthesizer", refuse)
    answer = client.post("/api/voices/preview", json={"voice": "Matthew", "engine": "neural", "speed": "natural",
                                                      "tone": "documentary"}, headers=ORIGIN)  # fmt: skip
    assert answer.status_code == 503 and "polly:SynthesizeSpeech" in answer.json()["error"]
    assert (
        not list((tmp_path / "previews").glob("*")) if (tmp_path / "previews").exists() else True
    )  # nothing half-kept


def test_a_preview_is_delivered_like_someone_introducing_themselves():
    import re

    from app.narration import ssml_problems

    voice, speed = {"name": "Ruth"}, {"label": "brisk", "rate": 1.08}
    ssml = voices.preview_ssml(voice, "generative", speed)
    line = voices.TEMPLATE.format(agent="Ruth", speed="Brisk", provider=voices.PROVIDER, engine="Generative")
    spoken = " ".join(re.sub(r"<[^>]+>", "", ssml).split())
    assert ssml_problems(ssml) == [] and spoken == line  # the words the page shows, nothing else
    assert ssml.startswith('<speak><prosody rate="108%"><s>Hello!</s> <break time="300ms"/> <s>')
    assert '<emphasis level="moderate">Ruth</emphasis>' in ssml  # the name is stressed
    assert ', <break time="150ms"/>' in ssml  # a breath at the comma
