## Improvement Suggestions

Found **5** suggestions for metadata improvement.

### 1. 🔴 [HIGH] Add a DOI or persistent identifier

**Category:** findability

A DOI makes the dataset findable and citable. Register with DataCite or Zenodo.

**XPath:** `//gmd:identifier`

```
<gco:CharacterString>10.5281/zenodo.1234567</gco:CharacterString>
```

### 2. 🔴 [HIGH] Add temporal extent

**Category:** completeness

Temporal coverage helps users find data for their time period of interest.

**XPath:** `//gmd:identificationInfo//gmd:extent//gmd:temporalElement`

### 3. 🟡 [MEDIUM] Link keywords to a controlled vocabulary

**Category:** interoperability

Reference a thesaurus (e.g., GCMD Science Keywords) for machine-readable keywords.

**XPath:** `//gmd:descriptiveKeywords/gmd:MD_Keywords/gmd:thesaurusName`

### 4. 🟡 [MEDIUM] Add data quality and lineage information

**Category:** reusability

Lineage describes how the data was collected and processed.

**XPath:** `//gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:lineage`

### 5. 🟡 [MEDIUM] Add distribution information

**Category:** accessibility

Specify how the data can be accessed (URL, format, protocol).

**XPath:** `//gmd:distributionInfo`
