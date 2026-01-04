"""Configuration management for ULD."""

from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ULDConfig(BaseSettings):
    """Global configuration for ULD.

    Settings can be configured via:
    1. Environment variables (prefixed with ULD_)
    2. Config file (~/.config/uld/config.toml)
    3. Command line arguments (highest priority)
    """

    model_config = SettingsConfigDict(
        env_prefix="ULD_",
        env_file=".env",
        extra="ignore",
    )

    # General settings
    download_dir: Path = Field(
        default_factory=lambda: Path.home() / "Downloads",
        description="Default download directory",
    )
    verbose: bool = Field(
        default=False,
        description="Enable verbose output",
    )
    quiet: bool = Field(
        default=False,
        description="Minimal output (errors only)",
    )

    # Torrent settings
    seed_ratio: float = Field(
        default=1.0,
        ge=0.0,
        description="Default seed ratio (0 = no seeding)",
    )
    seed_time: int = Field(
        default=0,
        ge=0,
        description="Seed time in minutes (0 = use ratio only)",
    )
    max_connections: int = Field(
        default=200,
        ge=1,
        le=1000,
        description="Maximum peer connections",
    )
    max_upload_slots: int = Field(
        default=8,
        ge=1,
        le=100,
        description="Maximum upload slots",
    )
    download_rate_limit: int = Field(
        default=0,
        ge=0,
        description="Download rate limit in KB/s (0 = unlimited)",
    )
    upload_rate_limit: int = Field(
        default=0,
        ge=0,
        description="Upload rate limit in KB/s (0 = unlimited)",
    )
    listen_port_start: int = Field(
        default=6881,
        ge=1024,
        le=65535,
        description="Start of port range for incoming connections",
    )
    listen_port_end: int = Field(
        default=6891,
        ge=1024,
        le=65535,
        description="End of port range for incoming connections",
    )
    enable_dht: bool = Field(
        default=True,
        description="Enable DHT for peer discovery",
    )
    enable_lsd: bool = Field(
        default=True,
        description="Enable Local Service Discovery",
    )
    enable_upnp: bool = Field(
        default=True,
        description="Enable UPnP for port forwarding",
    )
    enable_natpmp: bool = Field(
        default=True,
        description="Enable NAT-PMP for port forwarding",
    )

    # Video settings (for future use)
    video_quality: str = Field(
        default="best",
        description="Preferred video quality",
    )
    video_format: str = Field(
        default="mp4",
        description="Preferred video format",
    )

    # HTTP settings (for future use)
    http_timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="HTTP request timeout in seconds",
    )
    http_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Number of retry attempts for failed requests",
    )

    @field_validator("download_dir", mode="before")
    @classmethod
    def expand_download_dir(cls, v: str | Path) -> Path:
        """Expand ~ and make path absolute."""
        path = Path(v).expanduser()
        return path.resolve()

    @field_validator("listen_port_end")
    @classmethod
    def validate_port_range(cls, v: int, info: Any) -> int:
        """Ensure port_end >= port_start."""
        port_start = info.data.get("listen_port_start", 6881)
        if v < port_start:
            raise ValueError(
                f"listen_port_end ({v}) must be >= listen_port_start ({port_start})"
            )
        return v


# Global config instance (lazy-loaded)
_config: ULDConfig | None = None


def get_config() -> ULDConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = ULDConfig()
    return _config


def reset_config() -> None:
    """Reset config to defaults (mainly for testing)."""
    global _config
    _config = None
