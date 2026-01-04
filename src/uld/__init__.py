"""ULD - Unified Local Downloader.

A single CLI tool for downloading content from multiple sources:
torrents, magnet links, video platforms, and direct URLs.
"""

__version__ = "1.0.5"
__author__ = "Sheik Javeed"

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
    EngineType,
    TorrentInfo,
    VideoInfo,
)

__all__ = [
    # Version
    "__version__",
    "__author__",
    # Exceptions
    "ULDError",
    "DetectionError",
    "DownloadError",
    "EngineNotAvailableError",
    "InvalidURLError",
    # Models
    "EngineType",
    "DownloadRequest",
    "DownloadProgress",
    "DownloadResult",
    "TorrentInfo",
    "VideoInfo",
]
