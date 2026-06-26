"""Draupnir CLI — generate JSON Schema from Verdandi YAML.

Thin typer wrapper that parses CLI args into a PipelineArgs dataclass
and delegates to run_pipeline (orchestrate layer). All business logic
lives in the orchestrate layer — this module only handles CLI concerns
(argument parsing, exit code translation).

Default mode generates all schemas and fragments. --check, --list, and
--fragments are mutually exclusive alternatives for CI and tooling use.
"""

import typer

from draupnir.logic.orchestrate.compile.orchestrate import run_pipeline
from draupnir.structure.config.pipeline import PipelineArgs

app = typer.Typer(help="Generate JSON Schema from Verdandi YAML.")


@app.command()
def run(
    check: bool = typer.Option(False, help="Check for drift without writing"),
    list_schemas: bool = typer.Option(False, "--list", help="List available schemas"),
    fragments: bool = typer.Option(False, help="Generate include-fragment schemas"),
    project: str | None = typer.Option(None, help="Verdandi project name"),
    verdandi_dir: str | None = typer.Option(None, help="Override Verdandi source directory"),
    output_dir: str | None = typer.Option(None, help="Override output directory"),
    workspace: str | None = typer.Option(None, help="Override workspace root"),
) -> None:
    """Generate JSON Schema from Verdandi YAML.

    Translates typer CLI args to a PipelineArgs dataclass and delegates
    to the orchestrate layer. Non-zero return codes become typer.Exit
    to propagate the failure to the shell.
    """
    args = PipelineArgs(
        check=check,
        list_schemas=list_schemas,
        fragments=fragments,
        project=project,
        verdandi_dir=verdandi_dir,
        output_dir=output_dir,
        workspace=workspace,
    )
    code = run_pipeline(args)
    if code != 0:
        raise typer.Exit(code)


def main() -> None:
    """Entry point for pyproject.toml — draupnir."""
    app()


def generate_models_main() -> None:
    """Entry point for pyproject.toml — draupnir-generate-models."""
    from draupnir.logic.orchestrate.codegen_models.orchestrate import run_codegen

    raise SystemExit(run_codegen())


def export_schemas_main() -> None:
    """Entry point for pyproject.toml — draupnir-export-schemas."""
    from draupnir.logic.orchestrate.codegen_schemas.orchestrate import run_export

    raise SystemExit(run_export())
