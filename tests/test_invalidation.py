from invalidation import build_graph, rebuild_plan

SCENES = {"s01": ["s01c01", "s01c02"], "s02": ["s02c01", "s02c02", "s02c03", "s02c04"], "s03": ["s03c01"]}

def ids(order):
    return {n.split(":")[1] for n in order}

def test_visual_feedback_touches_only_that_clip_its_scene_and_video():
    order = rebuild_plan(build_graph(SCENES), {"spec:s02c03"})
    assert ids(order) == {"s02c03", "s02", "all"}
    assert order.index("code:s02c03") < order.index("final:s02c03") < order.index("scene:s02") < order.index("video:all")

def test_unchanged_exit_contract_stops_propagation_to_next_clip():
    order = rebuild_plan(build_graph(SCENES), {"plan:s02c03"}, unchanged_outputs={"contract:s02c03"})
    assert "spec:s02c04" not in order and "audio:s02c03" in order

def test_changed_exit_contract_propagates_to_next_clip_only():
    order = rebuild_plan(build_graph(SCENES), {"plan:s02c03"})
    assert "spec:s02c04" in order
    assert not any(c in ids(order) for c in ["s01c01", "s02c01", "s02c02", "s03c01"])

def test_contract_does_not_cross_scene_boundary():
    order = rebuild_plan(build_graph(SCENES), {"plan:s01c02"})
    assert "spec:s02c01" not in order

def test_manim_upgrade_invalidates_all_specs_and_code():
    order = rebuild_plan(build_graph(SCENES), {"api:all"})
    assert sum(n.startswith("code:") for n in order) == 7
    assert not any(n.startswith(("plan:", "audio:")) for n in order)  # plans + paid TTS survive
