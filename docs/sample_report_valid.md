# Compliance Report

**Target:** `examples/valid_metadata.xml`  
**Timestamp:** 2026-05-15T22:03:22Z  
**Status:** ✓ PASSED  

## Summary

| Level    | Count |
|----------|-------|
| Errors   | 0 |
| Warnings | 0 |
| Info     | 1 |
| **Total**| **1** |

## Findings

### 1. 🔵 [INFO] Recommended element missing: gmd:dataQualityInfo

- **Source:** `examples/valid_metadata.xml`
- **XPath:** `//gmd:dataQualityInfo`
- **Rule:** `XSD-020`
- **Fix:** Consider adding gmd:dataQualityInfo for better metadata completeness.
