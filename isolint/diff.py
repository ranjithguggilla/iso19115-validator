"""
Metadata diff engine.

Compares two metadata files (XML or NetCDF) and reports structural
and semantic differences. Useful for tracking metadata evolution
across versions or comparing records from different sources.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

from lxml import etree

logger = logging.getLogger(__name__)

NAMESPACES = {
    "gmd": "http://www.isotc211.org/2005/gmd",
    "gco": "http://www.isotc211.org/2005/gco",
}


@dataclass
class DiffResult:
    """Result of comparing two metadata files."""

    file_a: str
    file_b: str
    added: List[str] = field(default_factory=list)
    removed: List[str] = field(default_factory=list)
    changed: List[Dict[str, str]] = field(default_factory=list)
    identical: bool = False

    def to_dict(self) -> dict:
        return {
            "file_a": self.file_a,
            "file_b": self.file_b,
            "identical": self.identical,
            "summary": {
                "added": len(self.added),
                "removed": len(self.removed),
                "changed": len(self.changed),
            },
            "added": self.added,
            "removed": self.removed,
            "changed": self.changed,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def to_markdown(self) -> str:
        lines = [
            "# Metadata Diff Report",
            "",
            f"**File A:** `{self.file_a}`  ",
            f"**File B:** `{self.file_b}`  ",
            f"**Status:** {'Identical' if self.identical else 'Differences found'}  ",
            "",
        ]

        if self.identical:
            lines.append("No differences detected.")
            return "\n".join(lines)

        lines.append(f"## Summary: {len(self.added)} added, "
                      f"{len(self.removed)} removed, {len(self.changed)} changed")
        lines.append("")

        if self.added:
            lines.append("## Added in B (not in A)")
            lines.append("")
            for item in self.added:
                lines.append(f"- `{item}`")
            lines.append("")

        if self.removed:
            lines.append("## Removed from B (was in A)")
            lines.append("")
            for item in self.removed:
                lines.append(f"- `{item}`")
            lines.append("")

        if self.changed:
            lines.append("## Changed")
            lines.append("")
            lines.append("| Element | Value in A | Value in B |")
            lines.append("|---------|-----------|-----------|")
            for ch in self.changed:
                lines.append(f"| `{ch['path']}` | {ch['value_a'][:40]} | {ch['value_b'][:40]} |")
            lines.append("")

        return "\n".join(lines)


def diff_xml(path_a: Path, path_b: Path) -> DiffResult:
    """
    Compare two ISO 19115-2 XML files.

    Extracts all text content from leaf elements and compares
    element paths and values.

    Args:
        path_a: First XML file.
        path_b: Second XML file.

    Returns:
        DiffResult with added, removed, and changed elements.
    """
    result = DiffResult(file_a=str(path_a), file_b=str(path_b))

    try:
        tree_a = etree.parse(str(path_a))
        tree_b = etree.parse(str(path_b))
    except etree.XMLSyntaxError as e:
        logger.error("XML parse error during diff: %s", e)
        return result

    elements_a = _extract_leaf_elements(tree_a)
    elements_b = _extract_leaf_elements(tree_b)

    paths_a = set(elements_a.keys())
    paths_b = set(elements_b.keys())

    result.added = sorted(paths_b - paths_a)
    result.removed = sorted(paths_a - paths_b)

    common = paths_a & paths_b
    for path in sorted(common):
        val_a = elements_a[path]
        val_b = elements_b[path]
        if val_a != val_b:
            result.changed.append({
                "path": path,
                "value_a": val_a,
                "value_b": val_b,
            })

    result.identical = not result.added and not result.removed and not result.changed
    return result


def diff_netcdf(path_a: Path, path_b: Path) -> DiffResult:
    """
    Compare two NetCDF files' global attributes.

    Args:
        path_a: First NetCDF file.
        path_b: Second NetCDF file.

    Returns:
        DiffResult for global attributes.
    """
    result = DiffResult(file_a=str(path_a), file_b=str(path_b))

    try:
        import netCDF4
    except ImportError:
        logger.warning("netCDF4 not available for diff")
        return result

    try:
        ds_a = netCDF4.Dataset(str(path_a), "r")
        ds_b = netCDF4.Dataset(str(path_b), "r")
    except Exception as e:
        logger.error("Cannot open NetCDF for diff: %s", e)
        return result

    try:
        attrs_a = {k: str(ds_a.getncattr(k)) for k in ds_a.ncattrs()}
        attrs_b = {k: str(ds_b.getncattr(k)) for k in ds_b.ncattrs()}

        keys_a = set(attrs_a.keys())
        keys_b = set(attrs_b.keys())

        result.added = sorted(keys_b - keys_a)
        result.removed = sorted(keys_a - keys_b)

        for key in sorted(keys_a & keys_b):
            if attrs_a[key] != attrs_b[key]:
                result.changed.append({
                    "path": key,
                    "value_a": attrs_a[key],
                    "value_b": attrs_b[key],
                })

        result.identical = not result.added and not result.removed and not result.changed
    finally:
        ds_a.close()
        ds_b.close()

    return result


def _extract_leaf_elements(tree: etree._ElementTree) -> Dict[str, str]:
    """Extract all leaf elements with their paths and text content."""
    elements: Dict[str, str] = {}
    counters: Dict[str, int] = {}

    for elem in tree.iter():
        if len(elem) == 0:  # leaf node
            path = _element_path(elem)
            if path in counters:
                counters[path] += 1
                path = f"{path}[{counters[path]}]"
            else:
                counters[path] = 1

            text = (elem.text or "").strip()
            elements[path] = text

    return elements


def _element_path(elem: etree._Element) -> str:
    """Build a simplified XPath-like path for an element."""
    parts = []
    current = elem
    while current is not None:
        tag = etree.QName(current.tag).localname if current.tag.startswith("{") else current.tag
        parts.append(tag)
        current = current.getparent()
    parts.reverse()
    return "/" + "/".join(parts)
