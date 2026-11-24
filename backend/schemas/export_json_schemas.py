"""Write a JSON Schema file for every contract in backend/schemas/ → backend/schemas/json/<Model>.schema.json.

uv run python backend/schemas/export_json_schemas.py
"""

import importlib
import inspect
import json
import sys
from pathlib import Path

from pydantic import BaseModel

SCHEMAS_DIRECTORY = Path(__file__).resolve().parent
OUTPUT_DIRECTORY = SCHEMAS_DIRECTORY / "json"
MODULES = ["requirements", "script", "plans", "reviews", "interaction", "run_state", "media", "session", "api"]


def contracts() -> dict[str, type[BaseModel]]:
    """Every model defined in the schema modules (the unused contracts are not exported)."""
    sys.path.insert(0, str(SCHEMAS_DIRECTORY.parent))
    found = {}
    for module_name in MODULES:
        module = importlib.import_module(f"schemas.{module_name}")
        for name, value in vars(module).items():
            if inspect.isclass(value) and issubclass(value, BaseModel) and value.__module__ == module.__name__:
                found[name] = value
    return found


if __name__ == "__main__":
    OUTPUT_DIRECTORY.mkdir(exist_ok=True)
    for old in OUTPUT_DIRECTORY.glob("*.schema.json"):
        old.unlink()
    models = contracts()
    for name, model in models.items():
        (OUTPUT_DIRECTORY / f"{name}.schema.json").write_text(json.dumps(model.model_json_schema(), indent=2) + "\n")
    print(f"wrote {len(models)} schemas to {OUTPUT_DIRECTORY}")
