# Technical Methods — iso19115-validator

## 1. Validation Architecture

### 1.1 Multi-Layer Approach

The validator implements a layered validation strategy:

1. **Structural (XSD)** — Checks XML well-formedness and required element
   presence against the ISO 19115-2 schema specification.
2. **Policy (Schematron)** — Enforces semantic constraints: date formats,
   controlled vocabularies, geographic bounds, and cross-element consistency.
3. **Convention (CF/ACDD)** — Inspects NetCDF attributes for compliance with
   CF Conventions 1.8 and ACDD 1.3.
4. **Custom (YAML DSL)** — Applies user-defined rules without code changes.

### 1.2 Engine Design

`ValidationEngine` orchestrates all layers and collects `Finding` objects
into a `ComplianceReport`. Each finding carries:

- Severity (error / warning / info)
- Human-readable message
- XPath to the offending element (when applicable)
- Rule ID for traceability
- Fix suggestion

The engine supports both file-level and directory-level validation, and
automatically dispatches to the appropriate checker based on file extension.

## 2. XSD Structural Validation

### 2.1 Required Elements

Per ISO 19115-2, a minimal valid metadata record must contain:

| Element                | XPath                                            |
|------------------------|--------------------------------------------------|
| `fileIdentifier`       | `//gmd:fileIdentifier/gco:CharacterString`       |
| `language`             | `//gmd:language/gco:CharacterString`             |
| `contact`              | `//gmd:contact`                                  |
| `dateStamp`            | `//gmd:dateStamp`                                |
| `identificationInfo`   | `//gmd:identificationInfo`                       |

### 2.2 Recommended Elements

Checked at INFO severity:

- `gmd:abstract`
- `gmd:topicCategory`
- `gmd:extent`
- `gmd:dataQualityInfo`

## 3. Schematron Policy Rules

Seven policy rules implemented as assertion functions:

| Rule    | Description                              | Severity |
|---------|------------------------------------------|----------|
| SCH-001 | Date must be valid ISO 8601              | error    |
| SCH-002 | Geographic bounds must be valid          | error    |
| SCH-003 | Topic category from controlled vocab     | error    |
| SCH-004 | Online resource URLs well-formed         | warning  |
| SCH-005 | Responsible party needs a name           | warning  |
| SCH-006 | No empty CharacterString elements        | warning  |
| SCH-007 | Abstract >= 50 characters                | warning  |

## 4. CF-1.8 Convention Checking

### 4.1 Global Attributes

Required: `Conventions`, `title`
Recommended: `history`, `source`, `institution`, `references`, `comment`

### 4.2 Variable Attributes

Each data variable is checked for:
- `standard_name` or `long_name` (at least one required)
- `units` attribute (required for data variables, not QC flags)
- Standard name validity against a curated lookup table

### 4.3 Coordinate Variables

Coordinate variables (those sharing a name with a dimension) must have
`units`. The `time` coordinate additionally checks for `calendar`.

## 5. ACDD 1.3 Checking

Three levels per the ACDD specification:

- **Required**: `title`, `summary`, `keywords`, `Conventions`
- **Recommended**: 16 attributes including `creator_name`, `license`,
  `geospatial_*`, `time_coverage_*`
- **Suggested**: 14 attributes including `publisher_*`, `platform`

Cross-attribute consistency checks:
- `geospatial_lat_min` < `geospatial_lat_max`
- `time_coverage_start` < `time_coverage_end`

## 6. YAML Rules DSL

### 6.1 Rule Types

| Type              | Target | Description                               |
|-------------------|--------|-------------------------------------------|
| `xpath_exists`    | XML    | Element must exist                        |
| `xpath_not_empty` | XML    | Element text must be non-empty            |
| `xpath_regex`     | XML    | Element text must match regex             |
| `attr_exists`     | NetCDF | Global attribute must exist               |
| `attr_regex`      | NetCDF | Attribute value must match regex          |
| `file_exists`     | Dir    | Named file must exist in directory        |

### 6.2 Rule Schema

```yaml
rules:
  - id: RULE-001            # unique identifier
    description: "..."       # human-readable message
    severity: error|warning|info
    check:
      type: xpath_exists     # rule type
      xpath: "//gmd:..."     # type-specific parameters
    suggestion: "..."        # fix recommendation
    enabled: true|false      # optional, default true
```

## 7. FAIR Self-Scoring

### 7.1 Scoring Criteria

Each FAIR principle is scored on [0.0, 1.0]:

**Findable:**
- F1: Has globally unique identifier
- F2: Rich metadata (title + abstract + keywords)
- F3: Dataset identifier present

**Accessible:**
- A1: Standard retrieval protocol (online resource URL)
- A2: Metadata accessible (contact information)

**Interoperable:**
- I1: Formal language (XML namespaces)
- I2: FAIR vocabularies (thesaurus reference)
- I3: Qualified cross-references

**Reusable:**
- R1.1: License/constraints
- R1.2: Provenance/lineage
- R1.3: Community standards (ISO 19115)

### 7.2 Grading

| Overall Score | Grade |
|---------------|-------|
| >= 90%        | A     |
| >= 80%        | B     |
| >= 70%        | C     |
| >= 60%        | D     |
| < 60%         | F     |

## 8. Checksum Verification

Supports two checksum formats:

1. **Aggregate manifest** (`MANIFEST.sha256`) — one file, multiple entries
2. **Per-file sidecar** (`*.nc.sha256`) — one checksum per data file

Format: `<sha256_hex>  <filename>` (compatible with `sha256sum -c`).

## 9. References

- ISO 19115-2:2019 — Geographic information — Metadata — Part 2: Extensions
  for acquisition and processing.
- CF Metadata Conventions v1.8 (2020). http://cfconventions.org/
- Attribute Convention for Data Discovery 1.3 (2015).
  https://wiki.esipfed.org/ACDD_1.3
- FAIR Data Principles (Wilkinson et al., 2016). doi:10.1038/sdata.2016.18
- Schematron (ISO/IEC 19757-3:2020).
