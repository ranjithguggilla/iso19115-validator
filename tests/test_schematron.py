"""Tests for Schematron policy validation."""

import textwrap

from isolint.schematron import validate_schematron


class TestSchematron:
    def test_valid_date_no_error(self, valid_xml):
        """Valid ISO 8601 date should produce no date errors."""
        findings = validate_schematron(valid_xml)
        date_errors = [f for f in findings if f.rule_id == "SCH-001"]
        assert len(date_errors) == 0

    def test_invalid_date_format(self, tmp_path):
        """Non-ISO date should produce SCH-001 error."""
        xml = tmp_path / "bad_date.xml"
        xml.write_text(textwrap.dedent("""\
            <?xml version="1.0"?>
            <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd"
                             xmlns:gco="http://www.isotc211.org/2005/gco">
              <gmd:dateStamp>
                <gco:Date>April 15, 2026</gco:Date>
              </gmd:dateStamp>
            </gmd:MD_Metadata>
        """))
        findings = validate_schematron(xml)
        date_errors = [f for f in findings if f.rule_id == "SCH-001"]
        assert len(date_errors) >= 1

    def test_invalid_geographic_bounds(self, tmp_path):
        """South > North should produce SCH-002 error."""
        xml = tmp_path / "bad_bbox.xml"
        xml.write_text(textwrap.dedent("""\
            <?xml version="1.0"?>
            <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd"
                             xmlns:gco="http://www.isotc211.org/2005/gco">
              <gmd:EX_GeographicBoundingBox>
                <gmd:westBoundLongitude><gco:Decimal>-90</gco:Decimal></gmd:westBoundLongitude>
                <gmd:eastBoundLongitude><gco:Decimal>-80</gco:Decimal></gmd:eastBoundLongitude>
                <gmd:southBoundLatitude><gco:Decimal>40</gco:Decimal></gmd:southBoundLatitude>
                <gmd:northBoundLatitude><gco:Decimal>30</gco:Decimal></gmd:northBoundLatitude>
              </gmd:EX_GeographicBoundingBox>
            </gmd:MD_Metadata>
        """))
        findings = validate_schematron(xml)
        bbox_errors = [f for f in findings if f.rule_id == "SCH-002"]
        assert any("South bound > north bound" in f.message for f in bbox_errors)

    def test_invalid_topic_category(self, tmp_path):
        """Invalid topic category should produce SCH-003 error."""
        xml = tmp_path / "bad_topic.xml"
        xml.write_text(textwrap.dedent("""\
            <?xml version="1.0"?>
            <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd"
                             xmlns:gco="http://www.isotc211.org/2005/gco">
              <gmd:topicCategory>
                <gmd:MD_TopicCategoryCode>invalidCategory</gmd:MD_TopicCategoryCode>
              </gmd:topicCategory>
            </gmd:MD_Metadata>
        """))
        findings = validate_schematron(xml)
        topic_errors = [f for f in findings if f.rule_id == "SCH-003"]
        assert len(topic_errors) >= 1

    def test_empty_characterstring_warning(self, tmp_path):
        """Empty CharacterString elements should produce SCH-006 warning."""
        xml = tmp_path / "empty_str.xml"
        xml.write_text(textwrap.dedent("""\
            <?xml version="1.0"?>
            <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd"
                             xmlns:gco="http://www.isotc211.org/2005/gco">
              <gmd:fileIdentifier>
                <gco:CharacterString></gco:CharacterString>
              </gmd:fileIdentifier>
            </gmd:MD_Metadata>
        """))
        findings = validate_schematron(xml)
        empty_warnings = [f for f in findings if f.rule_id == "SCH-006"]
        assert len(empty_warnings) >= 1

    def test_short_abstract_warning(self, tmp_path):
        """Short abstract should produce SCH-007 warning."""
        xml = tmp_path / "short_abstract.xml"
        xml.write_text(textwrap.dedent("""\
            <?xml version="1.0"?>
            <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd"
                             xmlns:gco="http://www.isotc211.org/2005/gco">
              <gmd:abstract>
                <gco:CharacterString>Too short.</gco:CharacterString>
              </gmd:abstract>
            </gmd:MD_Metadata>
        """))
        findings = validate_schematron(xml)
        abstract_warnings = [f for f in findings if f.rule_id == "SCH-007"]
        assert len(abstract_warnings) >= 1

    def test_malformed_xml_returns_empty(self, malformed_xml):
        """Malformed XML should return empty findings (XSD catches this)."""
        findings = validate_schematron(malformed_xml)
        assert len(findings) == 0
