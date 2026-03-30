"""
YAML-based rules DSL for extensible institutional policies.

Allows organizations to define custom validation rules in YAML without
writing Python code. Rules can check for required elements, controlled
vocabularies, regex patterns, and cross-element dependencies.

Example rule file (rules.yaml):

    rules:
      - id: INST-001
        description: "Dataset must have DOI"
        severity: error
        check:
          type: xpath_exists
          xpath: "//gmd:identifier//gco:CharacterString[starts-with(., '10.')]"
        suggestion: "Add a DOI identifier to the metadata."

      - id: INST-002
        description: "Creator email must be institutional"
        severity: warning
        check:
          type: attr_regex
          attribute: creator_email
          pattern: ".*@(university|lab)\\.edu$"
        suggestion: "Use institutional email for creator_email."
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import yaml
from lxml import etree

from isolint.report import Finding, Severity

logger = logging.getLogger(__name__)

NAMESPACES = {
    "gmd": "http://www.isotc211.org/2005/gmd",
    "gco": "http://www.isotc211.org/2005/gco",
    "gml": "http://www.opengis.net/gml/3.2",
    "gmi": "http://www.isotc211.org/2005/gmi",
    "srv": "http://www.isotc211.org/2005/srv",
}


@dataclass
class Rule:
    """A single YAML-defined validation rule."""

    id: str
    description: str
    severity: Severity
    check_type: str
    check_params: dict = field(default_factory=dict)
    suggestion: str = ""
    enabled: bool = True

    @classmethod
    def from_dict(cls, d: dict) -> "Rule":
        """Parse a rule from a YAML dictionary."""
        severity_map = {
            "error": Severity.ERROR,
            "warning": Severity.WARNING,
            "info": Severity.INFO,
        }
        check = d.get("check", {})
        return cls(
            id=d["id"],
            description=d["description"],
            severity=severity_map.get(d.get("severity", "warning"), Severity.WARNING),
            check_type=check.get("type", ""),
            check_params=check,
            suggestion=d.get("suggestion", ""),
            enabled=d.get("enabled", True),
        )


@dataclass
class RuleSet:
    """Collection of YAML-defined rules."""

    rules: List[Rule] = field(default_factory=list)
    name: str = ""
    version: str = ""

    def evaluate(self, target: Path) -> List[Finding]:
        """
        Evaluate all rules against a target directory or file.

        Args:
            target: Path to directory or file.

        Returns:
            List of findings from rule evaluation.
        """
        findings: List[Finding] = []

        xml_files = []
        nc_files = []

        if target.is_dir():
            xml_files = sorted(target.rglob("*.xml"))
            nc_files = sorted(target.rglob("*.nc"))
        elif target.suffix == ".xml":
            xml_files = [target]
        elif target.suffix == ".nc":
            nc_files = [target]

        for rule in self.rules:
            if not rule.enabled:
                continue

            if rule.check_type == "xpath_exists":
                for xml_path in xml_files:
                    findings.extend(_eval_xpath_exists(rule, xml_path))
            elif rule.check_type == "xpath_not_empty":
                for xml_path in xml_files:
                    findings.extend(_eval_xpath_not_empty(rule, xml_path))
            elif rule.check_type == "xpath_regex":
                for xml_path in xml_files:
                    findings.extend(_eval_xpath_regex(rule, xml_path))
            elif rule.check_type == "attr_exists":
                for nc_path in nc_files:
                    findings.extend(_eval_attr_exists(rule, nc_path))
            elif rule.check_type == "attr_regex":
                for nc_path in nc_files:
                    findings.extend(_eval_attr_regex(rule, nc_path))
            elif rule.check_type == "file_exists":
                findings.extend(_eval_file_exists(rule, target))
            else:
                logger.warning("Unknown rule check type: %s (rule %s)", rule.check_type, rule.id)

        return findings


def load_ruleset(path: Path) -> RuleSet:
    """
    Load a YAML rules file.

    Args:
        path: Path to YAML file.

    Returns:
        Parsed RuleSet.
    """
    with open(path) as f:
        data = yaml.safe_load(f)

    ruleset = RuleSet(
        name=data.get("name", path.stem),
        version=data.get("version", "1.0"),
    )

    for rule_dict in data.get("rules", []):
        try:
            rule = Rule.from_dict(rule_dict)
            ruleset.rules.append(rule)
        except (KeyError, TypeError) as e:
            logger.warning("Skipping malformed rule: %s", e)

    logger.info("Loaded ruleset '%s' with %d rules", ruleset.name, len(ruleset.rules))
    return ruleset


def _eval_xpath_exists(rule: Rule, xml_path: Path) -> List[Finding]:
    """Check that an XPath expression returns results."""
    findings = []
    xpath = rule.check_params.get("xpath", "")
    if not xpath:
        return findings

    try:
        tree = etree.parse(str(xml_path))
        results = tree.xpath(xpath, namespaces=NAMESPACES)
        if not results:
            findings.append(Finding(
                severity=rule.severity,
                message=rule.description,
                source=str(xml_path),
                xpath=xpath,
                rule_id=rule.id,
                suggestion=rule.suggestion,
            ))
    except (etree.XMLSyntaxError, etree.XPathError) as e:
        logger.debug("XPath eval error for rule %s: %s", rule.id, e)

    return findings


def _eval_xpath_not_empty(rule: Rule, xml_path: Path) -> List[Finding]:
    """Check that XPath results have non-empty text content."""
    findings = []
    xpath = rule.check_params.get("xpath", "")
    if not xpath:
        return findings

    try:
        tree = etree.parse(str(xml_path))
        results = tree.xpath(xpath, namespaces=NAMESPACES)
        for elem in results:
            if elem.text is None or elem.text.strip() == "":
                findings.append(Finding(
                    severity=rule.severity,
                    message=f"{rule.description}: element is empty",
                    source=str(xml_path),
                    xpath=xpath,
                    rule_id=rule.id,
                    suggestion=rule.suggestion,
                ))
    except (etree.XMLSyntaxError, etree.XPathError) as e:
        logger.debug("XPath eval error for rule %s: %s", rule.id, e)

    return findings


def _eval_xpath_regex(rule: Rule, xml_path: Path) -> List[Finding]:
    """Check that XPath result text matches a regex pattern."""
    findings = []
    xpath = rule.check_params.get("xpath", "")
    pattern = rule.check_params.get("pattern", "")
    if not xpath or not pattern:
        return findings

    try:
        tree = etree.parse(str(xml_path))
        results = tree.xpath(xpath, namespaces=NAMESPACES)
        regex = re.compile(pattern)
        for elem in results:
            if elem.text and not regex.match(elem.text.strip()):
                findings.append(Finding(
                    severity=rule.severity,
                    message=f"{rule.description}: '{elem.text.strip()}' does not match pattern",
                    source=str(xml_path),
                    xpath=xpath,
                    rule_id=rule.id,
                    suggestion=rule.suggestion,
                ))
    except (etree.XMLSyntaxError, etree.XPathError, re.error) as e:
        logger.debug("Eval error for rule %s: %s", rule.id, e)

    return findings


def _eval_attr_exists(rule: Rule, nc_path: Path) -> List[Finding]:
    """Check that a NetCDF attribute exists."""
    findings = []
    attr_name = rule.check_params.get("attribute", "")
    if not attr_name:
        return findings

    try:
        import netCDF4
        ds = netCDF4.Dataset(str(nc_path), "r")
        try:
            if attr_name not in ds.ncattrs():
                findings.append(Finding(
                    severity=rule.severity,
                    message=rule.description,
                    source=str(nc_path),
                    rule_id=rule.id,
                    suggestion=rule.suggestion,
                ))
        finally:
            ds.close()
    except Exception:
        pass

    return findings


def _eval_attr_regex(rule: Rule, nc_path: Path) -> List[Finding]:
    """Check that a NetCDF attribute value matches a regex."""
    findings = []
    attr_name = rule.check_params.get("attribute", "")
    pattern = rule.check_params.get("pattern", "")
    if not attr_name or not pattern:
        return findings

    try:
        import netCDF4
        ds = netCDF4.Dataset(str(nc_path), "r")
        try:
            if attr_name in ds.ncattrs():
                val = str(ds.getncattr(attr_name))
                if not re.match(pattern, val):
                    findings.append(Finding(
                        severity=rule.severity,
                        message=f"{rule.description}: '{val}' does not match",
                        source=str(nc_path),
                        rule_id=rule.id,
                        suggestion=rule.suggestion,
                    ))
        finally:
            ds.close()
    except Exception:
        pass

    return findings


def _eval_file_exists(rule: Rule, target: Path) -> List[Finding]:
    """Check that a required file exists in the target directory."""
    findings = []
    filename = rule.check_params.get("filename", "")
    if not filename:
        return findings

    search_dir = target if target.is_dir() else target.parent
    if not (search_dir / filename).exists():
        findings.append(Finding(
            severity=rule.severity,
            message=rule.description,
            source=str(search_dir),
            rule_id=rule.id,
            suggestion=rule.suggestion,
        ))

    return findings
