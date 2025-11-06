"""Unit tests for config module."""

import json
import pytest
from pathlib import Path
from graph_agent.config import (
    load_user_preferences,
    save_user_preferences,
    update_last_used,
    get_config_file_path,
    DEFAULT_SETTINGS
)


@pytest.fixture
def temp_config_dir(tmp_path, monkeypatch):
    """Create temporary config directory for testing."""
    # Override CONFIG_DIR and CONFIG_FILE to use temp directory
    config_dir = tmp_path / ".config" / "graph-agent"
    config_file = config_dir / "settings.json"

    import graph_agent.config as config_module
    monkeypatch.setattr(config_module, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(config_module, "CONFIG_FILE", config_file)

    return config_dir


class TestConfigFileCreation:
    """Test config file creation and initialization."""

    def test_config_file_created_on_first_load(self, temp_config_dir):
        """Test that config file is created with defaults on first load."""
        prefs = load_user_preferences()

        # Verify defaults are returned
        assert prefs == DEFAULT_SETTINGS

        # Verify file was created
        config_file = temp_config_dir / "settings.json"
        assert config_file.exists()

        # Verify file contents
        with open(config_file, 'r') as f:
            file_contents = json.load(f)
        assert file_contents == DEFAULT_SETTINGS

    def test_config_directory_created_if_missing(self, temp_config_dir):
        """Test that config directory is created if it doesn't exist."""
        # Directory shouldn't exist yet
        assert not temp_config_dir.exists()

        # Load preferences should create it
        load_user_preferences()

        # Directory should now exist
        assert temp_config_dir.exists()


class TestLoadUserPreferences:
    """Test loading user preferences from config file."""

    def test_load_returns_defaults_for_new_config(self, temp_config_dir):
        """Test that load returns default values for new config."""
        prefs = load_user_preferences()

        assert prefs["default_style"] is None
        assert prefs["default_format"] is None
        assert prefs["last_used_style"] is None
        assert prefs["last_used_format"] is None

    def test_load_returns_saved_preferences(self, temp_config_dir):
        """Test that load returns previously saved preferences."""
        # Save some preferences
        save_user_preferences(default_style="bnr", default_format="svg")

        # Load and verify
        prefs = load_user_preferences()
        assert prefs["default_style"] == "bnr"
        assert prefs["default_format"] == "svg"
        assert prefs["last_used_style"] is None
        assert prefs["last_used_format"] is None


class TestSaveUserPreferences:
    """Test saving user preferences to config file."""

    def test_save_default_style(self, temp_config_dir):
        """Test saving default style preference."""
        save_user_preferences(default_style="fd")

        prefs = load_user_preferences()
        assert prefs["default_style"] == "fd"
        assert prefs["default_format"] is None

    def test_save_default_format(self, temp_config_dir):
        """Test saving default format preference."""
        save_user_preferences(default_format="png")

        prefs = load_user_preferences()
        assert prefs["default_style"] is None
        assert prefs["default_format"] == "png"

    def test_save_both_defaults(self, temp_config_dir):
        """Test saving both default style and format."""
        save_user_preferences(default_style="bnr", default_format="svg")

        prefs = load_user_preferences()
        assert prefs["default_style"] == "bnr"
        assert prefs["default_format"] == "svg"

    def test_save_updates_existing_values(self, temp_config_dir):
        """Test that save updates existing values without affecting others."""
        # Set initial values
        save_user_preferences(default_style="fd", default_format="png")

        # Update only style
        save_user_preferences(default_style="bnr")

        # Verify format unchanged
        prefs = load_user_preferences()
        assert prefs["default_style"] == "bnr"
        assert prefs["default_format"] == "png"

    def test_save_preserves_last_used(self, temp_config_dir):
        """Test that save_user_preferences preserves last_used fields."""
        # Set last_used values
        update_last_used(style="fd", format="png")

        # Update default values
        save_user_preferences(default_style="bnr")

        # Verify last_used unchanged
        prefs = load_user_preferences()
        assert prefs["last_used_style"] == "fd"
        assert prefs["last_used_format"] == "png"


class TestUpdateLastUsed:
    """Test updating last_used fields in config file."""

    def test_update_last_used_style(self, temp_config_dir):
        """Test updating last used style."""
        update_last_used(style="bnr")

        prefs = load_user_preferences()
        assert prefs["last_used_style"] == "bnr"
        assert prefs["last_used_format"] is None

    def test_update_last_used_format(self, temp_config_dir):
        """Test updating last used format."""
        update_last_used(format="svg")

        prefs = load_user_preferences()
        assert prefs["last_used_style"] is None
        assert prefs["last_used_format"] == "svg"

    def test_update_both_last_used(self, temp_config_dir):
        """Test updating both last used style and format."""
        update_last_used(style="fd", format="png")

        prefs = load_user_preferences()
        assert prefs["last_used_style"] == "fd"
        assert prefs["last_used_format"] == "png"

    def test_update_last_used_preserves_defaults(self, temp_config_dir):
        """Test that update_last_used preserves default fields."""
        # Set default values
        save_user_preferences(default_style="bnr", default_format="svg")

        # Update last_used values
        update_last_used(style="fd", format="png")

        # Verify defaults unchanged
        prefs = load_user_preferences()
        assert prefs["default_style"] == "bnr"
        assert prefs["default_format"] == "svg"
        assert prefs["last_used_style"] == "fd"
        assert prefs["last_used_format"] == "png"

    def test_update_last_used_multiple_times(self, temp_config_dir):
        """Test that update_last_used can be called multiple times."""
        update_last_used(style="fd", format="png")
        update_last_used(style="bnr")
        update_last_used(format="svg")

        prefs = load_user_preferences()
        assert prefs["last_used_style"] == "bnr"
        assert prefs["last_used_format"] == "svg"


class TestPriorityLogic:
    """Test priority logic for resolving style and format."""

    def test_priority_with_only_default(self, temp_config_dir):
        """Test that default is used when only default is set."""
        save_user_preferences(default_style="fd", default_format="png")

        prefs = load_user_preferences()

        # Simulate priority logic
        style = prefs.get("default_style") or prefs.get("last_used_style") or "fd"
        format = prefs.get("default_format") or prefs.get("last_used_format") or "png"

        assert style == "fd"
        assert format == "png"

    def test_priority_with_only_last_used(self, temp_config_dir):
        """Test that last_used is used when only last_used is set."""
        update_last_used(style="bnr", format="svg")

        prefs = load_user_preferences()

        # Simulate priority logic
        style = prefs.get("default_style") or prefs.get("last_used_style") or "fd"
        format = prefs.get("default_format") or prefs.get("last_used_format") or "png"

        assert style == "bnr"
        assert format == "svg"

    def test_priority_default_overrides_last_used(self, temp_config_dir):
        """Test that default takes priority over last_used."""
        save_user_preferences(default_style="fd", default_format="png")
        update_last_used(style="bnr", format="svg")

        prefs = load_user_preferences()

        # Simulate priority logic (default should win)
        style = prefs.get("default_style") or prefs.get("last_used_style") or "fd"
        format = prefs.get("default_format") or prefs.get("last_used_format") or "png"

        assert style == "fd"
        assert format == "png"

    def test_priority_fallback_to_defaults(self, temp_config_dir):
        """Test fallback to hardcoded defaults when nothing is set."""
        prefs = load_user_preferences()

        # Simulate priority logic with fallback
        style = prefs.get("default_style") or prefs.get("last_used_style") or "fd"
        format = prefs.get("default_format") or prefs.get("last_used_format") or "png"

        assert style == "fd"
        assert format == "png"


class TestGetConfigFilePath:
    """Test helper function for getting config file path."""

    def test_get_config_file_path_returns_path(self):
        """Test that get_config_file_path returns a Path object."""
        path = get_config_file_path()
        assert isinstance(path, Path)
        assert path.name == "settings.json"
