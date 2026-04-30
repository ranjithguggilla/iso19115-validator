"""Tests for the CLI interface."""

from click.testing import CliRunner

from isolint.cli import main


class TestCLI:
    def test_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "isolint" in result.output

    def test_check_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["check", "--help"])
        assert result.exit_code == 0
        assert "PATH" in result.output

    def test_check_valid_xml(self, valid_xml):
        runner = CliRunner()
        result = runner.invoke(main, ["check", str(valid_xml)])
        assert result.exit_code == 0
        assert "PASSED" in result.output

    def test_check_incomplete_xml(self, incomplete_xml):
        runner = CliRunner()
        result = runner.invoke(main, ["check", str(incomplete_xml)])
        assert result.exit_code == 1  # fails due to errors
        assert "FAILED" in result.output

    def test_check_json_format(self, valid_xml):
        runner = CliRunner()
        result = runner.invoke(main, ["check", str(valid_xml), "--format", "json"])
        assert result.exit_code == 0
        assert '"passed": true' in result.output

    def test_check_markdown_format(self, valid_xml):
        runner = CliRunner()
        result = runner.invoke(main, ["check", str(valid_xml), "--format", "markdown"])
        assert result.exit_code == 0
        assert "# Compliance Report" in result.output

    def test_check_with_output_file(self, valid_xml, tmp_path):
        output = tmp_path / "report.json"
        runner = CliRunner()
        result = runner.invoke(main, ["check", str(valid_xml), "-o", str(output)])
        assert result.exit_code == 0
        assert output.exists()

    def test_suggest_command(self, valid_xml):
        runner = CliRunner()
        result = runner.invoke(main, ["suggest", str(valid_xml)])
        assert result.exit_code == 0

    def test_suggest_json(self, valid_xml):
        runner = CliRunner()
        result = runner.invoke(main, ["suggest", str(valid_xml), "--format", "json"])
        assert result.exit_code == 0
        assert "[" in result.output  # JSON array

    def test_diff_identical(self, valid_xml):
        runner = CliRunner()
        result = runner.invoke(main, ["diff", str(valid_xml), str(valid_xml)])
        assert result.exit_code == 0
        assert "identical" in result.output.lower()

    def test_fair_command(self, valid_xml):
        runner = CliRunner()
        result = runner.invoke(main, ["fair", str(valid_xml)])
        assert result.exit_code == 0
        assert "FAIR Score" in result.output

    def test_fair_json(self, valid_xml):
        runner = CliRunner()
        result = runner.invoke(main, ["fair", str(valid_xml), "--format", "json"])
        assert result.exit_code == 0
        assert '"grade"' in result.output

    def test_version(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "1.0.0" in result.output
