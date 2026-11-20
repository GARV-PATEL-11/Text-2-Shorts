#!/usr/bin/env python3
"""build_manim_api_index.py — deterministic, version-pinned Manim API index.

Introspects the *installed* Manim Community package (never the docs website) and
writes a JSON index of every public name exported by `from manim import *`:
classes (with MRO, __init__ signature, public methods + signatures), functions,
and constants. The index is the ground truth used by `validate_manim_code.py`
and by the doc-retrieval layer, so generated code is checked against the exact
runtime the renderer will use.

Usage:
    python tools/build_manim_api_index.py --out cache/manim_api/0.20.1/index.json

Status: IMPLEMENTED in this package (tested against manim==0.20.1).
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import sys
from pathlib import Path


def _signature(obj) -> str | None:
    try:
        return str(inspect.signature(obj))
    except (TypeError, ValueError):
        return None


def _doc_first_line(obj) -> str:
    doc = inspect.getdoc(obj) or ""
    return doc.strip().splitlines()[0][:200] if doc.strip() else ""


def build_index() -> dict:
    import manim

    exported = {}
    namespace: dict = {}
    exec("from manim import *", namespace)  # exactly what generated scene files do
    for name, obj in sorted(namespace.items()):
        if name.startswith("_") or name == "__builtins__":
            continue
        module = getattr(obj, "__module__", None) or ""
        if inspect.isclass(obj):
            methods = {}
            for method_name, member in inspect.getmembers(obj):
                if method_name.startswith("_"):
                    continue
                if callable(member) or isinstance(inspect.getattr_static(obj, method_name, None), property):
                    methods[method_name] = _signature(member) if callable(member) else "<property>"
            own_methods = sorted(
                key
                for key, value in vars(obj).items()
                if not key.startswith("_")
                and (callable(value) or isinstance(value, (property, staticmethod, classmethod)))
            )
            exported[name] = {
                "kind": "class",
                "own_methods": own_methods,
                "module": module,
                "mro": [base_class.__name__ for base_class in obj.__mro__[1:] if base_class.__name__ != "object"],
                "init": _signature(obj.__init__),
                "doc": _doc_first_line(obj),
                "methods": methods,
            }
        elif inspect.isfunction(obj) or inspect.isbuiltin(obj):
            exported[name] = {
                "kind": "function",
                "module": module,
                "signature": _signature(obj),
                "doc": _doc_first_line(obj),
            }
        elif inspect.ismodule(obj):
            # e.g. `np` — `from manim import *` re-exports numpy as np; generated code relies on it
            exported[name] = {"kind": "module", "module": obj.__name__}
        else:
            exported[name] = {"kind": "constant", "type": type(obj).__name__, "repr": repr(obj)[:120]}

    payload = json.dumps(exported, sort_keys=True)
    return {
        "manim_version": manim.__version__,
        "python_version": sys.version.split()[0],
        "content_hash": hashlib.sha256(payload.encode()).hexdigest()[:16],
        "counts": {
            key: sum(1 for value in exported.values() if value["kind"] == key)
            for key in ("class", "function", "constant", "module")
        },
        "names": exported,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    arguments = parser.parse_args()
    index = build_index()
    output_path = Path(arguments.out)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(index, indent=1, sort_keys=True))
    print(f"manim {index['manim_version']} · {index['counts']} · hash {index['content_hash']} → {output_path}")


if __name__ == "__main__":
    main()
