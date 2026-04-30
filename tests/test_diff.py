"""Tests for the metadata diff engine."""

import textwrap

from isolint.diff import diff_xml


class TestDiffXML:
    def test_identical_files(self, valid_xml):
        """Diffing a file with itself should show no differences."""
        result = diff_xml(valid_xml, valid_xml)
        assert result.identical is True
        assert len(result.added) == 0
        assert len(result.removed) == 0
        assert len(result.changed) == 0

    def test_added_elements(self, tmp_path):
        """Elements in B but not A should appear as 'added'."""
        a = tmp_path / "a.xml"
        b = tmp_path / "b.xml"
        a.write_text(textwrap.dedent("""\
            <?xml version="1.0"?>
            <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd"
                             xmlns:gco="http://www.isotc211.org/2005/gco">
              <gmd:fileIdentifier>
                <gco:CharacterString>file-a</gco:CharacterString>
              </gmd:fileIdentifier>
            </gmd:MD_Metadata>
        """))
        b.write_text(textwrap.dedent("""\
            <?xml version="1.0"?>
            <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd"
                             xmlns:gco="http://www.isotc211.org/2005/gco">
              <gmd:fileIdentifier>
                <gco:CharacterString>file-a</gco:CharacterString>
              </gmd:fileIdentifier>
              <gmd:language>
                <gco:CharacterString>eng</gco:CharacterString>
              </gmd:language>
            </gmd:MD_Metadata>
        """))
        result = diff_xml(a, b)
        assert result.identical is False
        assert len(result.added) >= 1

    def test_changed_elements(self, tmp_path):
        """Modified text content should appear as 'changed'."""
        a = tmp_path / "a.xml"
        b = tmp_path / "b.xml"
        a.write_text(textwrap.dedent("""\
            <?xml version="1.0"?>
            <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd"
                             xmlns:gco="http://www.isotc211.org/2005/gco">
              <gmd:fileIdentifier>
                <gco:CharacterString>version-1</gco:CharacterString>
              </gmd:fileIdentifier>
            </gmd:MD_Metadata>
        """))
        b.write_text(textwrap.dedent("""\
            <?xml version="1.0"?>
            <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd"
                             xmlns:gco="http://www.isotc211.org/2005/gco">
              <gmd:fileIdentifier>
                <gco:CharacterString>version-2</gco:CharacterString>
              </gmd:fileIdentifier>
            </gmd:MD_Metadata>
        """))
        result = diff_xml(a, b)
        assert result.identical is False
        assert len(result.changed) >= 1
        assert any(c["value_a"] == "version-1" and c["value_b"] == "version-2" for c in result.changed)

    def test_to_json(self, valid_xml):
        result = diff_xml(valid_xml, valid_xml)
        j = result.to_json()
        assert '"identical": true' in j

    def test_to_markdown(self, valid_xml):
        result = diff_xml(valid_xml, valid_xml)
        md = result.to_markdown()
        assert "Identical" in md

    def test_malformed_xml_returns_empty_result(self, malformed_xml, valid_xml):
        result = diff_xml(malformed_xml, valid_xml)
        assert result.identical is False
        assert len(result.added) == 0
