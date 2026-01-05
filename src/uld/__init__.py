"""ULD - Unified Local Downloader.

A single CLI tool for downloading content from multiple sources:
torrents, magnet links, video platforms, and direct URLs.

Programmatic usage:
    >>> from uld import download, get_info
    >>> result = download("https://youtube.com/watch?v=...")
    >>> print(result.file_path)
"""

from __future__ import annotations

import asyncio
from importlib.metadata import metadata
from pathlib import Path
from typing import TYPE_CHECKING, Any

from uld.detector import InputDetector, detect
from uld.engines import get_available_engines, get_engine
from uld.engines.base import BaseEngine, ProgressCallback
from uld.exceptions import (
    DetectionError,
    DownloadError,
    EngineNotAvailableError,
    InvalidURLError,
    ULDError,
)
from uld.models import (
    DownloadProgress,
    DownloadRequest,
    DownloadResult,
    EngineStatus,
    EngineType,
    TorrentInfo,
    VideoInfo,
)

if TYPE_CHECKING:
    from collections.abc import Callable

_meta = metadata("uld-cli")
__version__ = _meta["Version"]
__author__ = _meta["Author"]


def download(
    url: str,
    output_dir: Path | str | None = None,
    *,
    quality: str = "best",
    progress_callback: Callable[[DownloadProgress], None] | None = None,
    seed_ratio: float = 1.0,
    seed_time: int = 0,
    playlist: bool = False,
    filename: str | None = None,
) -> DownloadResult:
    """Download from any supported URL.

    This is a sync wrapper around the async engine download methods.
    Auto-detects URL type and uses the appropriate engine.

    Args:
        url: URL, magnet link, or torrent file path to download.
        output_dir: Directory to save downloads. Defaults to ~/Downloads.
        quality: Video quality (best, 1080p, 720p, etc.). Default: "best".
        progress_callback: Optional callback for progress updates.
        seed_ratio: Torrent seed ratio (0 = no seeding). Default: 1.0.
        seed_time: Torrent seed time in minutes. Default: 0.
        playlist: Force download as playlist (for video URLs). Default: False.
        filename: Override output filename. Default: None (auto-detect).

    Returns:
        DownloadResult with success status, file path, and statistics.

    Raises:
        DetectionError: If URL type cannot be determined.
        DownloadError: If download fails.
        EngineNotAvailableError: If required engine is not installed.

    Example:
        >>> from uld import download
        >>> result = download("https://youtube.com/watch?v=dQw4w9WgXcQ")
        >>> print(f"Saved to: {result.file_path}")

        >>> # With progress callback
        >>> def on_progress(p):
        ...     print(f"{p.percentage:.1f}% - {p.speed_human}")
        >>> result = download("magnet:?xt=...", progress_callback=on_progress)
    """
    # Resolve output directory
    if output_dir is None:
        from uld.config import get_config

        output_dir = get_config().download_dir
    elif isinstance(output_dir, str):
        output_dir = Path(output_dir).expanduser().resolve()

    # Detect URL type
    engine_type = detect(url)

    # Create download request
    request = DownloadRequest(
        url=url,
        output_dir=output_dir,
        quality=quality,
        seed_ratio=seed_ratio,
        seed_time=seed_time,
        playlist=playlist,
        filename=filename,
    )

    # Get engine and download
    engine = get_engine(engine_type)
    try:
        return asyncio.run(engine.download(request, progress_callback))
    finally:
        engine.close()


def get_info(url: str) -> dict[str, Any]:
    """Get metadata about a URL without downloading.

    Args:
        url: URL, magnet link, or torrent file path.

    Returns:
        Dictionary with metadata (varies by URL type).
        - Videos: title, duration, uploader, formats, etc.
        - Torrents: name, info_hash, total_size, files, etc.
        - HTTP: filename, size, content_type, etc.

    Raises:
        DetectionError: If URL type cannot be determined.
        EngineNotAvailableError: If required engine is not installed.

    Example:
        >>> from uld import get_info
        >>> info = get_info("https://youtube.com/watch?v=...")
        >>> print(info["title"], info["duration"])
    """
    engine_type = detect(url)
    engine = get_engine(engine_type)
    try:
        return engine.get_info(url)
    finally:
        engine.close()


__all__ = [
    # Version
    "__version__",
    "__author__",
    # High-level functions
    "download",
    "get_info",
    # Detection
    "detect",
    "InputDetector",
    # Engine management
    "get_engine",
    "get_available_engines",
    # Types
    "BaseEngine",
    "ProgressCallback",
    # Exceptions
    "ULDError",
    "DetectionError",
    "DownloadError",
    "EngineNotAvailableError",
    "InvalidURLError",
    # Models
    "EngineType",
    "EngineStatus",
    "DownloadRequest",
    "DownloadProgress",
    "DownloadResult",
    "TorrentInfo",
    "VideoInfo",
]
