#!/usr/bin/env python3
"""invalidation.py — dependency-aware selective regeneration planner.

Builds the artifact dependency graph for a VideoPlan and answers one question:
"given that these artifacts changed, what is the minimum set that must be rebuilt, in order?"

Key design rule (the reason unrelated clips are never regenerated):
    a clip depends on its NEIGHBOUR'S CONTINUITY CONTRACT (exit-state hash from the plan),
    never on the neighbour's code or render. Re-animating clip s02c03 therefore does not
    touch s02c04 unless the s02c03 *exit contract* changed.

Node naming:  <kind>:<id>   e.g. plan:s02c03, audio:s02c03, spec:s02c03, code:s02c03,
              check:s02c03, draft:s02c03, critic:s02c03, final:s02c03, contract:s02c03,
              scene:s02, video:all, style:all, api:all, video_plan:all
Status: IMPLEMENTED in this package (tests/test_invalidation.py).
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field

LLM_NODES = {"plan", "spec", "code", "critic"}           # cost money when rebuilt
CHECKPOINT_NODES = {"plan", "critic", "scene", "video"}  # may require human approval again


@dataclass
class Graph:
    deps: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))   # node -> inputs
    users: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))  # node -> dependents

    def add(self, node: str, *inputs: str) -> None:
        self.deps.setdefault(node, set())
        for i in inputs:
            self.deps[node].add(i)
            self.users[i].add(node)
            self.deps.setdefault(i, set())

    def topo(self, nodes: set[str]) -> list[str]:
        indeg = {n: len(self.deps[n] & nodes) for n in nodes}
        q = deque(sorted(n for n, d in indeg.items() if d == 0))
        out = []
        while q:
            n = q.popleft(); out.append(n)
            for u in sorted(self.users[n] & nodes):
                indeg[u] -= 1
                if indeg[u] == 0:
                    q.append(u)
        return out


def build_graph(scenes: dict[str, list[str]]) -> Graph:
    """scenes: {'s01': ['s01c01','s01c02'], ...} in order."""
    g = Graph()
    g.add("video_plan:all", "brief:all")
    prev_clip = None
    for sid, clips in scenes.items():
        for cid in clips:
            g.add(f"plan:{cid}", "video_plan:all")
            g.add(f"contract:{cid}", f"plan:{cid}")                # exit contract is a field of the plan
            g.add(f"audio:{cid}", f"plan:{cid}")                   # narration text lives in the plan
            spec_inputs = [f"plan:{cid}", f"audio:{cid}", "style:all", "api:all"]
            if prev_clip and prev_clip.startswith(sid):            # continuity only within a scene
                spec_inputs.append(f"contract:{prev_clip}")
            g.add(f"spec:{cid}", *spec_inputs)
            g.add(f"code:{cid}", f"spec:{cid}", "api:all")
            g.add(f"check:{cid}", f"code:{cid}", f"audio:{cid}")   # static + layout + timing (deterministic)
            g.add(f"draft:{cid}", f"check:{cid}")
            g.add(f"critic:{cid}", f"draft:{cid}")
            g.add(f"final:{cid}", f"critic:{cid}")
            prev_clip = cid
        g.add(f"scene:{sid}", *[f"final:{c}" for c in clips], *[f"audio:{c}" for c in clips])
    g.add("video:all", *[f"scene:{s}" for s in scenes])
    return g


def rebuild_plan(g: Graph, changed: set[str], unchanged_outputs: set[str] = frozenset()) -> list[str]:
    """Nodes to rebuild, topologically ordered. `unchanged_outputs` lets the caller stop propagation
    when a rebuilt node produced a byte-identical artifact (hash equal) — e.g. a plan edit that did
    not alter the exit contract stops at contract:<id>."""
    dirty, q = set(), deque(changed)
    while q:
        n = q.popleft()
        if n in unchanged_outputs:
            continue
        for u in g.users[n]:
            if u not in dirty:
                dirty.add(u); q.append(u)
    return g.topo(dirty | (set(changed) - {n for n in changed if n.endswith(":all") and n.startswith(("brief", "style", "api"))}))


def summarize(order: list[str]) -> dict:
    kinds = defaultdict(int)
    for n in order:
        kinds[n.split(":")[0]] += 1
    return {"total": len(order), "llm_calls_min": sum(v for k, v in kinds.items() if k in LLM_NODES),
            "human_checkpoints": sorted({n for n in order if n.split(":")[0] in CHECKPOINT_NODES}), "by_kind": dict(kinds)}


if __name__ == "__main__":
    scenes = {"s01": ["s01c01", "s01c02"], "s02": ["s02c01", "s02c02", "s02c03", "s02c04"], "s03": ["s03c01"]}
    g = build_graph(scenes)
    print("Visual-only feedback on s02c03 (code regenerated):")
    o = rebuild_plan(g, {"spec:s02c03"}); print(" ", o, "\n ", summarize(o))
    print("Narration edit on s02c03, exit contract unchanged:")
    o = rebuild_plan(g, {"plan:s02c03"}, unchanged_outputs={"contract:s02c03"}); print(" ", o)
    print("Exit contract of s02c03 changed:")
    o = rebuild_plan(g, {"plan:s02c03"}); print(" ", [n for n in o if "s02c04" in n])
