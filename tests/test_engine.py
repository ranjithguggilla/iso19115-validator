"""Tests for the main validation engine."""


from isolint.engine import ValidationConfig, ValidationEngine
from isolint.report import Severity


class TestValidationEngine:
    def test_validate_valid_xml(self, valid_xml):
        engine = ValidationEngine()
        report = engine.validate_file(valid_xml)
        errors = [f for f in report.findings if f.severity == Severity.ERROR]
        assert len(errors) == 0

    def test_validate_incomplete_xml(self, incomplete_xml):
        engine = ValidationEngine()
        report = engine.validate_file(incomplete_xml)
        errors = [f for f in report.findings if f.severity == Severity.ERROR]
        assert len(errors) >= 2  # missing required elements

    def test_validate_directory(self, valid_xml, incomplete_xml):
        """Validate a directory with multiple XML files."""
        engine = ValidationEngine()
        report = engine.validate_directory(valid_xml.parent)
        # Should have processed at least one file
        assert len(report.findings) > 0

    def test_validate_with_yaml_rules(self, valid_xml, sample_rules_yaml):
        """Engine with YAML rules should apply custom rules."""
        config = ValidationConfig(yaml_rules_path=sample_rules_yaml)
        engine = ValidationEngine(config)
        report = engine.validate_file(valid_xml)
        # Should include YAML rule findings (TEST-003 for README)
        yaml_findings = [f for f in report.findings if f.rule_id.startswith("TEST")]
        assert len(yaml_findings) >= 1

    def test_validate_checksums(self, valid_checksum_file):
        """Engine should verify checksums when .sha256 files exist."""
        config = ValidationConfig(checksum_enabled=True)
        engine = ValidationEngine(config)
        report = engine.validate_directory(valid_checksum_file.parent)
        checksum_findings = [f for f in report.findings if f.rule_id.startswith("CHK")]
        assert len(checksum_findings) >= 1

    def test_disable_xsd(self, incomplete_xml):
        """Disabling XSD should skip structural validation."""
        config = ValidationConfig(xsd_enabled=False, schematron_enabled=False)
        engine = ValidationEngine(config)
        report = engine.validate_file(incomplete_xml)
        xsd_findings = [f for f in report.findings if f.rule_id.startswith("XSD")]
        assert len(xsd_findings) == 0

    def test_disable_schematron(self, valid_xml):
        config = ValidationConfig(schematron_enabled=False)
        engine = ValidationEngine(config)
        report = engine.validate_file(valid_xml)
        sch_findings = [f for f in report.findings if f.rule_id.startswith("SCH")]
        assert len(sch_findings) == 0

    def test_unsupported_file_type(self, tmp_path):
        """Unsupported file types should get a warning."""
        txt = tmp_path / "readme.txt"
        txt.write_text("not metadata")
        engine = ValidationEngine()
        report = engine.validate_file(txt)
        warnings = [f for f in report.findings if f.severity == Severity.WARNING]
        assert len(warnings) >= 1

    def test_report_is_finalized(self, valid_xml):
        engine = ValidationEngine()
        report = engine.validate_file(valid_xml)
        assert report.timestamp  # should be set by finalize()
