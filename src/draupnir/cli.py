"""Draupnir CLI — generate JSON Schema from Verdandi YAML.

Default mode generates all schemas. --check, --list, --fragments
are mutually exclusive alternatives.
"""

import typer

from draupnir.logic.entry_point import run_pipeline
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
    """Generate JSON Schema from Verdandi YAML."""
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
    """Entry point for pyproject.toml."""
    app()
