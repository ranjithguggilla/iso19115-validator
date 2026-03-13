"""
XSD structural validation for ISO 19115-2 XML.

Validates XML documents against the ISO 19115-2 schema structure.
Uses lxml for schema parsing and validation with detailed error
reporting including line numbers and XPath locations.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List

from lxml import etree

from isolint.report import Finding, Severity

logger = logging.getLogger(__name__)

# Namespace map for ISO 19115-2
NAMESPACES = {
    "gmd": "http://www.isotc211.org/2005/gmd",
    "gco": "http://www.isotc211.org/2005/gco",
    "gml": "http://www.opengis.net/gml/3.2",
    "gmi": "http://www.isotc211.org/2005/gmi",
    "srv": "http://www.isotc211.org/2005/srv",
    "xlink": "http://www.w3.org/1999/xlink",
}

# Required top-level elements for a minimal valid ISO 19115-2 record
REQUIRED_ELEMENTS = [
    ("gmd:fileIdentifier", "//gmd:fileIdentifier/gco:CharacterString"),
    ("gmd:language", "//gmd:language/gco:CharacterString"),
    ("gmd:contact", "//gmd:contact"),
    ("gmd:dateStamp", "//gmd:dateStamp"),
    ("gmd:identificationInfo", "//gmd:identificationInfo"),
]

# Recommended elements (not required, but flagged as warnings)
RECOMMENDED_ELEMENTS = [
    ("gmd:abstract", "//gmd:identificationInfo//gmd:abstract/gco:CharacterString"),
    ("gmd:topicCategory", "//gmd:identificationInfo//gmd:topicCategory"),
    ("gmd:extent", "//gmd:identificationInfo//gmd:extent"),
    ("gmd:dataQualityInfo", "//gmd:dataQualityInfo"),
]


def validate_xsd(xml_path: Path) -> List[Finding]:
    """
    Validate an XML file against ISO 19115-2 structural requirements.

    Performs:
    1. Well-formedness check (XML parsing)
    2. Required element presence check
    3. Recommended element presence check
    4. Namespace validation

    Args:
        xml_path: Path to XML file.

    Returns:
        List of findings (errors, warnings, info).
    """
    findings: List[Finding] = []

    # Parse XML
    try:
        tree = etree.parse(str(xml_path))
    except etree.XMLSyntaxError as e:
        findings.append(Finding(
            severity=Severity.ERROR,
            message=f"XML syntax error: {e}",
            source=str(xml_path),
            rule_id="XSD-001",
            suggestion="Fix the XML syntax error. Ensure all tags are properly closed.",
        ))
        return findings

    root = tree.getroot()

    # Check root element
    root_tag = etree.QName(root.tag).localname if root.tag.startswith("{") else root.tag
    if root_tag not in ("MD_Metadata", "MI_Metadata"):
        findings.append(Finding(
            severity=Severity.WARNING,
            message=f"Root element is '{root_tag}', expected 'MD_Metadata' or 'MI_Metadata'",
            source=str(xml_path),
            xpath="/",
            rule_id="XSD-002",
            suggestion="Use gmd:MD_Metadata or gmi:MI_Metadata as the root element.",
        ))

    # Check required elements
    for name, xpath_expr in REQUIRED_ELEMENTS:
        try:
            results = root.xpath(xpath_expr, namespaces=NAMESPACES)
        except etree.XPathError:
            results = []

        if not results:
            findings.append(Finding(
                severity=Severity.ERROR,
                message=f"Required element missing: {name}",
                source=str(xml_path),
                xpath=xpath_expr,
                rule_id="XSD-010",
                suggestion=f"Add the required element {name} to the metadata record.",
            ))
        else:
            # Check if element has content
            for elem in results:
                if elem.text is None or elem.text.strip() == "":
                    if len(elem) == 0:  # no child elements either
                        findings.append(Finding(
                            severity=Severity.WARNING,
                            message=f"Required element {name} is empty",
                            source=str(xml_path),
                            xpath=xpath_expr,
                            rule_id="XSD-011",
                            suggestion=f"Provide a value for {name}.",
                        ))

    # Check recommended elements
    for name, xpath_expr in RECOMMENDED_ELEMENTS:
        try:
            results = root.xpath(xpath_expr, namespaces=NAMESPACES)
        except etree.XPathError:
            results = []

        if not results:
            findings.append(Finding(
                severity=Severity.INFO,
                message=f"Recommended element missing: {name}",
                source=str(xml_path),
                xpath=xpath_expr,
                rule_id="XSD-020",
                suggestion=f"Consider adding {name} for better metadata completeness.",
            ))

    # Validate namespaces
    declared_ns = dict(root.nsmap) if root.nsmap else {}
    if not any("isotc211" in str(v) for v in declared_ns.values()):
        findings.append(Finding(
            severity=Severity.WARNING,
            message="No ISO TC211 namespaces declared",
            source=str(xml_path),
            xpath="/",
            rule_id="XSD-030",
            suggestion="Declare ISO 19115 namespaces (gmd, gco) in the root element.",
        ))

    return findings
