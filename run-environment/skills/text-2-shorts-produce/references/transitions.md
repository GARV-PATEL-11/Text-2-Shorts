# Transitions — two levels

## Clip → clip (inside a scene): continuity, kept simple
- The next clip starts exactly where the previous one ended: entry contract = previous exit (same objects,
  positions, colours). Never re-draw, fade out and fade back in an object that continues.
- Between clips use only simple moves: keep, move or scale to make room, Transform/ReplacementTransform into the
  next form, FadeOut (0.4–0.6 s) what the narration has left behind. No wipes, flourishes or camera tricks.
- The narration just continues; no "now let's move on".

## Scene → scene: meaningful, explained
- Spoken — `bridge_in` of the next scene in `script.json`, 1–3 sentences: (1) what was just covered, in one plain
  sentence; (2) what comes next; (3) why it matters for the video's question or objectives.
  Example: "So gravity bends the path into an ellipse. Next: how fast the planet moves along it — that speed is
  what Kepler's second law describes."
- Visual — `transition_in` of the next scene's plan: scenes render separately and start on an empty frame, so the
  first clip's first beats re-create the previous scene's key final image (same objects, colours, zones) or a
  compact recap of it while the bridge is spoken, then transform or clear it into the new topic. The previous
  scene's last clip fades its objects out.
- The first scene is the index scene and has no bridge: it opens with the hook and the route ahead; s02's bridge
  turns from that overview to the first topic. The last scene closes the loop with the
  objectives; nothing bridges out of it.
