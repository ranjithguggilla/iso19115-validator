"""Tests for the YAML rules DSL engine."""


from isolint.report import Severity
from isolint.yaml_rules import Rule, RuleSet, load_ruleset


class TestRuleLoading:
    def test_load_ruleset(self, sample_rules_yaml):
        ruleset = load_ruleset(sample_rules_yaml)
        assert ruleset.name == "test-rules"
        assert len(ruleset.rules) == 3

    def test_rule_from_dict(self):
        d = {
            "id": "T-001",
            "description": "Test rule",
            "severity": "error",
            "check": {"type": "xpath_exists", "xpath": "//gmd:title"},
            "suggestion": "Add title.",
        }
        rule = Rule.from_dict(d)
        assert rule.id == "T-001"
        assert rule.severity == Severity.ERROR
        assert rule.check_type == "xpath_exists"

    def test_rule_severity_default(self):
        d = {
            "id": "T-002",
            "description": "Default severity",
            "check": {"type": "xpath_exists"},
        }
        rule = Rule.from_dict(d)
        assert rule.severity == Severity.WARNING

    def test_disabled_rule(self):
        d = {
            "id": "T-003",
            "description": "Disabled",
            "severity": "error",
            "check": {"type": "xpath_exists", "xpath": "//nothing"},
            "enabled": False,
        }
        rule = Rule.from_dict(d)
        assert rule.enabled is False


class TestRuleEvaluation:
    def test_xpath_exists_passes(self, valid_xml, sample_rules_yaml):
        """Rule requiring title should pass on valid XML."""
        ruleset = load_ruleset(sample_rules_yaml)
        findings = ruleset.evaluate(valid_xml.parent)
        # TEST-001 checks for title, which exists
        title_findings = [f for f in findings if f.rule_id == "TEST-001"]
        assert len(title_findings) == 0

    def test_xpath_exists_fails(self, incomplete_xml, sample_rules_yaml):
        """Rule requiring title should fail on incomplete XML."""
        ruleset = load_ruleset(sample_rules_yaml)
        findings = ruleset.evaluate(incomplete_xml.parent)
        title_findings = [f for f in findings if f.rule_id == "TEST-001"]
        assert len(title_findings) >= 1

    def test_xpath_regex_passes(self, valid_xml, sample_rules_yaml):
        """File identifier starting with lowercase should pass."""
        ruleset = load_ruleset(sample_rules_yaml)
        findings = ruleset.evaluate(valid_xml.parent)
        regex_findings = [f for f in findings if f.rule_id == "TEST-002"]
        assert len(regex_findings) == 0

    def test_file_exists_fails(self, valid_xml, sample_rules_yaml):
        """Missing README should produce finding."""
        ruleset = load_ruleset(sample_rules_yaml)
        findings = ruleset.evaluate(valid_xml.parent)
        file_findings = [f for f in findings if f.rule_id == "TEST-003"]
        assert len(file_findings) >= 1

    def test_file_exists_passes(self, valid_xml, sample_rules_yaml):
        """When README exists, no finding."""
        (valid_xml.parent / "README.txt").write_text("readme")
        ruleset = load_ruleset(sample_rules_yaml)
        findings = ruleset.evaluate(valid_xml.parent)
        file_findings = [f for f in findings if f.rule_id == "TEST-003"]
        assert len(file_findings) == 0

    def test_disabled_rules_skipped(self, valid_xml):
        """Disabled rules should not produce findings."""
        ruleset = RuleSet(rules=[
            Rule(
                id="SKIP-001",
                description="Should be skipped",
                severity=Severity.ERROR,
                check_type="xpath_exists",
                check_params={"xpath": "//nonexistent"},
                enabled=False,
            )
        ])
        findings = ruleset.evaluate(valid_xml.parent)
        assert len(findings) == 0
