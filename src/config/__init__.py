"""Configuration management for vscode-time.

This module provides a centralized configuration layer using TOML.
Configuration is stored locally at ~/.config/vscode-time/config.toml.
"""

import os
import tomllib
from pathlib import Path
from typing import Any, Optional

from goals import validate_goal, parse_goal_input, InvalidGoalError, DEFAULT_DAILY_GOAL_SECONDS


# Configuration file location
CONFIG_DIR = Path.home() / ".config" / "vscode-time"
CONFIG_FILE = CONFIG_DIR / "config.toml"

# Supported configuration keys
SUPPORTED_KEYS = {"daily_goal_seconds"}

# Default configuration values
DEFAULTS = {
    "daily_goal_seconds": DEFAULT_DAILY_GOAL_SECONDS,
}


class ConfigError(Exception):
    """Error in configuration."""
    pass


class ConfigValidationError(ConfigError):
    """Configuration validation error."""
    pass


class Config:
    """Configuration manager for vscode-time."""

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize configuration.

        Args:
            config_path: Optional path to configuration file.
                        Defaults to ~/.config/vscode-time/config.toml
        """
        self.config_path = config_path or CONFIG_FILE
        self._data: dict = {}

    def load(self) -> dict:
        """Load configuration from file.

        Returns:
            Configuration dictionary.

        Raises:
            ConfigError: If configuration file is malformed.
        """
        if not self.config_path.exists():
            self._data = dict(DEFAULTS)
            return self._data

        try:
            with open(self.config_path, "rb") as f:
                self._data = tomllib.load(f)
        except tomllib.TOMLDecodeError as e:
            raise ConfigError(f"Malformed configuration file: {e}")

        # Apply defaults for missing keys
        for key, default in DEFAULTS.items():
            if key not in self._data:
                self._data[key] = default

        return self._data

    def save(self) -> None:
        """Save configuration to file.

        Creates parent directory if needed.
        Preserves unrelated settings.
        """
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        # Write TOML manually for simplicity
        lines = []
        lines.append("# vscode-time configuration")
        lines.append("")

        for key in sorted(self._data.keys()):
            value = self._data[key]
            if isinstance(value, int):
                lines.append(f"{key} = {value}")
            elif isinstance(value, float):
                lines.append(f"{key} = {value}")
            elif isinstance(value, str):
                lines.append(f'{key} = "{value}"')
            elif isinstance(value, bool):
                lines.append(f"{key} = {'true' if value else 'false'}")

        # Write atomically
        tmp_path = self.config_path.with_suffix(".tmp")
        try:
            tmp_path.write_text("\n".join(lines) + "\n")
            tmp_path.replace(self.config_path)
        except Exception:
            if tmp_path.exists():
                tmp_path.unlink()
            raise

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value.

        Args:
            key: Configuration key.
            default: Default value if key not set.

        Returns:
            Configuration value.
        """
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value.

        Args:
            key: Configuration key.
            value: Value to set.

        Raises:
            ConfigValidationError: If key or value is invalid.
        """
        if key not in SUPPORTED_KEYS:
            raise ConfigValidationError(f"Unsupported configuration key: {key}")

        # Validate the value
        if key == "daily_goal_seconds":
            if not isinstance(value, int):
                raise ConfigValidationError(f"daily_goal_seconds must be an integer, got {type(value).__name__}")
            validate_goal(value)

        self._data[key] = value

    def set_from_input(self, key: str, input_str: str) -> Any:
        """Set a configuration value from human-readable input.

        Args:
            key: Configuration key.
            input_str: Human-readable input string.

        Returns:
            The parsed value that was set.

        Raises:
            ConfigValidationError: If key or input is invalid.
        """
        if key not in SUPPORTED_KEYS:
            raise ConfigValidationError(f"Unsupported configuration key: {key}")

        if key == "daily_goal_seconds":
            value = parse_goal_input(input_str)
            validate_goal(value)
            self._data[key] = value
            return value

        raise ConfigValidationError(f"No parser for key: {key}")


def load_config(config_path: Optional[Path] = None) -> Config:
    """Load configuration from file.

    Args:
        config_path: Optional path to configuration file.

    Returns:
        Config object with loaded data.
    """
    config = Config(config_path)
    config.load()
    return config


def get_config_value(key: str, config_path: Optional[Path] = None) -> Any:
    """Get a single configuration value.

    Args:
        key: Configuration key.
        config_path: Optional path to configuration file.

    Returns:
        Configuration value, or default if not set.
    """
    config = load_config(config_path)
    return config.get(key, DEFAULTS.get(key))


def set_config_value(key: str, value: Any, config_path: Optional[Path] = None) -> None:
    """Set a single configuration value and save.

    Args:
        key: Configuration key.
        value: Value to set.
        config_path: Optional path to configuration file.
    """
    config = load_config(config_path)
    config.set(key, value)
    config.save()


def migrate_goal_from_db(db_goal: Optional[int], config_path: Optional[Path] = None) -> int:
    """Migrate daily goal from database to config file.

    If the config file doesn't have a goal set, use the database value.
    If both exist, config file takes precedence.

    Args:
        db_goal: Goal from database (seconds), or None if not set.
        config_path: Optional path to configuration file.

    Returns:
        The effective daily goal in seconds.
    """
    config = load_config(config_path)

    # If config has a non-default value, use it
    if config.get("daily_goal_seconds") != DEFAULT_DAILY_GOAL_SECONDS:
        return config.get("daily_goal_seconds")

    # If database has a goal, migrate it to config
    if db_goal is not None and db_goal != DEFAULT_DAILY_GOAL_SECONDS:
        config.set("daily_goal_seconds", db_goal)
        config.save()
        return db_goal

    # Use default
    return config.get("daily_goal_seconds")
