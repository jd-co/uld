"""Pydantic models for ULD."""

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field, field_validator


class EngineType(str, Enum):
    """Supported download engine types."""

    TORRENT = "torrent"
    VIDEO = "video"
    HTTP = "http"


class DownloadRequest(BaseModel):
    """Request model for initiating a download."""

    url: str = Field(..., description="URL, magnet link, or file path to download")
    output_dir: Path = Field(
        default_factory=lambda: Path.home() / "Downloads",
        description="Output directory for downloaded files",
    )
    filename: str | None = Field(
        default=None,
        description="Custom filename (auto-detected if not provided)",
    )

    # Torrent-specific options
    seed_ratio: float = Field(
        default=1.0,
        ge=0.0,
        description="Seed ratio target (0 = no seeding)",
    )
    seed_time: int = Field(
        default=0,
        ge=0,
        description="Seed time in minutes (0 = use ratio only)",
    )

    # Video-specific options
    quality: str | None = Field(
        default=None,
        description="Preferred quality (e.g., '1080p', 'best', 'worst')",
    )
    playlist: bool = Field(
        default=False,
        description="Download entire playlist (video only)",
    )

    model_config = {"extra": "forbid"}

    @field_validator("output_dir", mode="before")
    @classmethod
    def expand_path(cls, v: str | Path) -> Path:
        """Expand ~ and make path absolute."""
        path = Path(v).expanduser()
        return path.resolve()


class DownloadProgress(BaseModel):
    """Progress information during download."""

    downloaded: int = Field(..., ge=0, description="Bytes downloaded")
    total: int = Field(..., ge=0, description="Total bytes (0 if unknown)")
    speed: float = Field(default=0.0, ge=0, description="Download speed in bytes/sec")
    eta: int | None = Field(default=None, description="Estimated time remaining (sec)")
    percentage: float = Field(default=0.0, ge=0, le=100, description="Progress percent")

    # Torrent-specific
    upload_speed: float = Field(default=0.0, ge=0, description="Upload speed bytes/sec")
    uploaded: int = Field(default=0, ge=0, description="Bytes uploaded")
    peers: int = Field(default=0, ge=0, description="Connected peers")
    seeds: int = Field(default=0, ge=0, description="Connected seeds")

    # State
    state: str = Field(default="downloading", description="Current state")

    # Playlist-specific (video)
    playlist_index: int | None = Field(default=None, description="Current video index")
    playlist_count: int | None = Field(
        default=None, description="Total videos in playlist"
    )
    video_title: str | None = Field(default=None, description="Current video title")

    model_config = {"extra": "allow"}

    @property
    def speed_human(self) -> str:
        """Return human-readable download speed."""
        return _format_size(self.speed) + "/s"

    @property
    def uploaded_human(self) -> str:
        """Return human-readable uploaded size."""
        return _format_size(self.uploaded)

    @property
    def downloaded_human(self) -> str:
        """Return human-readable downloaded size."""
        return _format_size(self.downloaded)

    @property
    def total_human(self) -> str:
        """Return human-readable total size."""
        return _format_size(self.total) if self.total > 0 else "Unknown"


class DownloadResult(BaseModel):
    """Result of a completed download."""

    success: bool = Field(..., description="Whether download succeeded")
    file_path: Path | None = Field(
        default=None, description="Path to downloaded file(s)"
    )
    error: str | None = Field(default=None, description="Error message if failed")
    total_downloaded: int = Field(default=0, ge=0, description="Total bytes downloaded")
    total_uploaded: int = Field(default=0, ge=0, description="Total bytes uploaded")
    duration: float = Field(default=0.0, ge=0, description="Download duration in sec")
    avg_speed: float = Field(default=0.0, ge=0, description="Average download speed")

    model_config = {"extra": "allow"}


class TorrentFile(BaseModel):
    """Information about a single file in a torrent."""

    path: str = Field(..., description="Relative path within torrent")
    size: int = Field(..., ge=0, description="File size in bytes")
    priority: int = Field(default=4, ge=0, le=7, description="Download priority")

    @property
    def size_human(self) -> str:
        """Return human-readable file size."""
        return _format_size(self.size)


class TorrentInfo(BaseModel):
    """Metadata information for a torrent."""

    name: str = Field(..., description="Torrent name")
    info_hash: str = Field(..., description="Torrent info hash")
    total_size: int = Field(..., ge=0, description="Total size in bytes")
    files: list[TorrentFile] = Field(
        default_factory=list, description="Files in torrent"
    )
    piece_length: int = Field(default=0, ge=0, description="Piece size in bytes")
    num_pieces: int = Field(default=0, ge=0, description="Number of pieces")
    comment: str | None = Field(default=None, description="Torrent comment")
    creator: str | None = Field(default=None, description="Torrent creator")
    trackers: list[str] = Field(default_factory=list, description="Tracker URLs")

    model_config = {"extra": "allow"}

    @property
    def total_size_human(self) -> str:
        """Return human-readable total size."""
        return _format_size(self.total_size)

    @property
    def num_files(self) -> int:
        """Return number of files in torrent."""
        return len(self.files)


class VideoInfo(BaseModel):
    """Metadata information for a video."""

    title: str = Field(..., description="Video title")
    duration: int = Field(default=0, ge=0, description="Duration in seconds")
    uploader: str | None = Field(default=None, description="Video uploader/channel")
    view_count: int | None = Field(default=None, description="View count")
    upload_date: str | None = Field(default=None, description="Upload date (YYYYMMDD)")
    description: str | None = Field(default=None, description="Video description")
    thumbnail: str | None = Field(default=None, description="Thumbnail URL")
    formats: list[str] = Field(default_factory=list, description="Available qualities")
    webpage_url: str = Field(..., description="Original video URL")

    model_config = {"extra": "allow"}

    @property
    def duration_human(self) -> str:
        """Return human-readable duration."""
        if self.duration == 0:
            return "Unknown"
        hours, remainder = divmod(self.duration, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"


class EngineStatus(BaseModel):
    """Status information for a download engine."""

    name: str = Field(..., description="Engine name")
    engine_type: EngineType = Field(..., description="Engine type")
    available: bool = Field(..., description="Whether engine is available")
    version: str | None = Field(default=None, description="Engine version")
    install_hint: str | None = Field(
        default=None, description="How to install if unavailable"
    )

    model_config = {"extra": "forbid"}


def _format_size(size_bytes: int | float) -> str:
    """Format bytes to human-readable string."""
    if size_bytes == 0:
        return "0 B"

    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    size = float(size_bytes)

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    return f"{size:.2f} {units[unit_index]}"
