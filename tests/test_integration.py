"""Integration tests for the full system (requires GOOGLE_API_KEY)."""

import os
import pytest
from click.testing import CliRunner
from graph_agent.cli import main


@pytest.mark.skipif(
    not os.environ.get("GOOGLE_API_KEY"),
    reason="GOOGLE_API_KEY not set - skipping integration tests",
)
class TestIntegrationWithRealLLM:
    """Integration tests that use the real Gemini LLM."""

    def test_direct_mode_off_topic_real_llm(self):
        """Test direct mode with off-topic request using real LLM."""
        runner = CliRunner()
        result = runner.invoke(main, ["make me a sandwich"])

        assert result.exit_code == 0
        assert "can only help you create charts" in result.output.lower()

    def test_direct_mode_chart_request_real_llm(self):
        """Test direct mode with chart request using real LLM."""
        runner = CliRunner()
        result = runner.invoke(main, ["A=10, B=20, C=30"])

        assert result.exit_code == 0
        assert "chart saved:" in result.output.lower()

    def test_conversational_mode_real_llm(self):
        """Test conversational mode with real LLM."""
        runner = CliRunner()
        result = runner.invoke(main, input="create a line chart\nexit\n")

        assert result.exit_code == 0
        assert "welcome" in result.output.lower()
        assert "goodbye" in result.output.lower()


def test_cli_without_api_key(monkeypatch):
    """Test that CLI fails gracefully without API key."""
    runner = CliRunner()

    # Remove API key from actual environment
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    # Use isolated filesystem to ensure no .env file exists
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["test"])

        # Should exit with error
        assert result.exit_code != 0
        assert "GOOGLE_API_KEY" in result.output
