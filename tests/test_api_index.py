import json

import manim


def test_index_matches_installed_version(api_index):
    index = json.loads(api_index.read_text())
    assert index["manim_version"] == manim.__version__


def test_known_names(api_index):
    names = json.loads(api_index.read_text())["names"]
    # exist in 0.20.1 (the current plan critic wrongly bans the first two)
    for name in ["GrowFromCenter", "ShowPassingFlash", "MathTex", "TransformMatchingTex", "Axes", "ValueTracker"]:
        assert name in names, name
    # removed / ManimGL-only — must NOT exist
    for name in ["ShowCreation", "GraphScene", "TextMobject", "ThoughtBubble", "InteractiveScene"]:
        assert name not in names, name
    assert "plot" in names["Axes"]["methods"] and "get_graph" not in names["Axes"]["methods"]
    assert "plot_line_graph" in names["Axes"]["methods"] and "get_line_graph" not in names["Axes"]["methods"]


def test_doc_cards_resolve_class_dot_method(api_index):
    from conftest import run_tool

    exit_code, output = run_tool("doc_cards.py", "--index", api_index, "--names", "Axes.plot,Axes.get_graph")
    assert "### Axes.plot" in output  # a real method is not "missing"
    assert "NOT IN Manim" in output and "Axes.get_graph" in output.split("NOT IN Manim")[1]
    assert "Axes.plot" not in output.split("NOT IN Manim")[1]
