"""Tests for checksum validation."""

import hashlib

from isolint.checksum_validator import sha256_file, validate_checksums
from isolint.report import Severity


class TestSHA256File:
    def test_computes_correct_hash(self, tmp_path):
        f = tmp_path / "data.txt"
        f.write_text("hello world\n")
        expected = hashlib.sha256(b"hello world\n").hexdigest()
        assert sha256_file(f) == expected

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_bytes(b"")
        expected = hashlib.sha256(b"").hexdigest()
        assert sha256_file(f) == expected


class TestValidateChecksums:
    def test_valid_checksum_passes(self, valid_checksum_file):
        root = valid_checksum_file.parent
        findings = validate_checksums([valid_checksum_file], root)
        errors = [f for f in findings if f.severity == Severity.ERROR]
        assert len(errors) == 0
        infos = [f for f in findings if f.rule_id == "CHK-100"]
        assert len(infos) == 1
        assert "1 files OK" in infos[0].message

    def test_bad_checksum_fails(self, bad_checksum_file):
        root = bad_checksum_file.parent
        findings = validate_checksums([bad_checksum_file], root)
        errors = [f for f in findings if f.severity == Severity.ERROR]
        assert len(errors) >= 1
        assert any("mismatch" in f.message.lower() for f in errors)

    def test_missing_file_error(self, tmp_path):
        checksum_file = tmp_path / "missing.sha256"
        checksum_file.write_text("abc123  nonexistent.dat\n")
        findings = validate_checksums([checksum_file], tmp_path)
        errors = [f for f in findings if f.severity == Severity.ERROR]
        assert len(errors) >= 1
        assert any("not found" in f.message.lower() for f in errors)

    def test_malformed_line_warning(self, tmp_path):
        checksum_file = tmp_path / "bad_format.sha256"
        checksum_file.write_text("this is not a valid checksum line\n")
        findings = validate_checksums([checksum_file], tmp_path)
        warnings = [f for f in findings if f.severity == Severity.WARNING]
        assert len(warnings) >= 1

    def test_manifest_multiple_files(self, tmp_path):
        """Test a MANIFEST.sha256 with multiple entries."""
        for name in ["a.dat", "b.dat", "c.dat"]:
            (tmp_path / name).write_text(f"content of {name}\n")

        lines = []
        for name in ["a.dat", "b.dat", "c.dat"]:
            digest = sha256_file(tmp_path / name)
            lines.append(f"{digest}  {name}")

        manifest = tmp_path / "MANIFEST.sha256"
        manifest.write_text("\n".join(lines) + "\n")

        findings = validate_checksums([manifest], tmp_path)
        errors = [f for f in findings if f.severity == Severity.ERROR]
        assert len(errors) == 0
        infos = [f for f in findings if f.rule_id == "CHK-100"]
        assert "3 files OK" in infos[0].message
