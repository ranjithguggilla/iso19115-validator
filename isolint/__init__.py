"""
iso19115-validator — metadata linter for geospatial datasets.

Validates ISO 19115-2 XML, CF-1.8 NetCDF attributes, and ACDD-1.3
conventions using structural (XSD), policy (Schematron), and
custom YAML rule definitions.
"""

__version__ = "1.0.0"
__author__ = "Ranjith Guggilla"

from isolint.engine import ValidationEngine
from isolint.fair import FAIRScorer
from isolint.report import ComplianceReport, Finding

__all__ = ["ValidationEngine", "ComplianceReport", "Finding", "FAIRScorer"]
