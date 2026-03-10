"""
Compliance report model and rendering.

Produces JSON and Markdown output with exact XPath locations,
severity levels, fix suggestions, and summary statistics.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class Severity(Enum):
    """Finding severity levels."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class Finding:
    """A single validation finding."""

    severity: Severity
    message: str
    source: str = ""
    xpath: str = ""
    rule_id: str = ""
    suggestion: str = ""
    line: Optional[int] = None

    def to_dict(self) -> dict:
        d = {
            "severity": self.severity.value,
            "message": self.message,
            "source": self.source,
        }
        if self.xpath:
            d["xpath"] = self.xpath
        if self.rule_id:
            d["rule_id"] = self.rule_id
        if self.suggestion:
            d["suggestion"] = self.suggestion
        if self.line is not None:
            d["line"] = self.line
        return d


@dataclass
class ComplianceReport:
    """
    Aggregated compliance report for a validation run.

    Tracks all findings, computes pass/fail status, and renders
    output in JSON or Markdown format.
    """

    target: str = ""
    findings: list = field(default_factory=list)
    timestamp: str = ""
    passed: bool = True
    errors: int = 0
    warnings: int = 0
    infos: int = 0

    def add_finding(self, finding: Finding) -> None:
        """Add a finding to the report."""
        self.findings.append(finding)

    def finalize(self) -> None:
        """Compute summary statistics and pass/fail."""
        self.timestamp = (
            datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )
        self.errors = sum(1 for f in self.findings if f.severity == Severity.ERROR)
        self.warnings = sum(1 for f in self.findings if f.severity == Severity.WARNING)
        self.infos = sum(1 for f in self.findings if f.severity == Severity.INFO)
        self.passed = self.errors == 0

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "target": self.target,
            "timestamp": self.timestamp,
            "passed": self.passed,
            "summary": {
                "errors": self.errors,
                "warnings": self.warnings,
                "info": self.infos,
                "total_findings": len(self.findings),
            },
            "findings": [f.to_dict() for f in self.findings],
        }

    def to_json(self, indent: int = 2) -> str:
        """Render as JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def to_markdown(self) -> str:
        """Render as Markdown compliance report."""
        lines = [
            "# Compliance Report",
            "",
            f"**Target:** `{self.target}`  ",
            f"**Timestamp:** {self.timestamp}  ",
            f"**Status:** {'✓ PASSED' if self.passed else '✗ FAILED'}  ",
            "",
            "## Summary",
            "",
            "| Level    | Count |",
            "|----------|-------|",
            f"| Errors   | {self.errors} |",
            f"| Warnings | {self.warnings} |",
            f"| Info     | {self.infos} |",
            f"| **Total**| **{len(self.findings)}** |",
            "",
        ]

        if self.findings:
            lines.append("## Findings")
            lines.append("")

            for i, f in enumerate(self.findings, 1):
                icon = {"error": "🔴", "warning": "🟡", "info": "🔵"}[f.severity.value]
                lines.append(f"### {i}. {icon} [{f.severity.value.upper()}] {f.message}")
                lines.append("")
                if f.source:
                    lines.append(f"- **Source:** `{f.source}`")
                if f.xpath:
                    lines.append(f"- **XPath:** `{f.xpath}`")
                if f.rule_id:
                    lines.append(f"- **Rule:** `{f.rule_id}`")
                if f.line is not None:
                    lines.append(f"- **Line:** {f.line}")
                if f.suggestion:
                    lines.append(f"- **Fix:** {f.suggestion}")
                lines.append("")

        return "\n".join(lines)

    def write_json(self, path: Path) -> None:
        """Write JSON report to file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json())
        logger.info("Wrote JSON report: %s", path)

    def write_markdown(self, path: Path) -> None:
        """Write Markdown report to file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_markdown())
        logger.info("Wrote Markdown report: %s", path)
