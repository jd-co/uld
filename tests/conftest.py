"""Pytest configuration and fixtures for ULD tests."""

import pytest

from uld.config import reset_config


@pytest.fixture(autouse=True)
def reset_config_fixture() -> None:
    """Reset config before each test."""
    reset_config()
    yield
    reset_config()


@pytest.fixture
def sample_magnet() -> str:
    """Sample magnet link for testing."""
    return (
        "magnet:?xt=urn:btih:dd8255ecdc7ca55fb0bbf81323d87062db1f6d1c&dn=Big+Buck+Bunny"
    )


@pytest.fixture
def sample_magnet_base32() -> str:
    """Sample magnet link with base32 hash."""
    return "magnet:?xt=urn:btih:3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ&dn=Example"


@pytest.fixture
def sample_youtube_url() -> str:
    """Sample YouTube URL for testing."""
    return "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


@pytest.fixture
def sample_direct_url() -> str:
    """Sample direct download URL for testing."""
    return "https://example.com/file.zip"
