"""Configuration management module."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ACRCloudConfig:
    """ACRCloud API configuration."""

    access_key: str
    access_secret: str
    host: str = "identify-ap-southeast-1.acrcloud.com"


@dataclass
class AudioConfig:
    """Audio input configuration."""

    input_device: str | None = None
    sample_rate: int = 44100
    volume_threshold_db: float = -40.0
    silence_threshold_db: float = -50.0
    silence_duration_sec: float = 5.0
    recognition_duration_sec: float = 10.0


@dataclass
class LaMetricConfig:
    """LaMetric device configuration."""

    ip: str | None = None
    api_key: str = ""
    icon: str = "i9218"
    lifetime: int | None = None  # Display duration in milliseconds
    cycles: int = 1  # 0 = keep until dismissed, 1+ = number of cycles


@dataclass
class RecognitionConfig:
    """Recognition behavior configuration."""

    cooldown_sec: int = 120
    max_failed_attempts: int = 3
    pause_duration_sec: int = 900


@dataclass
class LoggingConfig:
    """Logging configuration."""

    log_file_path: str = "./recognition_log.json"


@dataclass
class Config:
    """Main configuration."""

    acrcloud: ACRCloudConfig
    audio: AudioConfig
    lametric: LaMetricConfig
    recognition: RecognitionConfig
    logging: LoggingConfig


def _get_env(key: str, default: Any = None) -> Any:
    """Get environment variable value."""
    value = os.getenv(key)
    if value is None:
        return default
    # Try to convert to appropriate type
    if isinstance(default, bool):
        return value.lower() in ("true", "1", "yes")
    if isinstance(default, int):
        return int(value)
    if isinstance(default, float):
        return float(value)
    return value


def load_config(config_path: str | Path | None = None) -> Config:
    """
    Load configuration from YAML file and environment variables.

    Priority: Environment variables > YAML file > Default values

    Args:
        config_path: Path to YAML config file. If None, looks for config.yaml
                    in current directory.

    Returns:
        Config object

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If required configuration is missing
    """
    # Load from YAML if exists
    yaml_config = {}
    if config_path is None:
        config_path = Path("config.yaml")
    else:
        config_path = Path(config_path)

    if config_path.exists():
        with open(config_path) as f:
            yaml_config = yaml.safe_load(f) or {}

    # ACRCloud config (required)
    acrcloud_config = yaml_config.get("acrcloud", {})
    access_key = _get_env("ACRCLOUD_ACCESS_KEY", acrcloud_config.get("access_key"))
    access_secret = _get_env(
        "ACRCLOUD_ACCESS_SECRET", acrcloud_config.get("access_secret")
    )
    host = _get_env("ACRCLOUD_HOST", acrcloud_config.get("host", "identify-ap-southeast-1.acrcloud.com"))

    if not access_key or not access_secret:
        raise ValueError(
            "ACRCloud credentials are required. Set ACRCLOUD_ACCESS_KEY and "
            "ACRCLOUD_ACCESS_SECRET environment variables or add them to config.yaml"
        )

    acrcloud = ACRCloudConfig(
        access_key=access_key, access_secret=access_secret, host=host
    )

    # Audio config
    audio_config = yaml_config.get("audio", {})
    audio = AudioConfig(
        input_device=_get_env("AUDIO_INPUT_DEVICE", audio_config.get("input_device")),
        sample_rate=_get_env("AUDIO_SAMPLE_RATE", audio_config.get("sample_rate", 44100)),
        volume_threshold_db=_get_env(
            "VOLUME_THRESHOLD_DB", audio_config.get("volume_threshold_db", -40.0)
        ),
        silence_threshold_db=_get_env(
            "SILENCE_THRESHOLD_DB", audio_config.get("silence_threshold_db", -50.0)
        ),
        silence_duration_sec=_get_env(
            "SILENCE_DURATION_SEC", audio_config.get("silence_duration_sec", 5.0)
        ),
        recognition_duration_sec=_get_env(
            "RECOGNITION_DURATION_SEC",
            audio_config.get("recognition_duration_sec", 10.0),
        ),
    )

    # LaMetric config
    lametric_config = yaml_config.get("lametric", {})
    lametric_api_key = _get_env("LAMETRIC_API_KEY", lametric_config.get("api_key", ""))

    lametric = LaMetricConfig(
        ip=_get_env("LAMETRIC_IP", lametric_config.get("ip")),
        api_key=lametric_api_key,
        icon=_get_env("LAMETRIC_ICON", lametric_config.get("icon", "i9218")),
        lifetime=_get_env("LAMETRIC_LIFETIME", lametric_config.get("lifetime")),
        cycles=_get_env("LAMETRIC_CYCLES", lametric_config.get("cycles", 1)),
    )

    # Recognition config
    recognition_config = yaml_config.get("recognition", {})
    recognition = RecognitionConfig(
        cooldown_sec=_get_env(
            "COOLDOWN_SEC", recognition_config.get("cooldown_sec", 120)
        ),
        max_failed_attempts=_get_env(
            "MAX_FAILED_ATTEMPTS", recognition_config.get("max_failed_attempts", 3)
        ),
        pause_duration_sec=_get_env(
            "PAUSE_DURATION_SEC", recognition_config.get("pause_duration_sec", 900)
        ),
    )

    # Logging config
    logging_config = yaml_config.get("logging", {})
    logging = LoggingConfig(
        log_file_path=_get_env(
            "LOG_FILE_PATH", logging_config.get("log_file_path", "./recognition_log.json")
        )
    )

    return Config(
        acrcloud=acrcloud,
        audio=audio,
        lametric=lametric,
        recognition=recognition,
        logging=logging,
    )
