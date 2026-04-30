"""Tests for XSD structural validation."""

from isolint.report import Severity
from isolint.xsd_validator import validate_xsd


class TestXSDValidator:
    def test_valid_xml_has_no_errors(self, valid_xml):
        """Valid XML should produce no errors."""
        findings = validate_xsd(valid_xml)
        errors = [f for f in findings if f.severity == Severity.ERROR]
        assert len(errors) == 0

    def test_incomplete_xml_has_errors(self, incomplete_xml):
        """Missing required elements should produce errors."""
        findings = validate_xsd(incomplete_xml)
        errors = [f for f in findings if f.severity == Severity.ERROR]
        assert len(errors) >= 2  # missing contact, dateStamp, identificationInfo

    def test_malformed_xml_returns_syntax_error(self, malformed_xml):
        """Malformed XML should return XSD-001 error."""
        findings = validate_xsd(malformed_xml)
        assert len(findings) >= 1
        assert findings[0].rule_id == "XSD-001"
        assert findings[0].severity == Severity.ERROR

    def test_findings_have_xpath(self, incomplete_xml):
        """Findings for missing elements should include XPath."""
        findings = validate_xsd(incomplete_xml)
        xpath_findings = [f for f in findings if f.xpath]
        assert len(xpath_findings) > 0

    def test_findings_have_suggestions(self, incomplete_xml):
        """All findings should include fix suggestions."""
        findings = validate_xsd(incomplete_xml)
        for f in findings:
            assert f.suggestion, f"Finding '{f.message}' has no suggestion"

    def test_recommended_elements_are_info(self, valid_xml):
        """Missing recommended elements should be INFO level."""
        findings = validate_xsd(valid_xml)
        infos = [f for f in findings if f.severity == Severity.INFO]
        # valid_xml is missing some recommended elements
        assert all(f.rule_id == "XSD-020" for f in infos if "Recommended" in f.message)

    def test_namespace_check(self, tmp_path):
        """XML without ISO namespaces should get a warning."""
        xml = tmp_path / "no_ns.xml"
        xml.write_text('<?xml version="1.0"?>\n<root><child>text</child></root>')
        findings = validate_xsd(xml)
        ns_warnings = [f for f in findings if f.rule_id == "XSD-030"]
        assert len(ns_warnings) >= 1
