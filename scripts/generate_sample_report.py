#!/usr/bin/env python3
"""
Generate sample validation reports for documentation.

Creates example JSON and Markdown reports from the bundled example
metadata files. Output is written to docs/ for README embedding.
"""

from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from isolint.engine import ValidationConfig, ValidationEngine
from isolint.fair import FAIRScorer
from isolint.suggest import suggest_improvements, format_suggestions_markdown


def main():
    examples = project_root / "examples"
    docs = project_root / "docs"
    docs.mkdir(exist_ok=True)

    # Validate the valid example
    engine = ValidationEngine(ValidationConfig())
    report = engine.validate_file(examples / "valid_metadata.xml")
    report.write_json(docs / "sample_report_valid.json")
    report.write_markdown(docs / "sample_report_valid.md")
    print(f"Valid XML: {report.errors} errors, {report.warnings} warnings")

    # Validate the incomplete example
    report_inc = engine.validate_file(examples / "incomplete_metadata.xml")
    report_inc.write_json(docs / "sample_report_incomplete.json")
    report_inc.write_markdown(docs / "sample_report_incomplete.md")
    print(f"Incomplete XML: {report_inc.errors} errors, {report_inc.warnings} warnings")

    # FAIR score
    scorer = FAIRScorer()
    score = scorer.score_xml(examples / "valid_metadata.xml")
    (docs / "sample_fair_score.md").write_text(score.to_markdown())
    print(f"FAIR Score: {score.overall:.0%} (Grade: {score.grade})")

    # Suggestions
    suggestions = suggest_improvements(examples / "valid_metadata.xml")
    (docs / "sample_suggestions.md").write_text(format_suggestions_markdown(suggestions))
    print(f"Suggestions: {len(suggestions)}")

    print("\nSample reports written to docs/")


if __name__ == "__main__":
    main()
