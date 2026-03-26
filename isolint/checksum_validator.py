"""
SHA-256 checksum manifest validation.

Verifies data integrity by checking files against their recorded
SHA-256 digests. Supports both per-file sidecars (*.sha256) and
aggregate MANIFEST.sha256 files.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import List

from isolint.report import Finding, Severity

logger = logging.getLogger(__name__)


def sha256_file(path: Path) -> str:
    """Compute SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_checksums(checksum_files: List[Path], root: Path) -> List[Finding]:
    """
    Verify SHA-256 checksums from manifest and sidecar files.

    Supports two formats:
    1. MANIFEST.sha256: aggregate file with multiple entries
       Format: <hex_digest>  <relative_path>
    2. *.nc.sha256: per-file sidecar
       Format: <hex_digest>  <filename>

    Args:
        checksum_files: List of .sha256 files to verify.
        root: Root directory for resolving relative paths.

    Returns:
        List of findings (errors for mismatches, info for verified files).
    """
    findings: List[Finding] = []
    verified = 0
    failed = 0

    for checksum_file in checksum_files:
        lines = checksum_file.read_text().strip().splitlines()
        base_dir = checksum_file.parent

        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Parse "digest  filename" format (two spaces separator)
            parts = line.split("  ", 1)
            if len(parts) != 2:
                findings.append(Finding(
                    severity=Severity.WARNING,
                    message=f"Malformed checksum line {line_num} in {checksum_file.name}",
                    source=str(checksum_file),
                    line=line_num,
                    rule_id="CHK-001",
                    suggestion="Format: <sha256_hex>  <filename>",
                ))
                continue

            expected_digest, rel_path = parts
            expected_digest = expected_digest.lower().strip()

            # Resolve file path
            target_file = base_dir / rel_path
            if not target_file.exists():
                # Try from root
                target_file = root / rel_path
                if not target_file.exists():
                    findings.append(Finding(
                        severity=Severity.ERROR,
                        message=f"File not found: {rel_path}",
                        source=str(checksum_file),
                        line=line_num,
                        rule_id="CHK-002",
                        suggestion=f"Ensure '{rel_path}' exists relative to the manifest.",
                    ))
                    failed += 1
                    continue

            # Compute and compare
            actual_digest = sha256_file(target_file)
            if actual_digest != expected_digest:
                findings.append(Finding(
                    severity=Severity.ERROR,
                    message=(
                        f"Checksum mismatch for {rel_path}: "
                        f"expected {expected_digest[:16]}..., "
                        f"got {actual_digest[:16]}..."
                    ),
                    source=str(checksum_file),
                    line=line_num,
                    rule_id="CHK-003",
                    suggestion="File may be corrupted. Re-download or regenerate.",
                ))
                failed += 1
            else:
                verified += 1

    if verified > 0:
        findings.append(Finding(
            severity=Severity.INFO,
            message=f"Checksum verification: {verified} files OK, {failed} failed",
            source=str(root),
            rule_id="CHK-100",
        ))

    return findings
