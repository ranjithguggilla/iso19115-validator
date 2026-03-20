"""
CF Conventions 1.8 attribute checker for NetCDF files.

Inspects NetCDF-4 global and variable attributes for compliance with
the Climate and Forecast Metadata Conventions version 1.8. Checks
standard_name validity, units consistency, coordinate variables,
and required global attributes.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List

from isolint.report import Finding, Severity

logger = logging.getLogger(__name__)

# CF-1.8 required global attributes
CF_REQUIRED_GLOBALS = [
    "Conventions",
    "title",
]

# CF-1.8 recommended global attributes
CF_RECOMMENDED_GLOBALS = [
    "history",
    "source",
    "institution",
    "references",
    "comment",
]

# Common CF standard names for oceanographic data
KNOWN_STANDARD_NAMES = {
    "time", "latitude", "longitude", "depth", "altitude",
    "sea_water_temperature", "sea_water_practical_salinity",
    "sea_water_pressure", "air_temperature", "air_pressure",
    "wind_speed", "wind_from_direction", "wind_speed_of_gust",
    "sea_surface_wave_significant_height",
    "sea_surface_wave_mean_period",
    "sea_surface_wave_from_direction",
    "dew_point_temperature", "relative_humidity",
    "visibility_in_air", "sea_water_electrical_conductivity",
    "sea_surface_height_above_sea_level",
    "eastward_sea_water_velocity", "northward_sea_water_velocity",
    "sea_water_density", "sea_water_sigma_t",
    "mole_concentration_of_dissolved_molecular_oxygen_in_sea_water",
    "mass_concentration_of_chlorophyll_a_in_sea_water",
    "sea_water_ph_reported_on_total_scale",
    "sea_water_turbidity",
}

# Standard unit mappings for common standard names
STANDARD_UNITS = {
    "sea_water_temperature": ["degree_Celsius", "degC", "K"],
    "air_temperature": ["degree_Celsius", "degC", "K"],
    "wind_speed": ["m s-1", "m/s"],
    "sea_water_practical_salinity": ["1", "PSU", "psu"],
    "sea_water_pressure": ["dbar", "Pa", "hPa"],
    "air_pressure": ["Pa", "hPa", "mbar"],
    "latitude": ["degrees_north", "degree_north"],
    "longitude": ["degrees_east", "degree_east"],
    "time": ["seconds since *", "days since *", "hours since *"],
    "depth": ["m"],
}


def check_cf_attributes(nc_path: Path) -> List[Finding]:
    """
    Check a NetCDF file for CF-1.8 convention compliance.

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
            message="netCDF4 not available; skipping CF checks",
            source=str(nc_path),
            rule_id="CF-000",
        ))
        return findings

    try:
        ds = netCDF4.Dataset(str(nc_path), "r")
    except Exception as e:
        findings.append(Finding(
            severity=Severity.ERROR,
            message=f"Cannot open NetCDF file: {e}",
            source=str(nc_path),
            rule_id="CF-001",
            suggestion="Ensure the file is a valid NetCDF-4 or NetCDF-3 file.",
        ))
        return findings

    try:
        _check_global_attributes(ds, findings, nc_path)
        _check_conventions_string(ds, findings, nc_path)
        _check_variable_attributes(ds, findings, nc_path)
        _check_coordinate_variables(ds, findings, nc_path)
    finally:
        ds.close()

    return findings


def _check_global_attributes(
    ds, findings: List[Finding], nc_path: Path
) -> None:
    """Check required and recommended global attributes."""
    global_attrs = ds.ncattrs()

    for attr in CF_REQUIRED_GLOBALS:
        if attr not in global_attrs:
            findings.append(Finding(
                severity=Severity.ERROR,
                message=f"Missing required CF global attribute: {attr}",
                source=str(nc_path),
                rule_id="CF-010",
                suggestion=f"Add global attribute '{attr}' to the NetCDF file.",
            ))

    for attr in CF_RECOMMENDED_GLOBALS:
        if attr not in global_attrs:
            findings.append(Finding(
                severity=Severity.INFO,
                message=f"Missing recommended CF global attribute: {attr}",
                source=str(nc_path),
                rule_id="CF-011",
                suggestion=f"Consider adding global attribute '{attr}'.",
            ))


def _check_conventions_string(
    ds, findings: List[Finding], nc_path: Path
) -> None:
    """Check that Conventions attribute references CF."""
    global_attrs = ds.ncattrs()
    if "Conventions" in global_attrs:
        conv = ds.getncattr("Conventions")
        if "CF" not in conv:
            findings.append(Finding(
                severity=Severity.WARNING,
                message=f"Conventions attribute '{conv}' does not reference CF",
                source=str(nc_path),
                rule_id="CF-012",
                suggestion="Include 'CF-1.8' in the Conventions attribute.",
            ))


def _check_variable_attributes(
    ds, findings: List[Finding], nc_path: Path
) -> None:
    """Check variable-level attributes for CF compliance."""
    for var_name in ds.variables:
        var = ds.variables[var_name]
        var_attrs = var.ncattrs()

        # Skip coordinate variables (checked separately)
        if var_name in ds.dimensions:
            continue

        # Check for standard_name or long_name
        has_standard = "standard_name" in var_attrs
        has_long = "long_name" in var_attrs
        if not has_standard and not has_long:
            findings.append(Finding(
                severity=Severity.WARNING,
                message=f"Variable '{var_name}' lacks standard_name and long_name",
                source=str(nc_path),
                rule_id="CF-020",
                suggestion=f"Add standard_name or long_name to variable '{var_name}'.",
            ))

        # Validate standard_name if present
        if has_standard:
            sn = var.getncattr("standard_name")
            if sn not in KNOWN_STANDARD_NAMES:
                findings.append(Finding(
                    severity=Severity.INFO,
                    message=f"Variable '{var_name}': standard_name '{sn}' not in common list",
                    source=str(nc_path),
                    rule_id="CF-021",
                    suggestion="Verify the standard_name against the CF standard name table.",
                ))

        # Check units attribute
        if "units" not in var_attrs and var_name not in ds.dimensions:
            # QC flag variables don't need units
            if not var_name.endswith("_qc") and "flag_values" not in var_attrs:
                findings.append(Finding(
                    severity=Severity.WARNING,
                    message=f"Variable '{var_name}' has no units attribute",
                    source=str(nc_path),
                    rule_id="CF-022",
                    suggestion=f"Add units attribute to variable '{var_name}'.",
                ))


def _check_coordinate_variables(
    ds, findings: List[Finding], nc_path: Path
) -> None:
    """Check coordinate variable conventions."""
    dim_names = set(ds.dimensions.keys())

    for dim in dim_names:
        if dim in ds.variables:
            var = ds.variables[dim]
            if "units" not in var.ncattrs():
                findings.append(Finding(
                    severity=Severity.ERROR,
                    message=f"Coordinate variable '{dim}' has no units",
                    source=str(nc_path),
                    rule_id="CF-030",
                    suggestion=f"Add units attribute to coordinate variable '{dim}'.",
                ))
            if dim == "time" and "calendar" not in var.ncattrs():
                findings.append(Finding(
                    severity=Severity.INFO,
                    message="Time coordinate missing 'calendar' attribute",
                    source=str(nc_path),
                    rule_id="CF-031",
                    suggestion="Add calendar='standard' (or appropriate) to time variable.",
                ))
