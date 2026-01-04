"""ULD - Unified Local Downloader.

A single CLI tool for downloading content from multiple sources:
torrents, magnet links, video platforms, and direct URLs.
"""

from importlib.metadata import metadata

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

_meta = metadata("uld-cli")
__version__ = _meta["Version"]
__author__ = _meta["Author"]

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
