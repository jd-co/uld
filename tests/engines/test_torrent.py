"""Tests for torrent engine."""

import pytest

# Skip all tests if libtorrent is not available
pytest.importorskip("libtorrent", reason="libtorrent not installed")

from uld.engines.torrent import TorrentEngine


class TestTorrentEngine:
    """Tests for TorrentEngine."""

    def test_is_available(self) -> None:
        """Test that engine reports availability correctly."""
        # If we got here, libtorrent is installed
        assert TorrentEngine.is_available() is True

    def test_get_version(self) -> None:
        """Test version retrieval."""
        version = TorrentEngine.get_version()
        assert version is not None
        assert isinstance(version, str)

    def test_validate_magnet(self) -> None:
        """Test validation of magnet links."""
        engine = TorrentEngine()
        assert engine.validate("magnet:?xt=urn:btih:abc123") is True
        assert engine.validate("MAGNET:?xt=urn:btih:abc123") is True

    def test_validate_torrent_file(self) -> None:
        """Test validation of torrent files."""
        engine = TorrentEngine()
        assert engine.validate("file.torrent") is True
        assert engine.validate("/path/to/file.torrent") is True
        assert engine.validate("https://example.com/file.torrent") is True

    def test_validate_invalid(self) -> None:
        """Test validation rejects invalid input."""
        engine = TorrentEngine()
        assert engine.validate("https://youtube.com/watch?v=abc") is False
        assert engine.validate("not a torrent") is False

    def test_get_name(self) -> None:
        """Test engine name."""
        assert TorrentEngine.get_name() == "Torrent"


class TestTorrentEngineSession:
    """Tests for TorrentEngine session management."""

    def test_session_creation(self) -> None:
        """Test session is created on demand."""
        engine = TorrentEngine()
        assert engine._session is None
        session = engine._get_session()
        assert session is not None
        assert engine._session is session

    def test_close(self) -> None:
        """Test closing the engine."""
        engine = TorrentEngine()
        engine._get_session()  # Create session
        engine.close()
        assert engine._session is None
