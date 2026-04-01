"""Generate Pydantic input models from input validation schemas.

Reads level mappings from tools/codegen_input.toml, fetches schemas from
schemas/input/, and writes model modules to structure/gen/input/.

Input schemas have string refs where original models have model type refs.
Generated models have `str` fields for refs — these are the graph edges.

Run after export_input_schemas.py to keep models in sync.
"""

import subprocess
import sys
import tomllib
from pathlib import Path

from draupnir.logic.transform.codegen_clean.composed import strip_redundant_constraints
from draupnir.logic.transform.codegen_clean.primitive import strip_future_annotations

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCHEMAS_DIR = PROJECT_ROOT / "schemas" / "input"
STRUCTURES_DIR = PROJECT_ROOT / "src" / "draupnir" / "structure"
CONFIG_PATH = PROJECT_ROOT / "tools" / "codegen_input.toml"


def main() -> int:
    """Generate all Pydantic input model modules from input schemas."""
    config = tomllib.loads(CONFIG_PATH.read_text())
    all_schemas = config["levels"]

    success = 0
    failed = 0
    for schema_name, module_name in all_schemas.items():
        schema_path = SCHEMAS_DIR / f"{schema_name}.schema.json"
        if not schema_path.exists():
            sys.stdout.write(f"  SKIP: {schema_name} (schema not found)\n")
            continue

        output_path = STRUCTURES_DIR / f"{module_name}.py"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            [
                sys.executable, "-m", "datamodel_code_generator",
                "--input", str(schema_path),
                "--input-file-type", "jsonschema",
                "--output", str(output_path),
                "--output-model-type", "pydantic_v2.BaseModel",
                "--use-standard-collections",
                "--use-annotated",
                "--use-title-as-name",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            sys.stderr.write(f"  FAIL: {schema_name}\n")
            sys.stderr.write(result.stderr)
            failed += 1
            continue

        content = output_path.read_text()
        content = strip_future_annotations(content)
        content = strip_redundant_constraints(content)
        output_path.write_text(content)
        sys.stdout.write(f"  {schema_name} -> {module_name}.py\n")
        success += 1

    sys.stdout.write(f"\nGenerated: {success}/{len(all_schemas)}\n")
    if failed:
        sys.stderr.write(f"Failed: {failed}\n")
        return 1
    sys.stdout.write("Done.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
