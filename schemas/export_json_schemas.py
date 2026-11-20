"""Write JSON Schema files for every contract in models.py → schemas/json/*.schema.json."""
import json
from pathlib import Path

import models as m

OUT = Path(__file__).with_name("json")
CLASSES = [m.VideoProject, m.Brief, m.EnvironmentReport, m.VideoPlan, m.ScenePlan, m.ClipPlan, m.ContinuityState,
           m.NarrationSegment, m.AudioArtifact, m.DocumentationReference, m.VisualSpecification, m.ManimCodeArtifact,
           m.ValidationResult, m.CriticResult, m.Finding, m.HumanFeedback, m.CacheEntry, m.RenderArtifact,
           m.GenerationMetadata, m.ClipState, m.ArtifactRef]

if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for c in CLASSES:
        (OUT / f"{c.__name__}.schema.json").write_text(json.dumps(c.model_json_schema(), indent=2))
    print(f"wrote {len(CLASSES)} schemas to {OUT}")
