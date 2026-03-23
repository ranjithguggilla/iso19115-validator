"""
ACDD 1.3 (Attribute Convention for Data Discovery) checker.

Validates NetCDF global attributes for discoverability requirements.
ACDD defines three levels: Required (must have), Recommended (should have),
and Suggested (nice to have).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List

from isolint.report import Finding, Severity

logger = logging.getLogger(__name__)

# ACDD 1.3 required attributes
ACDD_REQUIRED = [
    "title",
    "summary",
    "keywords",
    "Conventions",
]

# ACDD 1.3 highly recommended
ACDD_RECOMMENDED = [
    "id",
    "naming_authority",
    "history",
    "source",
    "processing_level",
    "comment",
    "license",
    "creator_name",
    "creator_email",
    "institution",
    "date_created",
    "geospatial_lat_min",
    "geospatial_lat_max",
    "geospatial_lon_min",
    "geospatial_lon_max",
    "time_coverage_start",
    "time_coverage_end",
]

# ACDD 1.3 suggested
ACDD_SUGGESTED = [
    "contributor_name",
    "publisher_name",
    "publisher_url",
    "project",
    "platform",
    "instrument",
    "keywords_vocabulary",
    "standard_name_vocabulary",
    "date_modified",
    "creator_url",
    "creator_institution",
    "geospatial_vertical_min",
    "geospatial_vertical_max",
]


def check_acdd_attributes(nc_path: Path) -> List[Finding]:
    """
    Check a NetCDF file for ACDD 1.3 compliance.

    Args:
        nc_path: Path to NetCDF file.

    Returns:
        List of findings.
    """
    findings: List[Finding] = []

    try:
        import netCDF4
    except ImportError:
        findings.append(Finding(
            severity=Severity.WARNING,
            message="netCDF4 not available; skipping ACDD checks",
            source=str(nc_path),
            rule_id="ACDD-000",
        ))
        return findings

    try:
        ds = netCDF4.Dataset(str(nc_path), "r")
    except Exception as e:
        findings.append(Finding(
            severity=Severity.ERROR,
            message=f"Cannot open NetCDF: {e}",
            source=str(nc_path),
            rule_id="ACDD-001",
        ))
        return findings

    try:
        global_attrs = set(ds.ncattrs())

        # Check required
        for attr in ACDD_REQUIRED:
            if attr not in global_attrs:
                findings.append(Finding(
                    severity=Severity.ERROR,
                    message=f"Missing required ACDD attribute: {attr}",
                    source=str(nc_path),
                    rule_id="ACDD-010",
                    suggestion=f"Add global attribute '{attr}' for data discoverability.",
                ))
            else:
                val = ds.getncattr(attr)
                if isinstance(val, str) and not val.strip():
                    findings.append(Finding(
                        severity=Severity.WARNING,
                        message=f"ACDD required attribute '{attr}' is empty",
                        source=str(nc_path),
                        rule_id="ACDD-011",
                        suggestion=f"Provide a meaningful value for '{attr}'.",
                    ))

        # Check recommended
        missing_recommended = []
        for attr in ACDD_RECOMMENDED:
            if attr not in global_attrs:
                missing_recommended.append(attr)

        if missing_recommended:
            findings.append(Finding(
                severity=Severity.WARNING,
                message=(
                    f"Missing {len(missing_recommended)} ACDD recommended attributes: "
                    f"{', '.join(missing_recommended[:5])}"
                    + (f"... (+{len(missing_recommended) - 5} more)"
                       if len(missing_recommended) > 5 else "")
                ),
                source=str(nc_path),
                rule_id="ACDD-020",
                suggestion="Add recommended attributes for better data discoverability.",
            ))

        # Check suggested (only report count)
        missing_suggested = [a for a in ACDD_SUGGESTED if a not in global_attrs]
        if missing_suggested:
            findings.append(Finding(
                severity=Severity.INFO,
                message=f"Missing {len(missing_suggested)} ACDD suggested attributes",
                source=str(nc_path),
                rule_id="ACDD-030",
                suggestion="Consider adding suggested attributes for full ACDD compliance.",
            ))

        # Validate geospatial bounds consistency
        _check_geospatial_bounds(ds, global_attrs, findings, nc_path)

        # Validate time coverage
        _check_time_coverage(ds, global_attrs, findings, nc_path)

    finally:
        ds.close()

    return findings


def _check_geospatial_bounds(
    ds, global_attrs: set, findings: List[Finding], nc_path: Path
) -> None:
    """Validate geospatial attribute consistency."""
    lat_attrs = {"geospatial_lat_min", "geospatial_lat_max"}
    lon_attrs = {"geospatial_lon_min", "geospatial_lon_max"}

    if lat_attrs.issubset(global_attrs):
        lat_min = float(ds.getncattr("geospatial_lat_min"))
        lat_max = float(ds.getncattr("geospatial_lat_max"))
        if lat_min > lat_max:
            findings.append(Finding(
                severity=Severity.ERROR,
                message=f"geospatial_lat_min ({lat_min}) > geospatial_lat_max ({lat_max})",
                source=str(nc_path),
                rule_id="ACDD-040",
                suggestion="Swap min and max latitude values.",
            ))
        if not (-90 <= lat_min <= 90 and -90 <= lat_max <= 90):
            findings.append(Finding(
                severity=Severity.ERROR,
                message="Geospatial latitude out of valid range [-90, 90]",
                source=str(nc_path),
                rule_id="ACDD-041",
                suggestion="Ensure latitude values are between -90 and 90.",
            ))

    if lon_attrs.issubset(global_attrs):
        lon_min = float(ds.getncattr("geospatial_lon_min"))
        lon_max = float(ds.getncattr("geospatial_lon_max"))
        if not (-180 <= lon_min <= 180 and -180 <= lon_max <= 180):
            findings.append(Finding(
                severity=Severity.ERROR,
                message="Geospatial longitude out of valid range [-180, 180]",
                source=str(nc_path),
                rule_id="ACDD-042",
                suggestion="Ensure longitude values are between -180 and 180.",
            ))


def _check_time_coverage(
    ds, global_attrs: set, findings: List[Finding], nc_path: Path
) -> None:
    """Validate time coverage attributes."""
    if "time_coverage_start" in global_attrs and "time_coverage_end" in global_attrs:
        start = ds.getncattr("time_coverage_start")
        end = ds.getncattr("time_coverage_end")
        if isinstance(start, str) and isinstance(end, str):
            if start > end:
                findings.append(Finding(
                    severity=Severity.ERROR,
                    message=f"time_coverage_start ({start}) > time_coverage_end ({end})",
                    source=str(nc_path),
                    rule_id="ACDD-050",
                    suggestion="Ensure start time is before end time.",
                ))
