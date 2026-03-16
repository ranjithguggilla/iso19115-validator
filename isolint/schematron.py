"""
Schematron policy validation for ISO 19115-2.

Implements assertion-based validation rules that go beyond structural
correctness to enforce institutional and community policies. Rules
check semantic constraints: date formats, controlled vocabularies,
geographic bounds, and cross-element consistency.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import List

from lxml import etree

from isolint.report import Finding, Severity

logger = logging.getLogger(__name__)

NAMESPACES = {
    "gmd": "http://www.isotc211.org/2005/gmd",
    "gco": "http://www.isotc211.org/2005/gco",
    "gml": "http://www.opengis.net/gml/3.2",
    "gmi": "http://www.isotc211.org/2005/gmi",
}

# ISO 8601 date pattern
ISO_DATE_PATTERN = re.compile(
    r"^\d{4}(-\d{2}(-\d{2}(T\d{2}:\d{2}(:\d{2})?(Z|[+-]\d{2}:\d{2})?)?)?)?$"
)

# Valid topic categories per ISO 19115
VALID_TOPIC_CATEGORIES = {
    "farming", "biota", "boundaries", "climatologyMeteorologyAtmosphere",
    "economy", "elevation", "environment", "geoscientificInformation",
    "health", "imageryBaseMapsEarthCover", "intelligenceMilitary",
    "inlandWaters", "location", "oceans", "planningCadastre", "society",
    "structure", "transportation", "utilitiesCommunication",
}


def validate_schematron(xml_path: Path) -> List[Finding]:
    """
    Apply Schematron-style policy rules to an ISO 19115-2 XML file.

    Rules checked:
    - SCH-001: dateStamp must be valid ISO 8601
    - SCH-002: Geographic bounding box must have valid coordinates
    - SCH-003: Topic category must be from controlled vocabulary
    - SCH-004: Online resource URLs must be well-formed
    - SCH-005: Responsible party must have organization or individual name
    - SCH-006: CharacterString elements should not be empty
    - SCH-007: Abstract length should be >= 50 characters

    Args:
        xml_path: Path to XML file.

    Returns:
        List of findings.
    """
    findings: List[Finding] = []

    try:
        tree = etree.parse(str(xml_path))
    except etree.XMLSyntaxError:
        # XSD validator already catches this
        return findings

    root = tree.getroot()

    # SCH-001: Date validation
    _check_dates(root, findings, xml_path)

    # SCH-002: Geographic bounds
    _check_geographic_bounds(root, findings, xml_path)

    # SCH-003: Topic categories
    _check_topic_categories(root, findings, xml_path)

    # SCH-004: Online resource URLs
    _check_online_resources(root, findings, xml_path)

    # SCH-005: Responsible party
    _check_responsible_party(root, findings, xml_path)

    # SCH-006: Empty CharacterStrings
    _check_empty_strings(root, findings, xml_path)

    # SCH-007: Abstract length
    _check_abstract_length(root, findings, xml_path)

    return findings


def _check_dates(root: etree._Element, findings: List[Finding], xml_path: Path) -> None:
    """SCH-001: Validate date formats."""
    date_xpaths = [
        "//gmd:dateStamp/gco:Date",
        "//gmd:dateStamp/gco:DateTime",
        "//gmd:date/gmd:CI_Date/gmd:date/gco:Date",
        "//gmd:date/gmd:CI_Date/gmd:date/gco:DateTime",
    ]
    for xpath in date_xpaths:
        try:
            elements = root.xpath(xpath, namespaces=NAMESPACES)
        except etree.XPathError:
            continue

        for elem in elements:
            if elem.text and not ISO_DATE_PATTERN.match(elem.text.strip()):
                findings.append(Finding(
                    severity=Severity.ERROR,
                    message=f"Invalid ISO 8601 date: '{elem.text.strip()}'",
                    source=str(xml_path),
                    xpath=xpath,
                    rule_id="SCH-001",
                    suggestion="Use ISO 8601 format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ",
                ))


def _check_geographic_bounds(
    root: etree._Element, findings: List[Finding], xml_path: Path
) -> None:
    """SCH-002: Validate geographic bounding box coordinates."""
    bbox_xpath = "//gmd:EX_GeographicBoundingBox"
    try:
        bboxes = root.xpath(bbox_xpath, namespaces=NAMESPACES)
    except etree.XPathError:
        return

    for bbox in bboxes:
        coords = {}
        for direction in ("west", "east", "south", "north"):
            elem_xpath = f"gmd:{direction}BoundLongitude/gco:Decimal"
            if direction in ("south", "north"):
                elem_xpath = f"gmd:{direction}BoundLatitude/gco:Decimal"
            try:
                elems = bbox.xpath(elem_xpath, namespaces=NAMESPACES)
                if elems and elems[0].text:
                    coords[direction] = float(elems[0].text)
            except (etree.XPathError, ValueError):
                pass

        if len(coords) == 4:
            if not (-180 <= coords["west"] <= 180):
                findings.append(Finding(
                    severity=Severity.ERROR,
                    message=f"West longitude out of range: {coords['west']}",
                    source=str(xml_path),
                    xpath=bbox_xpath,
                    rule_id="SCH-002",
                    suggestion="Longitude must be between -180 and 180.",
                ))
            if not (-90 <= coords["south"] <= 90):
                findings.append(Finding(
                    severity=Severity.ERROR,
                    message=f"South latitude out of range: {coords['south']}",
                    source=str(xml_path),
                    xpath=bbox_xpath,
                    rule_id="SCH-002",
                    suggestion="Latitude must be between -90 and 90.",
                ))
            if coords["west"] > coords["east"]:
                findings.append(Finding(
                    severity=Severity.WARNING,
                    message="West bound > east bound (antimeridian crossing?)",
                    source=str(xml_path),
                    xpath=bbox_xpath,
                    rule_id="SCH-002",
                    suggestion="Verify this is intentional antimeridian crossing.",
                ))
            if coords["south"] > coords["north"]:
                findings.append(Finding(
                    severity=Severity.ERROR,
                    message="South bound > north bound",
                    source=str(xml_path),
                    xpath=bbox_xpath,
                    rule_id="SCH-002",
                    suggestion="Swap south and north latitude values.",
                ))


def _check_topic_categories(
    root: etree._Element, findings: List[Finding], xml_path: Path
) -> None:
    """SCH-003: Validate topic categories."""
    xpath = "//gmd:topicCategory/gmd:MD_TopicCategoryCode"
    try:
        elements = root.xpath(xpath, namespaces=NAMESPACES)
    except etree.XPathError:
        return

    for elem in elements:
        if elem.text and elem.text.strip() not in VALID_TOPIC_CATEGORIES:
            findings.append(Finding(
                severity=Severity.ERROR,
                message=f"Invalid topic category: '{elem.text.strip()}'",
                source=str(xml_path),
                xpath=xpath,
                rule_id="SCH-003",
                suggestion=f"Use one of: {', '.join(sorted(VALID_TOPIC_CATEGORIES)[:5])}...",
            ))


def _check_online_resources(
    root: etree._Element, findings: List[Finding], xml_path: Path
) -> None:
    """SCH-004: Validate online resource URLs."""
    xpath = "//gmd:CI_OnlineResource/gmd:linkage/gmd:URL"
    try:
        elements = root.xpath(xpath, namespaces=NAMESPACES)
    except etree.XPathError:
        return

    url_pattern = re.compile(r"^https?://[^\s]+$")
    for elem in elements:
        if elem.text and not url_pattern.match(elem.text.strip()):
            findings.append(Finding(
                severity=Severity.WARNING,
                message=f"Malformed URL: '{elem.text.strip()}'",
                source=str(xml_path),
                xpath=xpath,
                rule_id="SCH-004",
                suggestion="URLs should begin with http:// or https://",
            ))


def _check_responsible_party(
    root: etree._Element, findings: List[Finding], xml_path: Path
) -> None:
    """SCH-005: Responsible party must have a name."""
    xpath = "//gmd:CI_ResponsibleParty"
    try:
        parties = root.xpath(xpath, namespaces=NAMESPACES)
    except etree.XPathError:
        return

    for party in parties:
        org = party.xpath(
            "gmd:organisationName/gco:CharacterString", namespaces=NAMESPACES
        )
        ind = party.xpath(
            "gmd:individualName/gco:CharacterString", namespaces=NAMESPACES
        )
        has_org = any(e.text and e.text.strip() for e in org)
        has_ind = any(e.text and e.text.strip() for e in ind)

        if not has_org and not has_ind:
            findings.append(Finding(
                severity=Severity.WARNING,
                message="Responsible party has no organisation or individual name",
                source=str(xml_path),
                xpath=xpath,
                rule_id="SCH-005",
                suggestion="Add organisationName or individualName to CI_ResponsibleParty.",
            ))


def _check_empty_strings(
    root: etree._Element, findings: List[Finding], xml_path: Path
) -> None:
    """SCH-006: Flag empty CharacterString elements."""
    xpath = "//gco:CharacterString"
    try:
        elements = root.xpath(xpath, namespaces=NAMESPACES)
    except etree.XPathError:
        return

    empty_count = 0
    for elem in elements:
        if elem.text is None or elem.text.strip() == "":
            empty_count += 1

    if empty_count > 0:
        findings.append(Finding(
            severity=Severity.WARNING,
            message=f"{empty_count} empty gco:CharacterString element(s) found",
            source=str(xml_path),
            xpath=xpath,
            rule_id="SCH-006",
            suggestion="Remove empty elements or provide meaningful values.",
        ))


def _check_abstract_length(
    root: etree._Element, findings: List[Finding], xml_path: Path
) -> None:
    """SCH-007: Abstract should be sufficiently descriptive."""
    xpath = "//gmd:abstract/gco:CharacterString"
    try:
        elements = root.xpath(xpath, namespaces=NAMESPACES)
    except etree.XPathError:
        return

    for elem in elements:
        if elem.text and len(elem.text.strip()) < 50:
            findings.append(Finding(
                severity=Severity.WARNING,
                message=f"Abstract too short ({len(elem.text.strip())} chars, recommend >= 50)",
                source=str(xml_path),
                xpath=xpath,
                rule_id="SCH-007",
                suggestion="Provide a more descriptive abstract (at least 50 characters).",
            ))
