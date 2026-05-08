# Compliance Report

**Target:** `/Users/guggillaranjith/Documents/Claude/Projects/GRIIDC/iso19115-validator/examples/incomplete_metadata.xml`  
**Timestamp:** 2026-05-15T22:03:22Z  
**Status:** ✗ FAILED  

## Summary

| Level    | Count |
|----------|-------|
| Errors   | 3 |
| Warnings | 0 |
| Info     | 4 |
| **Total**| **7** |

## Findings

### 1. 🔴 [ERROR] Required element missing: gmd:contact

- **Source:** `/Users/guggillaranjith/Documents/Claude/Projects/GRIIDC/iso19115-validator/examples/incomplete_metadata.xml`
- **XPath:** `//gmd:contact`
- **Rule:** `XSD-010`
- **Fix:** Add the required element gmd:contact to the metadata record.

### 2. 🔴 [ERROR] Required element missing: gmd:dateStamp

- **Source:** `/Users/guggillaranjith/Documents/Claude/Projects/GRIIDC/iso19115-validator/examples/incomplete_metadata.xml`
- **XPath:** `//gmd:dateStamp`
- **Rule:** `XSD-010`
- **Fix:** Add the required element gmd:dateStamp to the metadata record.

### 3. 🔴 [ERROR] Required element missing: gmd:identificationInfo

- **Source:** `/Users/guggillaranjith/Documents/Claude/Projects/GRIIDC/iso19115-validator/examples/incomplete_metadata.xml`
- **XPath:** `//gmd:identificationInfo`
- **Rule:** `XSD-010`
- **Fix:** Add the required element gmd:identificationInfo to the metadata record.

### 4. 🔵 [INFO] Recommended element missing: gmd:abstract

- **Source:** `/Users/guggillaranjith/Documents/Claude/Projects/GRIIDC/iso19115-validator/examples/incomplete_metadata.xml`
- **XPath:** `//gmd:identificationInfo//gmd:abstract/gco:CharacterString`
- **Rule:** `XSD-020`
- **Fix:** Consider adding gmd:abstract for better metadata completeness.

### 5. 🔵 [INFO] Recommended element missing: gmd:topicCategory

- **Source:** `/Users/guggillaranjith/Documents/Claude/Projects/GRIIDC/iso19115-validator/examples/incomplete_metadata.xml`
- **XPath:** `//gmd:identificationInfo//gmd:topicCategory`
- **Rule:** `XSD-020`
- **Fix:** Consider adding gmd:topicCategory for better metadata completeness.

### 6. 🔵 [INFO] Recommended element missing: gmd:extent

- **Source:** `/Users/guggillaranjith/Documents/Claude/Projects/GRIIDC/iso19115-validator/examples/incomplete_metadata.xml`
- **XPath:** `//gmd:identificationInfo//gmd:extent`
- **Rule:** `XSD-020`
- **Fix:** Consider adding gmd:extent for better metadata completeness.

### 7. 🔵 [INFO] Recommended element missing: gmd:dataQualityInfo

- **Source:** `/Users/guggillaranjith/Documents/Claude/Projects/GRIIDC/iso19115-validator/examples/incomplete_metadata.xml`
- **XPath:** `//gmd:dataQualityInfo`
- **Rule:** `XSD-020`
- **Fix:** Consider adding gmd:dataQualityInfo for better metadata completeness.
