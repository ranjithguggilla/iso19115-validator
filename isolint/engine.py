"""
Core validation engine.

Orchestrates XSD structural validation, Schematron policy checks,
YAML-defined custom rules, and CF/ACDD attribute inspection.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from isolint.acdd_checker import check_acdd_attributes
from isolint.cf_checker import check_cf_attributes
from isolint.checksum_validator import validate_checksums
from isolint.report import ComplianceReport, Finding, Severity
from isolint.schematron import validate_schematron
from isolint.xsd_validator import validate_xsd
from isolint.yaml_rules import RuleSet, load_ruleset

logger = logging.getLogger(__name__)


@dataclass
class ValidationConfig:
    """Configuration for a validation run."""

    xsd_enabled: bool = True
    schematron_enabled: bool = True
    cf_enabled: bool = True
    acdd_enabled: bool = True
    checksum_enabled: bool = True
    yaml_rules_path: Optional[Path] = None
    strict: bool = False  # treat warnings as errors


class ValidationEngine:
    """
    Main entry point for metadata validation.

    Combines structural (XSD), policy (Schematron), convention (CF/ACDD),
    and custom (YAML) rule checking into a single coherent report.
    """

    def __init__(self, config: Optional[ValidationConfig] = None):
        self.config = config or ValidationConfig()
        self._ruleset: Optional[RuleSet] = None

        if self.config.yaml_rules_path:
            self._ruleset = load_ruleset(self.config.yaml_rules_path)

    def validate_directory(self, target: Path) -> ComplianceReport:
        """
        Validate all metadata files in a directory tree.

        Scans for:
          - *.xml → ISO 19115-2 XSD + Schematron
          - *.nc  → CF-1.8 + ACDD-1.3 attribute checks
          - MANIFEST.sha256 / *.sha256 → checksum verification
        """
        report = ComplianceReport(target=str(target))

        xml_files = sorted(target.rglob("*.xml"))
        nc_files = sorted(target.rglob("*.nc"))
        checksum_files = sorted(target.rglob("*.sha256"))

        for xml_path in xml_files:
            self._validate_xml(xml_path, report)

        for nc_path in nc_files:
            self._validate_netcdf(nc_path, report)

        if self.config.checksum_enabled and checksum_files:
            self._validate_checksums(checksum_files, target, report)

        if self._ruleset:
            self._apply_yaml_rules(target, report)

        report.finalize()
        return report

    def validate_file(self, filepath: Path) -> ComplianceReport:
        """Validate a single file."""
        report = ComplianceReport(target=str(filepath))

        if filepath.suffix == ".xml":
            self._validate_xml(filepath, report)
        elif filepath.suffix == ".nc":
            self._validate_netcdf(filepath, report)
        elif filepath.suffix == ".sha256":
            self._validate_checksums([filepath], filepath.parent, report)
        else:
            report.add_finding(Finding(
                severity=Severity.WARNING,
                message=f"Unsupported file type: {filepath.suffix}",
                source=str(filepath),
            ))

        if self._ruleset:
            self._apply_yaml_rules(filepath.parent, report)

        report.finalize()
        return report

    def _validate_xml(self, xml_path: Path, report: ComplianceReport) -> None:
        """Run XSD + Schematron checks on an XML file."""
        rel = str(xml_path)

        if self.config.xsd_enabled:
            xsd_findings = validate_xsd(xml_path)
            for f in xsd_findings:
                f.source = rel
                report.add_finding(f)

        if self.config.schematron_enabled:
            sch_findings = validate_schematron(xml_path)
            for f in sch_findings:
                f.source = rel
                report.add_finding(f)

    def _validate_netcdf(self, nc_path: Path, report: ComplianceReport) -> None:
        """Run CF + ACDD checks on a NetCDF file."""
        rel = str(nc_path)

        if self.config.cf_enabled:
            cf_findings = check_cf_attributes(nc_path)
            for f in cf_findings:
                f.source = rel
                report.add_finding(f)

        if self.config.acdd_enabled:
            acdd_findings = check_acdd_attributes(nc_path)
            for f in acdd_findings:
                f.source = rel
                report.add_finding(f)

    def _validate_checksums(
        self, checksum_files: list, root: Path, report: ComplianceReport
    ) -> None:
        """Verify SHA-256 checksums."""
        findings = validate_checksums(checksum_files, root)
        for f in findings:
            report.add_finding(f)

    def _apply_yaml_rules(self, target: Path, report: ComplianceReport) -> None:
        """Apply custom YAML-defined rules."""
        if not self._ruleset:
            return
        findings = self._ruleset.evaluate(target)
        for f in findings:
            report.add_finding(f)
