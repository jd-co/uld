"""Tests for input detection."""

import pytest

from uld.detector import InputDetector, detect
from uld.exceptions import DetectionError
from uld.models import EngineType


class TestInputDetector:
    """Tests for InputDetector class."""

    def test_detect_magnet_hex(self, sample_magnet: str) -> None:
        """Test detection of magnet link with hex hash."""
        detector = InputDetector()
        result = detector.detect(sample_magnet)
        assert result == EngineType.TORRENT

    def test_detect_magnet_base32(self, sample_magnet_base32: str) -> None:
        """Test detection of magnet link with base32 hash."""
        detector = InputDetector()
        result = detector.detect(sample_magnet_base32)
        assert result == EngineType.TORRENT

    def test_detect_torrent_url(self) -> None:
        """Test detection of remote torrent file."""
        detector = InputDetector()
        result = detector.detect("https://example.com/file.torrent")
        assert result == EngineType.TORRENT

    def test_detect_youtube(self, sample_youtube_url: str) -> None:
        """Test detection of YouTube URL."""
        detector = InputDetector()
        result = detector.detect(sample_youtube_url)
        assert result == EngineType.VIDEO

    def test_detect_youtube_short(self) -> None:
        """Test detection of YouTube short URL."""
        detector = InputDetector()
        result = detector.detect("https://youtu.be/dQw4w9WgXcQ")
        assert result == EngineType.VIDEO

    def test_detect_vimeo(self) -> None:
        """Test detection of Vimeo URL."""
        detector = InputDetector()
        result = detector.detect("https://vimeo.com/123456789")
        assert result == EngineType.VIDEO

    def test_detect_direct_url_zip(self, sample_direct_url: str) -> None:
        """Test detection of direct download URL."""
        detector = InputDetector()
        result = detector.detect(sample_direct_url)
        assert result == EngineType.HTTP

    def test_detect_direct_url_iso(self) -> None:
        """Test detection of ISO download URL."""
        detector = InputDetector()
        result = detector.detect("https://example.com/ubuntu.iso")
        assert result == EngineType.HTTP

    def test_detect_generic_http(self) -> None:
        """Test detection of generic HTTP URL goes to VIDEO (yt-dlp supports 1400+ sites)."""
        detector = InputDetector()
        result = detector.detect("https://example.com/some/path")
        # Generic URLs without file extensions go to VIDEO engine (yt-dlp fallback)
        assert result == EngineType.VIDEO

    def test_detect_empty_raises_error(self) -> None:
        """Test that empty input raises DetectionError."""
        detector = InputDetector()
        with pytest.raises(DetectionError):
            detector.detect("")

    def test_detect_whitespace_raises_error(self) -> None:
        """Test that whitespace-only input raises DetectionError."""
        detector = InputDetector()
        with pytest.raises(DetectionError):
            detector.detect("   ")

    def test_is_magnet_valid(self) -> None:
        """Test _is_magnet with valid magnet link."""
        detector = InputDetector()
        assert detector._is_magnet(
            "magnet:?xt=urn:btih:dd8255ecdc7ca55fb0bbf81323d87062db1f6d1c"
        )

    def test_is_magnet_invalid(self) -> None:
        """Test _is_magnet with invalid input."""
        detector = InputDetector()
        assert not detector._is_magnet("not a magnet link")
        assert not detector._is_magnet("magnet:invalid")

    def test_get_info_magnet(self, sample_magnet: str) -> None:
        """Test get_info extracts magnet info."""
        detector = InputDetector()
        info = detector.get_info(sample_magnet)
        assert info["type"] == EngineType.TORRENT
        assert info["subtype"] == "magnet"
        assert "info_hash" in info

    def test_get_info_video(self, sample_youtube_url: str) -> None:
        """Test get_info extracts video platform info."""
        detector = InputDetector()
        info = detector.get_info(sample_youtube_url)
        assert info["type"] == EngineType.VIDEO
        assert "www.youtube.com" in info["platform"]


class TestDetectFunction:
    """Tests for the detect convenience function."""

    def test_detect_magnet(self, sample_magnet: str) -> None:
        """Test detect function with magnet link."""
        result = detect(sample_magnet)
        assert result == EngineType.TORRENT

    def test_detect_youtube(self, sample_youtube_url: str) -> None:
        """Test detect function with YouTube URL."""
        result = detect(sample_youtube_url)
        assert result == EngineType.VIDEO

    def test_detect_direct(self, sample_direct_url: str) -> None:
        """Test detect function with direct URL."""
        result = detect(sample_direct_url)
        assert result == EngineType.HTTP
