"""
Command-line interface for isolint.

Commands:
  isolint check <path>        — validate metadata files
  isolint suggest <path>      — get improvement suggestions
  isolint diff <a> <b>        — compare two metadata files
  isolint fair <path>         — compute FAIR self-score
  isolint serve               — start the web UI
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

console = Console()


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )


@click.group()
@click.version_option(package_name="iso19115-validator")
def main():
    """isolint — ISO 19115-2, CF-1.8, and ACDD-1.3 metadata linter."""
    pass


@main.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--format", "output_format", type=click.Choice(["text", "json", "markdown"]),
              default="text", help="Output format.")
@click.option("--output", "-o", type=click.Path(), default=None,
              help="Write report to file.")
@click.option("--rules", "-r", type=click.Path(exists=True), default=None,
              help="YAML rules file for custom policies.")
@click.option("--strict", is_flag=True, help="Treat warnings as errors.")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output.")
def check(path, output_format, output, rules, strict, verbose):
    """Validate metadata files in PATH (file or directory)."""
    _setup_logging(verbose)

    from isolint.engine import ValidationConfig, ValidationEngine

    config = ValidationConfig(
        yaml_rules_path=Path(rules) if rules else None,
        strict=strict,
    )
    engine = ValidationEngine(config)
    target = Path(path)

    if target.is_dir():
        report = engine.validate_directory(target)
    else:
        report = engine.validate_file(target)

    if output_format == "json":
        text = report.to_json()
    elif output_format == "markdown":
        text = report.to_markdown()
    else:
        _print_report_rich(report)
        if output:
            Path(output).write_text(report.to_json())
            console.print(f"\n[dim]Report written to {output}[/dim]")
        sys.exit(0 if report.passed else 1)
        return

    if output:
        Path(output).write_text(text)
        console.print(f"Report written to {output}")
    else:
        click.echo(text)

    sys.exit(0 if report.passed else 1)


@main.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--format", "output_format", type=click.Choice(["text", "json", "markdown"]),
              default="text")
@click.option("--verbose", "-v", is_flag=True)
def suggest(path, output_format, verbose):
    """Get improvement suggestions for metadata at PATH."""
    _setup_logging(verbose)

    from isolint.suggest import format_suggestions_markdown, suggest_improvements

    target = Path(path)
    suggestions = suggest_improvements(target)

    if output_format == "json":
        click.echo(json.dumps([s.to_dict() for s in suggestions], indent=2))
    elif output_format == "markdown":
        click.echo(format_suggestions_markdown(suggestions))
    else:
        if not suggestions:
            console.print("[green]No improvements needed — metadata looks complete![/green]")
            return

        table = Table(title="Improvement Suggestions")
        table.add_column("#", style="dim")
        table.add_column("Priority", style="bold")
        table.add_column("Category")
        table.add_column("Title")
        table.add_column("Description", max_width=50)

        for i, s in enumerate(suggestions, 1):
            color = {"high": "red", "medium": "yellow", "low": "green"}[s.priority]
            table.add_row(str(i), f"[{color}]{s.priority}[/{color}]",
                          s.category, s.title, s.description)

        console.print(table)


@main.command()
@click.argument("file_a", type=click.Path(exists=True))
@click.argument("file_b", type=click.Path(exists=True))
@click.option("--format", "output_format", type=click.Choice(["text", "json", "markdown"]),
              default="text")
@click.option("--verbose", "-v", is_flag=True)
def diff(file_a, file_b, output_format, verbose):
    """Compare two metadata files and report differences."""
    _setup_logging(verbose)

    from isolint.diff import diff_netcdf, diff_xml

    path_a, path_b = Path(file_a), Path(file_b)

    if path_a.suffix == ".xml" and path_b.suffix == ".xml":
        result = diff_xml(path_a, path_b)
    elif path_a.suffix == ".nc" and path_b.suffix == ".nc":
        result = diff_netcdf(path_a, path_b)
    else:
        click.echo("Error: both files must be the same type (.xml or .nc)", err=True)
        sys.exit(1)

    if output_format == "json":
        click.echo(result.to_json())
    elif output_format == "markdown":
        click.echo(result.to_markdown())
    else:
        if result.identical:
            console.print("[green]Files are identical.[/green]")
        else:
            table = Table(title="Metadata Diff")
            table.add_column("Type", style="bold")
            table.add_column("Path/Attribute")
            table.add_column("Details")

            for item in result.added:
                table.add_row("[green]+[/green]", item, "Added in B")
            for item in result.removed:
                table.add_row("[red]-[/red]", item, "Removed from B")
            for ch in result.changed:
                table.add_row("[yellow]~[/yellow]", ch["path"],
                              f"{ch['value_a'][:30]} → {ch['value_b'][:30]}")

            console.print(table)
            console.print(f"\n[dim]{len(result.added)} added, "
                          f"{len(result.removed)} removed, "
                          f"{len(result.changed)} changed[/dim]")


@main.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--format", "output_format", type=click.Choice(["text", "json", "markdown"]),
              default="text")
@click.option("--verbose", "-v", is_flag=True)
def fair(path, output_format, verbose):
    """Compute FAIR self-assessment score for metadata at PATH."""
    _setup_logging(verbose)

    from isolint.fair import FAIRScorer

    scorer = FAIRScorer()
    target = Path(path)

    scores = []
    if target.is_dir():
        for xml in sorted(target.rglob("*.xml")):
            scores.append(scorer.score_xml(xml))
        for nc in sorted(target.rglob("*.nc")):
            scores.append(scorer.score_netcdf(nc))
    elif target.suffix == ".xml":
        scores.append(scorer.score_xml(target))
    elif target.suffix == ".nc":
        scores.append(scorer.score_netcdf(target))

    if not scores:
        click.echo("No metadata files found.", err=True)
        sys.exit(1)

    # Average
    score = scores[0]
    if len(scores) > 1:
        score.findable = sum(s.findable for s in scores) / len(scores)
        score.accessible = sum(s.accessible for s in scores) / len(scores)
        score.interoperable = sum(s.interoperable for s in scores) / len(scores)
        score.reusable = sum(s.reusable for s in scores) / len(scores)

    if output_format == "json":
        click.echo(json.dumps(score.to_dict(), indent=2))
    elif output_format == "markdown":
        click.echo(score.to_markdown())
    else:
        console.print(f"\n[bold]FAIR Score: {score.overall:.0%} (Grade: {score.grade})[/bold]\n")

        for label, val in [("Findable", score.findable), ("Accessible", score.accessible),
                           ("Interoperable", score.interoperable), ("Reusable", score.reusable)]:
            bar = "█" * int(val * 20) + "░" * (20 - int(val * 20))
            color = "green" if val >= 0.8 else "yellow" if val >= 0.6 else "red"
            console.print(f"  {label:14s} [{color}]{bar}[/{color}] {val:.0%}")

        console.print()
        for principle, items in score.details.items():
            for item in items:
                console.print(f"  {item}")


@main.command()
@click.option("--host", default="127.0.0.1", help="Bind host.")
@click.option("--port", default=8000, type=int, help="Bind port.")
@click.option("--verbose", "-v", is_flag=True)
def serve(host, port, verbose):
    """Start the web UI server."""
    _setup_logging(verbose)
    import uvicorn

    console.print(f"[bold]isolint web UI[/bold] → http://{host}:{port}")
    uvicorn.run("isolint.web:app", host=host, port=port, log_level="info")


def _print_report_rich(report) -> None:
    """Pretty-print a validation report using Rich."""
    status = "[green]PASSED[/green]" if report.passed else "[red]FAILED[/red]"
    console.print(f"\n[bold]Validation: {status}[/bold]")
    console.print(f"  Target: {report.target}")
    console.print(f"  Errors: {report.errors}  Warnings: {report.warnings}  "
                  f"Info: {report.infos}\n")

    if not report.findings:
        console.print("  [dim]No findings.[/dim]")
        return

    for f in report.findings:
        color = {"error": "red", "warning": "yellow", "info": "blue"}[f.severity.value]
        console.print(f"  [{color}][{f.severity.value.upper():7s}][/{color}] {f.message}")
        if f.source:
            console.print(f"           [dim]Source: {f.source}[/dim]")
        if f.xpath:
            console.print(f"           [dim]XPath:  {f.xpath}[/dim]")
        if f.suggestion:
            console.print(f"           [dim]Fix:    {f.suggestion}[/dim]")


if __name__ == "__main__":
    main()
