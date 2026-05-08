# Changelog

## [1.0.0] — 2026-05-15

### Added
- ISO 19115-2 XSD structural validation with required/recommended element checks
- Schematron policy rules: date format, geographic bounds, topic categories,
  URL validation, responsible party, empty element, abstract length
- CF Conventions 1.8 attribute checker for NetCDF files
- ACDD 1.3 compliance checking with three-level attribute classification
- YAML rules DSL for custom institutional policies without code changes
- SHA-256 checksum verification (manifest and per-file sidecar)
- FAIR self-scoring with Findable/Accessible/Interoperable/Reusable breakdown
- Metadata diff engine for XML and NetCDF comparison
- Auto-suggestion engine for metadata improvement
- CLI (`isolint`) with check, suggest, diff, fair, serve commands
- FastAPI web UI with validation, suggestion, and FAIR scoring endpoints
- JSON and Markdown compliance report rendering
- Rich terminal output with colored findings
- Built-in oceanographic and institutional rule sets
- Comprehensive test suite (60+ tests)
- CI/CD with GitHub Actions (lint + test matrix + build)
