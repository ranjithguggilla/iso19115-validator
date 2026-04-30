"""Shared fixtures for isolint tests."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest


@pytest.fixture
def tmp_dir(tmp_path):
    """Provide a clean temp directory."""
    return tmp_path


@pytest.fixture
def valid_xml(tmp_path) -> Path:
    """Create a valid ISO 19115-2 XML file."""
    content = textwrap.dedent("""\
        <?xml version="1.0" encoding="UTF-8"?>
        <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd"
                         xmlns:gco="http://www.isotc211.org/2005/gco">
          <gmd:fileIdentifier>
            <gco:CharacterString>test-dataset-001</gco:CharacterString>
          </gmd:fileIdentifier>
          <gmd:language>
            <gco:CharacterString>eng</gco:CharacterString>
          </gmd:language>
          <gmd:contact>
            <gmd:CI_ResponsibleParty>
              <gmd:individualName>
                <gco:CharacterString>Test Author</gco:CharacterString>
              </gmd:individualName>
            </gmd:CI_ResponsibleParty>
          </gmd:contact>
          <gmd:dateStamp>
            <gco:Date>2026-04-15</gco:Date>
          </gmd:dateStamp>
          <gmd:identificationInfo>
            <gmd:MD_DataIdentification>
              <gmd:citation>
                <gmd:CI_Citation>
                  <gmd:title>
                    <gco:CharacterString>Test Dataset Title</gco:CharacterString>
                  </gmd:title>
                </gmd:CI_Citation>
              </gmd:citation>
              <gmd:abstract>
                <gco:CharacterString>A sufficiently long abstract that provides enough detail about this test dataset for validation purposes.</gco:CharacterString>
              </gmd:abstract>
            </gmd:MD_DataIdentification>
          </gmd:identificationInfo>
        </gmd:MD_Metadata>
    """)
    xml_path = tmp_path / "valid.xml"
    xml_path.write_text(content)
    return xml_path


@pytest.fixture
def incomplete_xml(tmp_path) -> Path:
    """Create an XML file missing required elements."""
    content = textwrap.dedent("""\
        <?xml version="1.0" encoding="UTF-8"?>
        <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd"
                         xmlns:gco="http://www.isotc211.org/2005/gco">
          <gmd:fileIdentifier>
            <gco:CharacterString>incomplete-test</gco:CharacterString>
          </gmd:fileIdentifier>
          <gmd:language>
            <gco:CharacterString>eng</gco:CharacterString>
          </gmd:language>
        </gmd:MD_Metadata>
    """)
    xml_path = tmp_path / "incomplete.xml"
    xml_path.write_text(content)
    return xml_path


@pytest.fixture
def malformed_xml(tmp_path) -> Path:
    """Create a malformed XML file."""
    xml_path = tmp_path / "malformed.xml"
    xml_path.write_text("<root><unclosed>")
    return xml_path


@pytest.fixture
def valid_checksum_file(tmp_path) -> Path:
    """Create a file and its matching checksum sidecar."""
    import hashlib
    data_file = tmp_path / "test.dat"
    data_file.write_text("test data content\n")
    digest = hashlib.sha256(data_file.read_bytes()).hexdigest()
    checksum_file = tmp_path / "test.dat.sha256"
    checksum_file.write_text(f"{digest}  test.dat\n")
    return checksum_file


@pytest.fixture
def bad_checksum_file(tmp_path) -> Path:
    """Create a file with a mismatched checksum."""
    data_file = tmp_path / "bad.dat"
    data_file.write_text("real content\n")
    checksum_file = tmp_path / "bad.dat.sha256"
    checksum_file.write_text("0000000000000000000000000000000000000000000000000000000000000000  bad.dat\n")
    return checksum_file


@pytest.fixture
def sample_rules_yaml(tmp_path) -> Path:
    """Create a sample YAML rules file."""
    content = textwrap.dedent("""\
        name: test-rules
        version: "1.0"
        rules:
          - id: TEST-001
            description: "Must have a title"
            severity: error
            check:
              type: xpath_exists
              xpath: "//gmd:title/gco:CharacterString"
            suggestion: "Add a title element."

          - id: TEST-002
            description: "File identifier should match pattern"
            severity: warning
            check:
              type: xpath_regex
              xpath: "//gmd:fileIdentifier/gco:CharacterString"
              pattern: "^[a-z]"
            suggestion: "Start with lowercase."

          - id: TEST-003
            description: "README must exist"
            severity: info
            check:
              type: file_exists
              filename: "README.txt"
            suggestion: "Add a README."
    """)
    rules_path = tmp_path / "rules.yaml"
    rules_path.write_text(content)
    return rules_path
