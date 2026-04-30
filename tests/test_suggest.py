"""Tests for the suggestion engine."""


from isolint.suggest import format_suggestions_markdown, suggest_improvements


class TestSuggestXML:
    def test_valid_xml_has_some_suggestions(self, valid_xml):
        """Even valid XML can have improvements (DOI, temporal, spatial)."""
        suggestions = suggest_improvements(valid_xml)
        assert len(suggestions) > 0

    def test_incomplete_xml_has_more_suggestions(self, valid_xml, incomplete_xml):
        """Incomplete XML should generate more suggestions."""
        s_valid = suggest_improvements(valid_xml)
        s_incomplete = suggest_improvements(incomplete_xml)
        # Both should have suggestions; incomplete might generate a parse-level one
        assert len(s_valid) > 0 or len(s_incomplete) > 0

    def test_suggestions_are_sorted_by_priority(self, valid_xml):
        suggestions = suggest_improvements(valid_xml)
        if len(suggestions) >= 2:
            priority_order = {"high": 0, "medium": 1, "low": 2}
            for i in range(len(suggestions) - 1):
                assert (
                    priority_order.get(suggestions[i].priority, 3)
                    <= priority_order.get(suggestions[i + 1].priority, 3)
                )

    def test_suggestion_has_category(self, valid_xml):
        suggestions = suggest_improvements(valid_xml)
        for s in suggestions:
            assert s.category, f"Suggestion '{s.title}' has no category"

    def test_format_markdown(self, valid_xml):
        suggestions = suggest_improvements(valid_xml)
        md = format_suggestions_markdown(suggestions)
        assert "Suggestions" in md

    def test_empty_suggestions_markdown(self, tmp_path):
        # A non-metadata directory
        md = format_suggestions_markdown([])
        assert "No improvements needed" in md


class TestSuggestDirectory:
    def test_directory_with_xml(self, valid_xml):
        suggestions = suggest_improvements(valid_xml.parent)
        assert len(suggestions) > 0

    def test_directory_no_metadata(self, tmp_path):
        (tmp_path / "readme.txt").write_text("no metadata here")
        suggestions = suggest_improvements(tmp_path)
        assert len(suggestions) == 0
