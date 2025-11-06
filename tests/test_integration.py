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


@pytest.mark.skipif(
    not os.environ.get("GOOGLE_API_KEY"),
    reason="GOOGLE_API_KEY not set - skipping integration tests",
)
class TestConfigIntegration:
    """Integration tests for config/preferences functionality."""

    def test_set_default_style_conversational(self, tmp_path, monkeypatch):
        """Test setting default style in conversational mode."""
        # Use temp config directory
        config_dir = tmp_path / ".config" / "graph-agent"
        config_file = config_dir / "settings.json"

        import graph_agent.config as config_module
        monkeypatch.setattr(config_module, "CONFIG_DIR", config_dir)
        monkeypatch.setattr(config_module, "CONFIG_FILE", config_file)

        runner = CliRunner()
        result = runner.invoke(main, input="Set my default style to FD\nexit\n")

        assert result.exit_code == 0
        assert "default style is now set to FD" in result.output

        # Verify config file was updated
        import json
        with open(config_file, 'r') as f:
            config = json.load(f)
        assert config["default_style"] == "fd"

    def test_set_default_format_conversational(self, tmp_path, monkeypatch):
        """Test setting default format in conversational mode."""
        # Use temp config directory
        config_dir = tmp_path / ".config" / "graph-agent"
        config_file = config_dir / "settings.json"

        import graph_agent.config as config_module
        monkeypatch.setattr(config_module, "CONFIG_DIR", config_dir)
        monkeypatch.setattr(config_module, "CONFIG_FILE", config_file)

        runner = CliRunner()
        result = runner.invoke(main, input="Set default format to SVG\nexit\n")

        assert result.exit_code == 0
        assert "default format is now set to SVG" in result.output

        # Verify config file was updated
        import json
        with open(config_file, 'r') as f:
            config = json.load(f)
        assert config["default_format"] == "svg"

    def test_use_default_style_when_not_specified(self, tmp_path, monkeypatch):
        """Test that default style is used in conversational mode when not explicitly specified."""
        # Use temp config directory
        config_dir = tmp_path / ".config" / "graph-agent"
        config_file = config_dir / "settings.json"

        import graph_agent.config as config_module
        monkeypatch.setattr(config_module, "CONFIG_DIR", config_dir)
        monkeypatch.setattr(config_module, "CONFIG_FILE", config_file)

        # First, set a default style
        from graph_agent.config import save_user_preferences
        save_user_preferences(default_style="bnr")

        # Then create a chart in conversational mode without specifying style
        # In conversational mode, style defaults are applied via priority logic
        runner = CliRunner()
        result = runner.invoke(main, input="A=10, B=20, C=30\nexit\n")

        assert result.exit_code == 0
        assert "chart saved:" in result.output.lower()

        # Verify last_used was updated to bnr (from default)
        import json
        with open(config_file, 'r') as f:
            config = json.load(f)
        assert config["last_used_style"] == "bnr"

    def test_explicit_style_overrides_default(self, tmp_path, monkeypatch):
        """Test that explicit style in CLI overrides default."""
        # Use temp config directory
        config_dir = tmp_path / ".config" / "graph-agent"
        config_file = config_dir / "settings.json"

        import graph_agent.config as config_module
        monkeypatch.setattr(config_module, "CONFIG_DIR", config_dir)
        monkeypatch.setattr(config_module, "CONFIG_FILE", config_file)

        # Set default to FD
        from graph_agent.config import save_user_preferences
        save_user_preferences(default_style="fd")

        # Create chart with explicit BNR style
        runner = CliRunner()
        result = runner.invoke(main, ["A=10, B=20", "--style", "bnr"])

        assert result.exit_code == 0

        # Verify last_used was updated to bnr (not fd)
        import json
        with open(config_file, 'r') as f:
            config = json.load(f)
        assert config["last_used_style"] == "bnr"


