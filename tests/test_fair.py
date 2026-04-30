"""Tests for FAIR self-scoring."""

import textwrap

from isolint.fair import FAIRScore, FAIRScorer


class TestFAIRScore:
    def test_overall_average(self):
        score = FAIRScore(findable=1.0, accessible=0.5, interoperable=0.5, reusable=0.0)
        assert score.overall == 0.5

    def test_grade_a(self):
        score = FAIRScore(findable=1.0, accessible=1.0, interoperable=1.0, reusable=1.0)
        assert score.grade == "A"

    def test_grade_f(self):
        score = FAIRScore(findable=0.0, accessible=0.0, interoperable=0.0, reusable=0.0)
        assert score.grade == "F"

    def test_grade_b(self):
        score = FAIRScore(findable=0.9, accessible=0.8, interoperable=0.8, reusable=0.8)
        assert score.grade == "B"

    def test_to_dict(self):
        score = FAIRScore(findable=0.8, accessible=0.6, interoperable=0.4, reusable=0.2)
        d = score.to_dict()
        assert d["findable"] == 0.8
        assert d["grade"] == "F"  # overall = 0.5
        assert "overall" in d

    def test_to_markdown(self):
        score = FAIRScore(
            findable=1.0, accessible=1.0, interoperable=1.0, reusable=1.0,
            details={"Findable": ["test detail"]},
        )
        md = score.to_markdown()
        assert "FAIR Self-Assessment" in md
        assert "test detail" in md
        assert "Grade: A" in md


class TestFAIRScorerXML:
    def test_score_valid_xml(self, valid_xml):
        scorer = FAIRScorer()
        score = scorer.score_xml(valid_xml)
        # Valid XML has file identifier, title, abstract
        assert score.findable > 0
        assert score.interoperable > 0
        assert score.overall > 0

    def test_score_incomplete_xml(self, incomplete_xml):
        scorer = FAIRScorer()
        score = scorer.score_xml(incomplete_xml)
        # Incomplete XML has ID but not much else
        assert score.findable > 0  # has fileIdentifier
        assert score.overall < 1.0  # not perfect

    def test_score_malformed_xml(self, malformed_xml):
        scorer = FAIRScorer()
        score = scorer.score_xml(malformed_xml)
        assert score.overall == 0.0

    def test_rich_metadata_scores_higher(self, tmp_path):
        """XML with keywords, abstract, and title should score higher on Findable."""
        rich_xml = tmp_path / "rich.xml"
        rich_xml.write_text(textwrap.dedent("""\
            <?xml version="1.0"?>
            <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd"
                             xmlns:gco="http://www.isotc211.org/2005/gco">
              <gmd:fileIdentifier>
                <gco:CharacterString>rich-dataset</gco:CharacterString>
              </gmd:fileIdentifier>
              <gmd:contact>
                <gco:CharacterString>Someone</gco:CharacterString>
              </gmd:contact>
              <gmd:identificationInfo>
                <gmd:title><gco:CharacterString>Rich Title</gco:CharacterString></gmd:title>
                <gmd:abstract>
                  <gco:CharacterString>A detailed abstract that is long enough to pass the 50-character threshold for quality scoring.</gco:CharacterString>
                </gmd:abstract>
                <gmd:keyword><gco:CharacterString>oceanography</gco:CharacterString></gmd:keyword>
              </gmd:identificationInfo>
            </gmd:MD_Metadata>
        """))
        scorer = FAIRScorer()
        score = scorer.score_xml(rich_xml)
        assert score.findable > 0.5
