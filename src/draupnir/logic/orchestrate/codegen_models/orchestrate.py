"""Generate Pydantic models from the schemas Draupnir reads data against.

One model per Verdandi level (from its input schema) and one per Nornir tool
schema Draupnir reads output through, each computed from its name. Runs
datamodel-code-generator on each.

Entry point: draupnir-generate-models → cli.py → run_codegen()
"""

import subprocess
import sys
from pathlib import Path

from draupnir.logic.impure.paths_locate.primitive import locate_draupnir_paths
from draupnir.logic.pure.model_locate.simple import model_targets
from draupnir.structure.config.model_codegen import ModelTarget


def generate_one_model(target: ModelTarget) -> bool:
    """Run datamodel-code-generator on one schema.

    Returns True on success, False on failure. A schema that is not there is a
    failure: the generator refuses to read it.
    """
    Path(target.module_file).parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            sys.executable, "-m", "datamodel_code_generator",
            "--input", target.schema_file,
            "--input-file-type", "jsonschema",
            "--output", target.module_file,
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
    """Generate every level's input model and every tool schema's model; 1 if any failed."""
    targets = model_targets(locate_draupnir_paths())
    failed = 0
    for target in targets:
        if generate_one_model(target):
            sys.stdout.write(f"  {target.name} -> {target.module_file}\n")
        else:
            sys.stderr.write(f"  FAIL: {target.name}\n")
            failed += 1
    sys.stdout.write(f"\nGenerated: {len(targets) - failed}/{len(targets)}\n")
    return 1 if failed else 0