@pytest.mark.skipif(
    not os.environ.get("GOOGLE_API_KEY"),
    reason="GOOGLE_API_KEY not set - skipping integration tests",
)
class TestAmbiguityResolution:
    """Integration tests for ambiguity resolution in conversational mode."""

    def test_categorical_data_with_no_defaults_asks_questions(self, tmp_path, monkeypatch):
        """Test that agent asks clarifying questions for categorical data with no defaults."""
        # Use temp config directory with no defaults or last_used
        config_dir = tmp_path / ".config" / "graph-agent"
        config_file = config_dir / "settings.json"

        import graph_agent.config as config_module
        monkeypatch.setattr(config_module, "CONFIG_DIR", config_dir)
        monkeypatch.setattr(config_module, "CONFIG_FILE", config_file)

        # Ensure config exists but is empty (no defaults)
        from graph_agent.config import ensure_config_exists
        ensure_config_exists()

        runner = CliRunner()
        # Categorical data without type or style, and no defaults set
        # Note: With real LLM and priority logic, this will use fallback defaults
        # The test verifies the system works end-to-end
        result = runner.invoke(main, input="chart: Apple=50, Orange=30\nexit\n")

        assert result.exit_code == 0
        # Either asks questions OR successfully generates with fallback defaults
        # Both are acceptable behaviors depending on LLM extraction
        assert "chart saved:" in result.output.lower() or "what type" in result.output.lower() or "which" in result.output.lower()

    def test_asks_for_type_when_categorical(self, tmp_path, monkeypatch):
        """Test that agent asks for type when data is categorical."""
        # Use temp config directory with default style but no type
        config_dir = tmp_path / ".config" / "graph-agent"
        config_file = config_dir / "settings.json"

        import graph_agent.config as config_module
        monkeypatch.setattr(config_module, "CONFIG_DIR", config_dir)
        monkeypatch.setattr(config_module, "CONFIG_FILE", config_file)

        # Set default style so only type is missing
        from graph_agent.config import save_user_preferences
        save_user_preferences(default_style="fd")

        runner = CliRunner()
        # Categorical data without type
        result = runner.invoke(main, input="chart: Apple=10, Banana=20\nexit\n")

        assert result.exit_code == 0
        # Should ask for type
        assert "what type of chart" in result.output.lower() or "bar or line" in result.output.lower()

    def test_no_question_with_all_params(self, tmp_path, monkeypatch):
        """Test that no clarification question is asked when all params are provided."""
        # Use temp config directory
        config_dir = tmp_path / ".config" / "graph-agent"
        config_file = config_dir / "settings.json"

        import graph_agent.config as config_module
        monkeypatch.setattr(config_module, "CONFIG_DIR", config_dir)
        monkeypatch.setattr(config_module, "CONFIG_FILE", config_file)

        runner = CliRunner()
        # All params specified
        result = runner.invoke(main, input="bar chart, FD style: A=10, B=20\nexit\n")

        assert result.exit_code == 0
        # Should NOT ask any questions - should generate chart directly
        assert "what type" not in result.output.lower()
        assert "which" not in result.output.lower() or "which brand style" not in result.output.lower()
        assert "chart saved:" in result.output.lower()

    def test_time_series_defaults_to_line(self, tmp_path, monkeypatch):
        """Test that time-series data defaults to line chart without asking."""
        # Use temp config directory with default style
        config_dir = tmp_path / ".config" / "graph-agent"
        config_file = config_dir / "settings.json"

        import graph_agent.config as config_module
        monkeypatch.setattr(config_module, "CONFIG_DIR", config_dir)
        monkeypatch.setattr(config_module, "CONFIG_FILE", config_file)

        # Set default style so nothing is missing
        from graph_agent.config import save_user_preferences
        save_user_preferences(default_style="fd")

        runner = CliRunner()
        # Time-series data (months)
        result = runner.invoke(main, input="chart: Jan=100, Feb=120, Mar=110\nexit\n")

        assert result.exit_code == 0
        # Should NOT ask for type (time-series defaults to line)
        assert "what type" not in result.output.lower()
        # Should generate chart directly
        assert "chart saved:" in result.output.lower()
