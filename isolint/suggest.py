"""
Auto-suggestion engine for metadata improvements.

Analyzes existing metadata and generates actionable suggestions
for improving completeness, accuracy, and compliance with
ISO 19115-2, CF-1.8, and ACDD-1.3 standards.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List

from lxml import etree

logger = logging.getLogger(__name__)

NAMESPACES = {
    "gmd": "http://www.isotc211.org/2005/gmd",
    "gco": "http://www.isotc211.org/2005/gco",
}


@dataclass
class Suggestion:
    """An actionable metadata improvement suggestion."""

    category: str  # e.g., "completeness", "accuracy", "discoverability"
    priority: str  # "high", "medium", "low"
    title: str
    description: str
    xpath: str = ""
    example: str = ""

    def to_dict(self) -> dict:
        d = {
            "category": self.category,
            "priority": self.priority,
            "title": self.title,
            "description": self.description,
        }
        if self.xpath:
            d["xpath"] = self.xpath
        if self.example:
            d["example"] = self.example
        return d


def suggest_improvements(target: Path) -> List[Suggestion]:
    """
    Analyze metadata files and generate improvement suggestions.

    Args:
        target: Path to file or directory.

    Returns:
        List of prioritized suggestions.
    """
    suggestions: List[Suggestion] = []

    if target.is_dir():
        xml_files = sorted(target.rglob("*.xml"))
        nc_files = sorted(target.rglob("*.nc"))
    elif target.suffix == ".xml":
        xml_files = [target]
        nc_files = []
    elif target.suffix == ".nc":
        xml_files = []
        nc_files = [target]
    else:
        return suggestions

    for xml_path in xml_files:
        suggestions.extend(_suggest_xml(xml_path))

    for nc_path in nc_files:
        suggestions.extend(_suggest_netcdf(nc_path))

    # Sort by priority
    priority_order = {"high": 0, "medium": 1, "low": 2}
    suggestions.sort(key=lambda s: priority_order.get(s.priority, 3))

    return suggestions


def _suggest_xml(xml_path: Path) -> List[Suggestion]:
    """Generate suggestions for an XML metadata file."""
    suggestions: List[Suggestion] = []

    try:
        tree = etree.parse(str(xml_path))
    except etree.XMLSyntaxError:
        suggestions.append(Suggestion(
            category="structural",
            priority="high",
            title="Fix XML syntax errors",
            description=f"{xml_path.name} has XML syntax errors that must be fixed first.",
        ))
        return suggestions

    root = tree.getroot()

    # Check for DOI
    identifiers = root.xpath("//gmd:identifier//gco:CharacterString", namespaces=NAMESPACES)
    has_doi = any(
        e.text and e.text.strip().startswith("10.") for e in identifiers if e.text
    )
    if not has_doi:
        suggestions.append(Suggestion(
            category="findability",
            priority="high",
            title="Add a DOI or persistent identifier",
            description="A DOI makes the dataset findable and citable. Register with DataCite or Zenodo.",
            xpath="//gmd:identifier",
            example='<gco:CharacterString>10.5281/zenodo.1234567</gco:CharacterString>',
        ))

    # Check temporal extent
    temporal = root.xpath("//gmd:EX_TemporalExtent", namespaces=NAMESPACES)
    if not temporal:
        suggestions.append(Suggestion(
            category="completeness",
            priority="high",
            title="Add temporal extent",
            description="Temporal coverage helps users find data for their time period of interest.",
            xpath="//gmd:identificationInfo//gmd:extent//gmd:temporalElement",
        ))

    # Check spatial extent
    spatial = root.xpath("//gmd:EX_GeographicBoundingBox", namespaces=NAMESPACES)
    if not spatial:
        suggestions.append(Suggestion(
            category="completeness",
            priority="high",
            title="Add geographic bounding box",
            description="Spatial extent enables geographic search and map-based discovery.",
            xpath="//gmd:identificationInfo//gmd:extent//gmd:geographicElement",
        ))

    # Check keywords with thesaurus
    keywords = root.xpath("//gmd:keyword/gco:CharacterString", namespaces=NAMESPACES)
    thesaurus = root.xpath("//gmd:thesaurusName", namespaces=NAMESPACES)
    if keywords and not thesaurus:
        suggestions.append(Suggestion(
            category="interoperability",
            priority="medium",
            title="Link keywords to a controlled vocabulary",
            description="Reference a thesaurus (e.g., GCMD Science Keywords) for machine-readable keywords.",
            xpath="//gmd:descriptiveKeywords/gmd:MD_Keywords/gmd:thesaurusName",
        ))

    # Check data quality / lineage
    lineage = root.xpath("//gmd:dataQualityInfo//gmd:lineage", namespaces=NAMESPACES)
    if not lineage:
        suggestions.append(Suggestion(
            category="reusability",
            priority="medium",
            title="Add data quality and lineage information",
            description="Lineage describes how the data was collected and processed.",
            xpath="//gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:lineage",
        ))

    # Check distribution info
    distribution = root.xpath("//gmd:distributionInfo", namespaces=NAMESPACES)
    if not distribution:
        suggestions.append(Suggestion(
            category="accessibility",
            priority="medium",
            title="Add distribution information",
            description="Specify how the data can be accessed (URL, format, protocol).",
            xpath="//gmd:distributionInfo",
        ))

    # Check abstract length
    abstract = root.xpath("//gmd:abstract/gco:CharacterString", namespaces=NAMESPACES)
    if abstract and abstract[0].text:
        if len(abstract[0].text.strip()) < 100:
            suggestions.append(Suggestion(
                category="discoverability",
                priority="low",
                title="Expand the abstract",
                description="A more detailed abstract (100+ characters) improves search relevance.",
                xpath="//gmd:abstract/gco:CharacterString",
            ))

    return suggestions


def _suggest_netcdf(nc_path: Path) -> List[Suggestion]:
    """Generate suggestions for a NetCDF file."""
    suggestions: List[Suggestion] = []

    try:
        import netCDF4
        ds = netCDF4.Dataset(str(nc_path), "r")
    except Exception:
        return suggestions

    try:
        attrs = set(ds.ncattrs())

        if "keywords" not in attrs:
            suggestions.append(Suggestion(
                category="findability",
                priority="high",
                title="Add keywords attribute",
                description="Keywords improve dataset discoverability in search engines.",
                example='ds.keywords = "oceanography, buoy, temperature"',
            ))

        if "license" not in attrs:
            suggestions.append(Suggestion(
                category="reusability",
                priority="high",
                title="Specify a license",
                description="A license clarifies how others may use the data.",
                example='ds.license = "CC-BY-4.0"',
            ))

        if "id" not in attrs:
            suggestions.append(Suggestion(
                category="findability",
                priority="medium",
                title="Add dataset identifier",
                description="A unique ID (DOI preferred) makes the dataset citable.",
                example='ds.id = "10.5281/zenodo.1234567"',
            ))

        # Check variables for standard_name
        vars_without_sn = []
        for var_name in ds.variables:
            var = ds.variables[var_name]
            if var_name not in ds.dimensions and "standard_name" not in var.ncattrs():
                if not var_name.endswith("_qc"):
                    vars_without_sn.append(var_name)

        if vars_without_sn:
            suggestions.append(Suggestion(
                category="interoperability",
                priority="medium",
                title="Add standard_name to data variables",
                description=(
                    f"{len(vars_without_sn)} variables lack standard_name: "
                    f"{', '.join(vars_without_sn[:3])}"
                    + ("..." if len(vars_without_sn) > 3 else "")
                ),
            ))

    finally:
        ds.close()

    return suggestions


def format_suggestions_markdown(suggestions: List[Suggestion]) -> str:
    """Render suggestions as Markdown."""
    if not suggestions:
        return "## Suggestions\n\nNo improvements needed — metadata looks complete!\n"

    lines = [
        "## Improvement Suggestions",
        "",
        f"Found **{len(suggestions)}** suggestions for metadata improvement.",
        "",
    ]

    for i, s in enumerate(suggestions, 1):
        icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}[s.priority]
        lines.append(f"### {i}. {icon} [{s.priority.upper()}] {s.title}")
        lines.append("")
        lines.append(f"**Category:** {s.category}")
        lines.append("")
        lines.append(s.description)
        if s.xpath:
            lines.append(f"\n**XPath:** `{s.xpath}`")
        if s.example:
            lines.append(f"\n```\n{s.example}\n```")
        lines.append("")

    return "\n".join(lines)
