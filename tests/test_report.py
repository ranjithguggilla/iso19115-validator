"""Tests for the compliance report model."""

import json

from isolint.report import ComplianceReport, Finding, Severity


class TestFinding:
    def test_to_dict_minimal(self):
        f = Finding(severity=Severity.ERROR, message="Test error")
        d = f.to_dict()
        assert d["severity"] == "error"
        assert d["message"] == "Test error"
        assert "xpath" not in d

    def test_to_dict_full(self):
        f = Finding(
            severity=Severity.WARNING,
            message="Test warning",
            source="test.xml",
            xpath="//gmd:title",
            rule_id="TST-001",
            suggestion="Fix it.",
            line=42,
        )
        d = f.to_dict()
        assert d["xpath"] == "//gmd:title"
        assert d["rule_id"] == "TST-001"
        assert d["line"] == 42


class TestComplianceReport:
    def test_empty_report_passes(self):
        report = ComplianceReport(target="test")
        report.finalize()
        assert report.passed is True
        assert report.errors == 0

    def test_error_makes_report_fail(self):
        report = ComplianceReport(target="test")
        report.add_finding(Finding(severity=Severity.ERROR, message="Err"))
        report.finalize()
        assert report.passed is False
        assert report.errors == 1

    def test_warnings_dont_fail(self):
        report = ComplianceReport(target="test")
        report.add_finding(Finding(severity=Severity.WARNING, message="Warn"))
        report.finalize()
        assert report.passed is True
        assert report.warnings == 1

    def test_to_json_is_valid(self):
        report = ComplianceReport(target="test")
        report.add_finding(Finding(severity=Severity.INFO, message="Info"))
        report.finalize()
        data = json.loads(report.to_json())
        assert data["passed"] is True
        assert data["summary"]["info"] == 1

    def test_to_markdown_contains_status(self):
        report = ComplianceReport(target="test")
        report.finalize()
        md = report.to_markdown()
        assert "PASSED" in md

    def test_to_markdown_with_findings(self):
        report = ComplianceReport(target="test")
        report.add_finding(Finding(
            severity=Severity.ERROR,
            message="Missing element",
            xpath="//gmd:title",
        ))
        report.finalize()
        md = report.to_markdown()
        assert "FAILED" in md
        assert "Missing element" in md
        assert "//gmd:title" in md

    def test_write_json(self, tmp_path):
        report = ComplianceReport(target="test")
        report.finalize()
        path = tmp_path / "report.json"
        report.write_json(path)
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["passed"] is True

    def test_write_markdown(self, tmp_path):
        report = ComplianceReport(target="test")
        report.finalize()
        path = tmp_path / "report.md"
        report.write_markdown(path)
        assert path.exists()
        assert "PASSED" in path.read_text()

    def test_timestamp_format(self):
        report = ComplianceReport(target="test")
        report.finalize()
        assert report.timestamp.endswith("Z")
        assert "+" not in report.timestamp
