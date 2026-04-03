"""
FAIR self-scoring module.

Evaluates metadata completeness against the FAIR Data Principles
(Findable, Accessible, Interoperable, Reusable) and produces a
normalized score per principle plus an overall composite score.

Based on the FAIR metrics framework from:
  Wilkinson et al. (2016). doi:10.1038/sdata.2016.18
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

from lxml import etree

logger = logging.getLogger(__name__)

NAMESPACES = {
    "gmd": "http://www.isotc211.org/2005/gmd",
    "gco": "http://www.isotc211.org/2005/gco",
    "gml": "http://www.opengis.net/gml/3.2",
}


@dataclass
class FAIRScore:
    """FAIR self-assessment score."""

    findable: float = 0.0      # F score [0.0, 1.0]
    accessible: float = 0.0    # A score [0.0, 1.0]
    interoperable: float = 0.0  # I score [0.0, 1.0]
    reusable: float = 0.0      # R score [0.0, 1.0]
    details: Dict[str, List[str]] = field(default_factory=dict)

    @property
    def overall(self) -> float:
        """Weighted overall FAIR score."""
        return (self.findable + self.accessible + self.interoperable + self.reusable) / 4.0

    @property
    def grade(self) -> str:
        """Letter grade based on overall score."""
        score = self.overall
        if score >= 0.9:
            return "A"
        elif score >= 0.8:
            return "B"
        elif score >= 0.7:
            return "C"
        elif score >= 0.6:
            return "D"
        return "F"

    def to_dict(self) -> dict:
        return {
            "findable": round(self.findable, 3),
            "accessible": round(self.accessible, 3),
            "interoperable": round(self.interoperable, 3),
            "reusable": round(self.reusable, 3),
            "overall": round(self.overall, 3),
            "grade": self.grade,
            "details": self.details,
        }

    def to_markdown(self) -> str:
        """Render FAIR score as Markdown."""
        bar = lambda v: "█" * int(v * 10) + "░" * (10 - int(v * 10))  # noqa: E731
        lines = [
            "## FAIR Self-Assessment",
            "",
            f"**Overall Score: {self.overall:.1%} (Grade: {self.grade})**",
            "",
            "| Principle      | Score | Bar        |",
            "|----------------|-------|------------|",
            f"| **F**indable      | {self.findable:.0%}  | {bar(self.findable)} |",
            f"| **A**ccessible    | {self.accessible:.0%}  | {bar(self.accessible)} |",
            f"| **I**nteroperable | {self.interoperable:.0%}  | {bar(self.interoperable)} |",
            f"| **R**eusable      | {self.reusable:.0%}  | {bar(self.reusable)} |",
            "",
        ]

        for principle, items in self.details.items():
            if items:
                lines.append(f"### {principle} details")
                for item in items:
                    lines.append(f"- {item}")
                lines.append("")

        return "\n".join(lines)


class FAIRScorer:
    """
    Evaluates FAIR compliance for metadata files.

    Scoring criteria:
    - Findable: persistent ID, rich metadata, searchable
    - Accessible: standard protocol, open/auth metadata
    - Interoperable: formal language, FAIR vocab, qualified refs
    - Reusable: license, provenance, community standards
    """

    def score_xml(self, xml_path: Path) -> FAIRScore:
        """Score an ISO 19115-2 XML metadata file."""
        score = FAIRScore(details={
            "Findable": [], "Accessible": [], "Interoperable": [], "Reusable": [],
        })

        try:
            tree = etree.parse(str(xml_path))
        except etree.XMLSyntaxError:
            return score

        root = tree.getroot()

        # --- Findable ---
        f_checks = []

        # F1: Globally unique identifier
        file_id = root.xpath("//gmd:fileIdentifier/gco:CharacterString", namespaces=NAMESPACES)
        if file_id and file_id[0].text:
            f_checks.append(1.0)
            score.details["Findable"].append("✓ Has file identifier")
        else:
            f_checks.append(0.0)
            score.details["Findable"].append("✗ Missing file identifier")

        # F2: Rich metadata (title, abstract, keywords)
        title = root.xpath("//gmd:title/gco:CharacterString", namespaces=NAMESPACES)
        abstract = root.xpath("//gmd:abstract/gco:CharacterString", namespaces=NAMESPACES)
        keywords = root.xpath("//gmd:keyword/gco:CharacterString", namespaces=NAMESPACES)

        richness = sum([
            1 if (title and title[0].text) else 0,
            1 if (abstract and abstract[0].text and len(abstract[0].text) > 50) else 0,
            1 if keywords else 0,
        ]) / 3.0
        f_checks.append(richness)
        if richness == 1.0:
            score.details["Findable"].append("✓ Rich metadata (title, abstract, keywords)")
        else:
            score.details["Findable"].append(f"△ Metadata richness: {richness:.0%}")

        # F3: Identifier in metadata
        identifiers = root.xpath(
            "//gmd:identifier//gco:CharacterString", namespaces=NAMESPACES
        )
        if identifiers:
            f_checks.append(1.0)
            score.details["Findable"].append("✓ Contains dataset identifier")
        else:
            f_checks.append(0.0)
            score.details["Findable"].append("✗ No dataset identifier found")

        score.findable = sum(f_checks) / len(f_checks) if f_checks else 0.0

        # --- Accessible ---
        a_checks = []

        # A1: Standard retrieval protocol
        online_res = root.xpath("//gmd:CI_OnlineResource/gmd:linkage/gmd:URL", namespaces=NAMESPACES)
        if online_res:
            a_checks.append(1.0)
            score.details["Accessible"].append("✓ Has online resource URL")
        else:
            a_checks.append(0.0)
            score.details["Accessible"].append("✗ No online resource URL")

        # A2: Metadata accessible even if data isn't
        contact = root.xpath("//gmd:contact", namespaces=NAMESPACES)
        if contact:
            a_checks.append(1.0)
            score.details["Accessible"].append("✓ Contact information present")
        else:
            a_checks.append(0.5)
            score.details["Accessible"].append("△ No contact information")

        score.accessible = sum(a_checks) / len(a_checks) if a_checks else 0.0

        # --- Interoperable ---
        i_checks = []

        # I1: Formal, accessible language (XML with namespaces)
        if root.nsmap:
            i_checks.append(1.0)
            score.details["Interoperable"].append("✓ Uses formal namespace declarations")
        else:
            i_checks.append(0.0)
            score.details["Interoperable"].append("✗ No namespaces declared")

        # I2: Uses FAIR vocabularies
        vocab_refs = root.xpath(
            "//gmd:thesaurusName/gmd:CI_Citation/gmd:title/gco:CharacterString",
            namespaces=NAMESPACES,
        )
        if vocab_refs:
            i_checks.append(1.0)
            score.details["Interoperable"].append("✓ References controlled vocabulary")
        else:
            i_checks.append(0.0)
            score.details["Interoperable"].append("✗ No vocabulary references")

        # I3: Qualified references to other data
        related = root.xpath(
            "//gmd:aggregationInfo", namespaces=NAMESPACES
        )
        if related:
            i_checks.append(1.0)
            score.details["Interoperable"].append("✓ Has related dataset references")
        else:
            i_checks.append(0.0)
            score.details["Interoperable"].append("✗ No cross-references to other data")

        score.interoperable = sum(i_checks) / len(i_checks) if i_checks else 0.0

        # --- Reusable ---
        r_checks = []

        # R1.1: License
        constraints = root.xpath(
            "//gmd:resourceConstraints//gmd:otherConstraints/gco:CharacterString",
            namespaces=NAMESPACES,
        )
        use_limits = root.xpath(
            "//gmd:resourceConstraints//gmd:useLimitation/gco:CharacterString",
            namespaces=NAMESPACES,
        )
        if constraints or use_limits:
            r_checks.append(1.0)
            score.details["Reusable"].append("✓ License/constraints specified")
        else:
            r_checks.append(0.0)
            score.details["Reusable"].append("✗ No license or usage constraints")

        # R1.2: Provenance
        lineage = root.xpath(
            "//gmd:dataQualityInfo//gmd:lineage", namespaces=NAMESPACES
        )
        if lineage:
            r_checks.append(1.0)
            score.details["Reusable"].append("✓ Provenance/lineage information present")
        else:
            r_checks.append(0.0)
            score.details["Reusable"].append("✗ No provenance/lineage information")

        # R1.3: Community standards
        # Check if it actually uses ISO 19115 namespaces properly
        if any("isotc211" in str(v) for v in (root.nsmap or {}).values()):
            r_checks.append(1.0)
            score.details["Reusable"].append("✓ Uses ISO 19115 community standard")
        else:
            r_checks.append(0.5)
            score.details["Reusable"].append("△ Partial community standard compliance")

        score.reusable = sum(r_checks) / len(r_checks) if r_checks else 0.0

        return score

    def score_netcdf(self, nc_path: Path) -> FAIRScore:
        """Score a NetCDF file's FAIR compliance via its attributes."""
        score = FAIRScore(details={
            "Findable": [], "Accessible": [], "Interoperable": [], "Reusable": [],
        })

        try:
            import netCDF4
            ds = netCDF4.Dataset(str(nc_path), "r")
        except Exception:
            return score

        try:
            attrs = set(ds.ncattrs())

            # Findable
            f_checks = []
            if "id" in attrs or "naming_authority" in attrs:
                f_checks.append(1.0)
                score.details["Findable"].append("✓ Has dataset identifier")
            else:
                f_checks.append(0.0)
                score.details["Findable"].append("✗ No dataset identifier")

            if "title" in attrs and "summary" in attrs:
                f_checks.append(1.0)
                score.details["Findable"].append("✓ Has title and summary")
            else:
                f_checks.append(0.5)
                score.details["Findable"].append("△ Missing title or summary")

            if "keywords" in attrs:
                f_checks.append(1.0)
                score.details["Findable"].append("✓ Has keywords")
            else:
                f_checks.append(0.0)
                score.details["Findable"].append("✗ No keywords")

            score.findable = sum(f_checks) / len(f_checks) if f_checks else 0.0

            # Accessible
            a_checks = []
            if "creator_email" in attrs or "publisher_url" in attrs:
                a_checks.append(1.0)
                score.details["Accessible"].append("✓ Contact/access info present")
            else:
                a_checks.append(0.0)
                score.details["Accessible"].append("✗ No contact information")

            score.accessible = sum(a_checks) / len(a_checks) if a_checks else 0.0

            # Interoperable
            i_checks = []
            if "Conventions" in attrs:
                conv = ds.getncattr("Conventions")
                if "CF" in conv:
                    i_checks.append(1.0)
                    score.details["Interoperable"].append("✓ Uses CF conventions")
                else:
                    i_checks.append(0.5)
                    score.details["Interoperable"].append("△ Conventions without CF")
            else:
                i_checks.append(0.0)
                score.details["Interoperable"].append("✗ No conventions declared")

            if "standard_name_vocabulary" in attrs:
                i_checks.append(1.0)
                score.details["Interoperable"].append("✓ References standard name vocab")
            else:
                i_checks.append(0.0)
                score.details["Interoperable"].append("✗ No standard name vocabulary")

            score.interoperable = sum(i_checks) / len(i_checks) if i_checks else 0.0

            # Reusable
            r_checks = []
            if "license" in attrs:
                r_checks.append(1.0)
                score.details["Reusable"].append("✓ License specified")
            else:
                r_checks.append(0.0)
                score.details["Reusable"].append("✗ No license")

            if "history" in attrs or "source" in attrs:
                r_checks.append(1.0)
                score.details["Reusable"].append("✓ Provenance (history/source)")
            else:
                r_checks.append(0.0)
                score.details["Reusable"].append("✗ No provenance information")

            score.reusable = sum(r_checks) / len(r_checks) if r_checks else 0.0

        finally:
            ds.close()

        return score
