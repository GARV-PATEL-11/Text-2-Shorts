"""Write JSON Schema files for every contract in models.py → schemas/json/*.schema.json."""

import json
from pathlib import Path

import models

OUTPUT_DIRECTORY = Path(__file__).with_name("json")
CLASSES = [
    models.VideoProject,
    models.Brief,
    models.Script,
    models.ScriptScene,
    models.ReviewReport,
    models.ReviewFinding,
    models.Critique,
    models.CritiqueRound,
    models.CritiqueIssue,
    models.EnvironmentReport,
    models.VideoPlan,
    models.ScenePlan,
    models.ClipPlan,
    models.ContinuityState,
    models.NarrationSegment,
    models.AudioArtifact,
    models.DocumentationReference,
    models.VisualSpecification,
    models.ManimCodeArtifact,
    models.ValidationResult,
    models.CriticResult,
    models.Finding,
    models.HumanFeedback,
    models.CacheEntry,
    models.RenderArtifact,
    models.GenerationMetadata,
    models.ClipState,
    models.ArtifactRef,
]

if __name__ == "__main__":
    OUTPUT_DIRECTORY.mkdir(exist_ok=True)
    for model_class in CLASSES:
        (OUTPUT_DIRECTORY / f"{model_class.__name__}.schema.json").write_text(
            json.dumps(model_class.model_json_schema(), indent=2)
        )
    print(f"wrote {len(CLASSES)} schemas to {OUTPUT_DIRECTORY}")
