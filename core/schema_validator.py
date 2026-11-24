"""
JSON Schema validator for project.yaml and other canonical state files.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema
from jsonschema import Draft7Validator


SCHEMA_DIR = Path(__file__).parent.parent / "schemas"


def load_schema(name: str) -> dict:
    """Load a JSON schema by name."""
    schema_path = SCHEMA_DIR / f"{name}.json"
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema not found: {schema_path}")
    return json.loads(schema_path.read_text(encoding="utf-8"))


# Load and compile validators
_PROJECT_SCHEMA = load_schema("project-v1")
_PROJECT_VALIDATOR = Draft7Validator(_PROJECT_SCHEMA)


def validate_project_spec(data: dict) -> list[str]:
    """Validate project.yaml data against schema.
    
    Returns list of error messages (empty if valid).
    """
    errors = []
    for error in _PROJECT_VALIDATOR.iter_errors(data):
        path = " -> ".join(str(p) for p in error.absolute_path) or "root"
        errors.append(f"{path}: {error.message}")
    return errors


def validate_project_spec_strict(data: dict) -> None:
    """Validate project.yaml, raise on first error."""
    _PROJECT_VALIDATOR.validate(data)


def validate_file(path: Path | str, schema_name: str) -> list[str]:
    """Validate a file against a schema."""
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    schema = load_schema(schema_name)
    validator = Draft7Validator(schema)
    
    errors = []
    for error in validator.iter_errors(data):
        path_str = " -> ".join(str(p) for p in error.absolute_path) or "root"
        errors.append(f"{path_str}: {error.message}")
    return errors


# CLI integration
def cmd_validate_schema(project_root: str, **kwargs) -> int:
    """CLI: validate project.yaml against JSON schema."""
    from core.spec import read_project_spec
    
    project_root = Path(project_root)
    spec_path = project_root / ".ai-coding-starter" / "project.yaml"
    
    if not spec_path.exists():
        print(f"project.yaml not found at {spec_path}")
        return 1
    
    # First, load raw JSON for schema validation
    try:
        raw_data = json.loads(spec_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Failed to parse JSON: {e}")
        return 1
    
    # Schema validation
    schema_errors = validate_project_spec(raw_data)
    
    # Domain model validation (catches CanonicalId format, ISO dates, etc.)
    domain_errors = []
    try:
        spec = read_project_spec(spec_path)
        # Also validate the serialized form matches
        data = spec.to_dict()
    except Exception as e:
        domain_errors.append(str(e))
    
    all_errors = schema_errors + domain_errors
    
    if all_errors:
        print(f"Validation failed ({len(all_errors)} errors):")
        for err in all_errors:
            print(f"  - {err}")
        return 1
    else:
        print("OK project.yaml is valid")
        return 0
    
    try:
        spec = read_project_spec(spec_path)
        data = spec.to_dict()
        errors = validate_project_spec(data)
        
        if errors:
            print(f"Validation failed ({len(errors)} errors):")
            for err in errors:
                print(f"  - {err}")
            return 1
        else:
            print("OK project.yaml is valid")
            return 0
    except Exception as e:
        print(f"Validation error: {e}")
        return 1