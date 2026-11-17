"""Generate Pydantic input models from input validation schemas.

Reads level mappings from tools/codegen_input.toml and runs
datamodel-code-generator on each schema.

Entry point: draupnir-generate-models → cli.py → run_codegen()
"""

import subprocess
import sys
from pathlib import Path

from draupnir.logic.impure.codegen_config.simple import load_codegen_config
from draupnir.logic.impure.paths_locate.primitive import locate_draupnir_paths
from draupnir.logic.pure.refusal_format.primitive import refusal_text
from draupnir.structure.config.draupnir_paths import DraupnirPaths
from draupnir.structure.model.tool_outcome import ToolRefusal


def generate_one_model(schema_path: Path, output_path: Path) -> bool:
    """Run datamodel-code-generator on one schema.

    Returns True on success, False on failure.
    """
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
            "--disable-future-imports",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        return False
    return True


def run_codegen() -> int:
    """Generate all Pydantic input model modules from input schemas.

    A refused config read generates nothing and returns 1.
    """
    paths = locate_draupnir_paths()
    config = load_codegen_config(paths)
    if isinstance(config, ToolRefusal):
        sys.stderr.write(f"CONFIG ERROR: {paths.codegen_config_file}: {refusal_text(config)}\n")
        return 1
    return generate_all_models(config.levels, paths)


def generate_all_models(all_schemas: dict[str, str], paths: DraupnirPaths) -> int:
    """Run the generator for each schema-name → module-name pair; 1 if any failed."""
    success = 0
    failed = 0
    for schema_name, module_name in all_schemas.items():
        schema_path = Path(paths.input_schema_dir) / f"{schema_name}.schema.json"
        if not schema_path.exists():
            sys.stdout.write(f"  SKIP: {schema_name} (schema not found)\n")
            continue
        output_path = Path(paths.structures_dir) / f"{module_name}.py"
        if generate_one_model(schema_path, output_path):
            sys.stdout.write(f"  {schema_name} -> {module_name}.py\n")
            success += 1
        else:
            sys.stderr.write(f"  FAIL: {schema_name}\n")
            failed += 1

    sys.stdout.write(f"\nGenerated: {success}/{len(all_schemas)}\n")
    if failed:
        sys.stderr.write(f"Failed: {failed}\n")
        return 1
    sys.stdout.write("Done.\n")
    return 0
