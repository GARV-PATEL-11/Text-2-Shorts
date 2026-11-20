import json
import manim

def test_index_matches_installed_version(api_index):
    idx = json.loads(api_index.read_text())
    assert idx["manim_version"] == manim.__version__

def test_known_names(api_index):
    names = json.loads(api_index.read_text())["names"]
    # exist in 0.20.1 (the current plan critic wrongly bans the first two)
    for n in ["GrowFromCenter", "ShowPassingFlash", "MathTex", "TransformMatchingTex", "Axes", "ValueTracker"]:
        assert n in names, n
    # removed / ManimGL-only — must NOT exist
    for n in ["ShowCreation", "GraphScene", "TextMobject", "ThoughtBubble", "InteractiveScene"]:
        assert n not in names, n
    assert "plot" in names["Axes"]["methods"] and "get_graph" not in names["Axes"]["methods"]
    assert "plot_line_graph" in names["Axes"]["methods"] and "get_line_graph" not in names["Axes"]["methods"]
