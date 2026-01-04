"""Tests for Pydantic models."""

from pathlib import Path

import pytest

from uld.models import (
    DownloadProgress,
    DownloadRequest,
    DownloadResult,
    EngineType,
    TorrentFile,
    TorrentInfo,
)


class TestEngineType:
    """Tests for EngineType enum."""

    def test_values(self) -> None:
        """Test enum values."""
        assert EngineType.TORRENT.value == "torrent"
        assert EngineType.VIDEO.value == "video"
        assert EngineType.HTTP.value == "http"

    def test_string_comparison(self) -> None:
        """Test string comparison works."""
        assert EngineType.TORRENT == "torrent"
        assert EngineType.VIDEO == "video"


class TestDownloadRequest:
    """Tests for DownloadRequest model."""

    def test_minimal_request(self) -> None:
        """Test creating request with minimal fields."""
        request = DownloadRequest(url="magnet:?xt=urn:btih:abc123")
        assert request.url == "magnet:?xt=urn:btih:abc123"
        assert request.output_dir == Path.home() / "Downloads"
        assert request.seed_ratio == 1.0

    def test_custom_output_dir(self, tmp_path: Path) -> None:
        """Test custom output directory."""
        request = DownloadRequest(url="magnet:?xt=urn:btih:abc", output_dir=tmp_path)
        assert request.output_dir == tmp_path

    def test_expand_tilde(self) -> None:
        """Test tilde expansion in output_dir."""
        request = DownloadRequest(
            url="magnet:?xt=urn:btih:abc", output_dir="~/Downloads"
        )
        assert str(request.output_dir).startswith(str(Path.home()))

    def test_seed_ratio_validation(self) -> None:
        """Test seed_ratio must be non-negative."""
        with pytest.raises(ValueError):
            DownloadRequest(url="magnet:?xt=urn:btih:abc", seed_ratio=-1.0)

    def test_no_seed(self) -> None:
        """Test seed_ratio=0 for no seeding."""
        request = DownloadRequest(url="magnet:?xt=urn:btih:abc", seed_ratio=0.0)
        assert request.seed_ratio == 0.0


class TestDownloadProgress:
    """Tests for DownloadProgress model."""

    def test_basic_progress(self) -> None:
        """Test basic progress creation."""
        progress = DownloadProgress(downloaded=1000, total=10000)
        assert progress.downloaded == 1000
        assert progress.total == 10000

    def test_percentage(self) -> None:
        """Test percentage calculation."""
        progress = DownloadProgress(downloaded=5000, total=10000, percentage=50.0)
        assert progress.percentage == 50.0

    def test_speed_human(self) -> None:
        """Test human-readable speed."""
        progress = DownloadProgress(downloaded=0, total=100, speed=1048576.0)  # 1 MB/s
        assert "1.00 MB/s" in progress.speed_human

    def test_torrent_specific_fields(self) -> None:
        """Test torrent-specific fields."""
        progress = DownloadProgress(
            downloaded=1000,
            total=10000,
            peers=10,
            seeds=5,
            upload_speed=500000.0,
        )
        assert progress.peers == 10
        assert progress.seeds == 5
        assert progress.upload_speed == 500000.0


class TestDownloadResult:
    """Tests for DownloadResult model."""

    def test_success_result(self, tmp_path: Path) -> None:
        """Test successful result."""
        result = DownloadResult(
            success=True,
            file_path=tmp_path / "test.iso",
            total_downloaded=1000000,
        )
        assert result.success is True
        assert result.file_path == tmp_path / "test.iso"

    def test_failure_result(self) -> None:
        """Test failed result."""
        result = DownloadResult(
            success=False,
            error="Connection timeout",
        )
        assert result.success is False
        assert result.error == "Connection timeout"


class TestTorrentFile:
    """Tests for TorrentFile model."""

    def test_basic_file(self) -> None:
        """Test basic file info."""
        file = TorrentFile(path="movie.mkv", size=1073741824)  # 1 GB
        assert file.path == "movie.mkv"
        assert file.size == 1073741824

    def test_size_human(self) -> None:
        """Test human-readable size."""
        file = TorrentFile(path="file.txt", size=1073741824)
        assert "1.00 GB" in file.size_human


class TestTorrentInfo:
    """Tests for TorrentInfo model."""

    def test_basic_info(self) -> None:
        """Test basic torrent info."""
        info = TorrentInfo(
            name="Ubuntu 24.04",
            info_hash="abc123def456",
            total_size=4294967296,  # 4 GB
        )
        assert info.name == "Ubuntu 24.04"
        assert info.info_hash == "abc123def456"

    def test_with_files(self) -> None:
        """Test torrent with files."""
        info = TorrentInfo(
            name="MultiFile",
            info_hash="abc123",
            total_size=2000,
            files=[
                TorrentFile(path="file1.txt", size=1000),
                TorrentFile(path="file2.txt", size=1000),
            ],
        )
        assert info.num_files == 2

    def test_total_size_human(self) -> None:
        """Test human-readable total size."""
        info = TorrentInfo(
            name="Test",
            info_hash="abc",
            total_size=1073741824,  # 1 GB
        )
        assert "1.00 GB" in info.total_size_human
