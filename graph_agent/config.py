"""User preferences and configuration management."""

import json
import logging
from pathlib import Path
from typing import Optional

# Configure logging
logger = logging.getLogger(__name__)

# Configuration paths
CONFIG_DIR = Path.home() / ".config" / "graph-agent"
CONFIG_FILE = CONFIG_DIR / "settings.json"

# Default settings structure
DEFAULT_SETTINGS = {
    "default_style": None,
    "default_format": None,
    "last_used_style": None,
    "last_used_format": None
}


def ensure_config_exists() -> None:
    """
    Create config directory and file if they don't exist.

    Creates ~/.config/graph-agent/settings.json with default values.
    """
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Config directory ensured at: {CONFIG_DIR}")

        if not CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'w') as f:
                json.dump(DEFAULT_SETTINGS, f, indent=2)
            logger.info(f"Created new config file at: {CONFIG_FILE}")
    except Exception as e:
        logger.error(f"Failed to ensure config exists: {e}")
        raise


def load_user_preferences() -> dict:
    """
    Load user preferences from config file.

    Returns:
        Dictionary with user preferences:
        {
            "default_style": "fd" or "bnr" or None,
            "default_format": "png" or "svg" or None,
            "last_used_style": "fd" or "bnr" or None,
            "last_used_format": "png" or "svg" or None
        }

    Example:
        >>> prefs = load_user_preferences()
        >>> print(prefs["default_style"])
        'fd'
    """
    ensure_config_exists()

    try:
        with open(CONFIG_FILE, 'r') as f:
            settings = json.load(f)
        logger.debug(f"Loaded preferences: {settings}")
        return settings
    except Exception as e:
        logger.error(f"Failed to load preferences: {e}")
        # Return defaults on error
        return DEFAULT_SETTINGS.copy()


def save_user_preferences(default_style: Optional[str] = None,
                         default_format: Optional[str] = None) -> None:
    """
    Update default_* fields in config file.

    Args:
        default_style: Default brand style ('fd' or 'bnr'), or None to leave unchanged
        default_format: Default output format ('png' or 'svg'), or None to leave unchanged

    Example:
        >>> save_user_preferences(default_style="fd")
        >>> save_user_preferences(default_format="svg")
        >>> save_user_preferences(default_style="bnr", default_format="png")
    """
    ensure_config_exists()

    try:
        settings = load_user_preferences()

        if default_style is not None:
            settings["default_style"] = default_style
            logger.info(f"Set default_style to: {default_style}")

        if default_format is not None:
            settings["default_format"] = default_format
            logger.info(f"Set default_format to: {default_format}")

        with open(CONFIG_FILE, 'w') as f:
            json.dump(settings, f, indent=2)

        logger.debug(f"Saved preferences: {settings}")
    except Exception as e:
        logger.error(f"Failed to save preferences: {e}")
        raise


def update_last_used(style: Optional[str] = None,
                    format: Optional[str] = None) -> None:
    """
    Update last_used_* fields in config file.

    This is called after successful chart generation to track
    the most recently used style and format.

    Args:
        style: Last used brand style ('fd' or 'bnr'), or None to leave unchanged
        format: Last used output format ('png' or 'svg'), or None to leave unchanged

    Example:
        >>> update_last_used(style="bnr", format="png")
    """
    ensure_config_exists()

    try:
        settings = load_user_preferences()

        if style is not None:
            settings["last_used_style"] = style
            logger.debug(f"Updated last_used_style to: {style}")

        if format is not None:
            settings["last_used_format"] = format
            logger.debug(f"Updated last_used_format to: {format}")

        with open(CONFIG_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to update last used: {e}")
        # Don't raise - this is not critical


def get_config_file_path() -> Path:
    """
    Get the path to the config file.

    Useful for testing and debugging.

    Returns:
        Path object pointing to settings.json
    """
    return CONFIG_FILE
