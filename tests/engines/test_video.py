"""Tests for video engine."""

import pytest

# Skip all tests if yt-dlp is not available
pytest.importorskip("yt_dlp", reason="yt-dlp not installed")

from uld.engines.video import VideoEngine


class TestVideoEngine:
    """Tests for VideoEngine."""

    def test_is_available(self) -> None:
        """Test that engine reports availability correctly."""
        # If we got here, yt-dlp is installed
        assert VideoEngine.is_available() is True

    def test_get_version(self) -> None:
        """Test version retrieval."""
        version = VideoEngine.get_version()
        assert version is not None
        assert isinstance(version, str)

    def test_validate_youtube(self) -> None:
        """Test validation of YouTube URLs."""
        engine = VideoEngine()
        assert engine.validate("https://youtube.com/watch?v=abc123") is True
        assert engine.validate("https://www.youtube.com/watch?v=abc123") is True
        assert engine.validate("https://youtu.be/abc123") is True

    def test_validate_vimeo(self) -> None:
        """Test validation of Vimeo URLs."""
        engine = VideoEngine()
        assert engine.validate("https://vimeo.com/123456") is True

    def test_validate_other_platforms(self) -> None:
        """Test validation of other video platforms."""
        engine = VideoEngine()
        assert engine.validate("https://twitter.com/user/status/123") is True
        assert engine.validate("https://x.com/user/status/123") is True
        assert engine.validate("https://reddit.com/r/sub/comments/abc") is True

    def test_validate_invalid(self) -> None:
        """Test validation rejects invalid input."""
        engine = VideoEngine()
        assert engine.validate("magnet:?xt=urn:btih:abc") is False
        assert engine.validate("file.torrent") is False
        assert engine.validate("https://example.com/file.txt") is False

    def test_get_name(self) -> None:
        """Test engine name."""
        assert VideoEngine.get_name() == "Video"

    def test_quality_formats(self) -> None:
        """Test quality format mappings exist."""
        assert "best" in VideoEngine.QUALITY_FORMATS
        assert "worst" in VideoEngine.QUALITY_FORMATS
        assert "1080p" in VideoEngine.QUALITY_FORMATS
        assert "720p" in VideoEngine.QUALITY_FORMATS

    def test_close(self) -> None:
        """Test closing the engine (no-op for yt-dlp)."""
        engine = VideoEngine()
        # Should not raise
        engine.close()

    def test_playlist_detection(self) -> None:
        """Test auto-detection of playlist URLs."""
        engine = VideoEngine()
        # YouTube playlists
        assert (
            engine._is_playlist_url("https://youtube.com/playlist?list=PLxxx") is True
        )
        assert (
            engine._is_playlist_url("https://www.youtube.com/watch?v=abc&list=PLxxx")
            is True
        )
        # Regular videos
        assert engine._is_playlist_url("https://youtube.com/watch?v=abc") is False
        assert engine._is_playlist_url("https://vimeo.com/123456") is False


class TestVideoEngineContext:
    """Tests for VideoEngine context manager."""

    def test_context_manager(self) -> None:
        """Test engine works as context manager."""
        with VideoEngine() as engine:
            assert engine.is_available() is True
        # Should not raise on exit
