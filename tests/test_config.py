"""Tests for configuration."""

from pathlib import Path

import pytest

from uld.config import ULDConfig, get_config, reset_config


class TestULDConfig:
    """Tests for ULDConfig."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = ULDConfig()
        assert config.download_dir == Path.home() / "Downloads"
        assert config.seed_ratio == 1.0
        assert config.max_connections == 200
        assert config.enable_dht is True

    def test_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test environment variable override."""
        monkeypatch.setenv("ULD_SEED_RATIO", "2.5")
        monkeypatch.setenv("ULD_MAX_CONNECTIONS", "100")

        config = ULDConfig()
        assert config.seed_ratio == 2.5
        assert config.max_connections == 100

    def test_download_dir_expansion(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test tilde expansion in download_dir."""
        monkeypatch.setenv("ULD_DOWNLOAD_DIR", "~/my_downloads")

        config = ULDConfig()
        assert str(config.download_dir).startswith(str(Path.home()))
        assert "my_downloads" in str(config.download_dir)

    def test_port_range_validation(self) -> None:
        """Test port range validation."""
        # Valid range
        config = ULDConfig(listen_port_start=6000, listen_port_end=6100)
        assert config.listen_port_start == 6000
        assert config.listen_port_end == 6100

    def test_invalid_port_range(self) -> None:
        """Test invalid port range raises error."""
        with pytest.raises(ValueError):
            ULDConfig(listen_port_start=7000, listen_port_end=6000)

    def test_rate_limit(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test rate limit configuration."""
        monkeypatch.setenv("ULD_DOWNLOAD_RATE_LIMIT", "1000")
        monkeypatch.setenv("ULD_UPLOAD_RATE_LIMIT", "500")

        config = ULDConfig()
        assert config.download_rate_limit == 1000
        assert config.upload_rate_limit == 500


class TestGetConfig:
    """Tests for get_config function."""

    def test_singleton(self) -> None:
        """Test that get_config returns same instance."""
        reset_config()
        config1 = get_config()
        config2 = get_config()
        assert config1 is config2

    def test_reset_config(self) -> None:
        """Test reset_config creates new instance."""
        config1 = get_config()
        reset_config()
        config2 = get_config()
        # Different instances (though equal values)
        assert config1 is not config2
