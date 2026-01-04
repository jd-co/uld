"""Video engine using yt-dlp for ULD."""

from __future__ import annotations

import asyncio
import concurrent.futures
import contextlib
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from uld.config import get_config
from uld.engines.base import BaseEngine, ProgressCallback
from uld.exceptions import DownloadError, EngineNotAvailableError
from uld.models import DownloadProgress, DownloadRequest, DownloadResult

if TYPE_CHECKING:
    import yt_dlp

# Try to import yt-dlp
_ytdlp_available = False
_ytdlp_version: str | None = None

try:
    import yt_dlp

    _ytdlp_available = True
    _ytdlp_version = yt_dlp.version.__version__
except ImportError:
    yt_dlp = None  # type: ignore[assignment]


class VideoEngine(BaseEngine):
    """Download engine for video platforms using yt-dlp."""

    # Quality presets
    QUALITY_FORMATS = {
        "best": "bestvideo+bestaudio/best",
        "worst": "worstvideo+worstaudio/worst",
        "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
        "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]",
        "480p": "bestvideo[height<=480]+bestaudio/best[height<=480]",
        "360p": "bestvideo[height<=360]+bestaudio/best[height<=360]",
    }

    def __init__(self) -> None:
        """Initialize the video engine."""
        if not self.is_available():
            raise EngineNotAvailableError(
                "video",
                "pip install yt-dlp  # or: pip install uld-cli",
            )
        self._config = get_config()

    async def download(
        self,
        request: DownloadRequest,
        progress_callback: ProgressCallback | None = None,
    ) -> DownloadResult:
        """Download a video from URL.

        Args:
            request: Download request with URL and options.
            progress_callback: Optional callback for progress updates.

        Returns:
            DownloadResult with success status and file path.
        """
        start_time = time.time()
        downloaded_file: Path | None = None

        # Build yt-dlp options
        quality = request.quality or "best"
        format_str = self.QUALITY_FORMATS.get(quality, quality)

        # Auto-detect playlist URLs or use explicit flag
        is_playlist = request.playlist or self._is_playlist_url(request.url)

        # Output template: add playlist index if downloading playlist
        if is_playlist:
            outtmpl = str(
                request.output_dir
                / "%(playlist_title)s/%(playlist_index)s - %(title)s.%(ext)s"
            )
        else:
            outtmpl = str(request.output_dir / "%(title)s.%(ext)s")

        ydl_opts: dict[str, Any] = {
            "format": format_str,
            "outtmpl": outtmpl,
            "noplaylist": not is_playlist,
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
        }

        # Progress tracking state - track cumulative across streams
        progress_state = {
            "downloaded": 0,
            "total": 0,
            "speed": 0.0,
            "cumulative_downloaded": 0,  # Total across all streams
        }
        cancel_event = threading.Event()

        def progress_hook(d: dict[str, Any]) -> None:
            # Check if download was cancelled
            if cancel_event.is_set():
                raise Exception("Download cancelled by user")
            if d["status"] == "downloading":
                progress_state["downloaded"] = d.get("downloaded_bytes", 0)
                progress_state["total"] = d.get("total_bytes") or d.get(
                    "total_bytes_estimate", 0
                )
                progress_state["speed"] = d.get("speed", 0) or 0

                if progress_callback:
                    total = int(progress_state["total"])
                    downloaded = int(progress_state["downloaded"])
                    speed = progress_state["speed"]

                    percentage = (downloaded / total * 100) if total > 0 else 0
                    eta = int((total - downloaded) / speed) if speed > 0 else None

                    # Get playlist info from yt-dlp info_dict
                    info = d.get("info_dict", {})
                    playlist_index = info.get("playlist_index")
                    playlist_count = info.get("playlist_count") or info.get("n_entries")
                    video_title = info.get("title")

                    progress_callback(
                        DownloadProgress(
                            downloaded=downloaded,
                            total=total,
                            speed=speed,
                            percentage=percentage,
                            eta=eta,
                            state="downloading",
                            playlist_index=playlist_index,
                            playlist_count=playlist_count,
                            video_title=video_title,
                        )
                    )

            elif d["status"] == "finished":
                # Add completed stream size to cumulative total
                progress_state["cumulative_downloaded"] += d.get("downloaded_bytes", 0)
                downloaded_file_path = d.get("filename")
                if downloaded_file_path:
                    nonlocal downloaded_file
                    downloaded_file = Path(downloaded_file_path)

        ydl_opts["progress_hooks"] = [progress_hook]

        # Run download in executor (yt-dlp is sync)
        # Create a future we can cancel
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = executor.submit(self._run_download, request.url, ydl_opts)

        try:
            # Wait for download with cancellation support
            while not future.done():
                try:
                    await asyncio.sleep(0.1)
                except asyncio.CancelledError:
                    # Signal yt-dlp to stop
                    cancel_event.set()
                    # Wait briefly for yt-dlp to notice
                    with contextlib.suppress(Exception):
                        future.result(timeout=2.0)
                    raise

            # Check if download raised an exception
            future.result()

            duration = time.time() - start_time

            # Get actual file size (yt-dlp merges video+audio streams)
            total_downloaded = progress_state["cumulative_downloaded"]
            result_path = downloaded_file

            if is_playlist and downloaded_file:
                # For playlists, return the playlist directory
                result_path = downloaded_file.parent
                # Sum up all files in playlist directory
                if result_path.exists():
                    total_downloaded = sum(
                        f.stat().st_size for f in result_path.rglob("*") if f.is_file()
                    )
            elif downloaded_file and downloaded_file.exists():
                total_downloaded = downloaded_file.stat().st_size

            return DownloadResult(
                success=True,
                file_path=result_path,
                total_downloaded=total_downloaded,
                duration=duration,
                avg_speed=(total_downloaded / duration if duration > 0 else 0),
            )

        except asyncio.CancelledError:
            cancel_event.set()
            raise
        except Exception as e:
            # Check if it was a user cancellation
            if "cancelled" in str(e).lower():
                raise asyncio.CancelledError() from e
            raise DownloadError(str(e), request.url, cause=e) from e
        finally:
            executor.shutdown(wait=False)

    def _run_download(self, url: str, ydl_opts: dict[str, Any]) -> None:
        """Run yt-dlp download (sync, called from executor)."""
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

    def get_info(self, url: str) -> dict[str, Any]:
        """Get video metadata without downloading."""
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "noplaylist": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        if info is None:
            return {"url": url, "error": "Could not extract info"}

        # Extract available formats/qualities
        formats = []
        if "formats" in info:
            seen_heights = set()
            for f in info["formats"]:
                height = f.get("height")
                if height and height not in seen_heights:
                    seen_heights.add(height)
                    formats.append(f"{height}p")
            formats.sort(key=lambda x: int(x[:-1]), reverse=True)

        return {
            "title": info.get("title", "Unknown"),
            "duration": info.get("duration", 0),
            "uploader": info.get("uploader"),
            "view_count": info.get("view_count"),
            "upload_date": info.get("upload_date"),
            "description": (info.get("description") or "")[:200],
            "thumbnail": info.get("thumbnail"),
            "formats": formats,
            "webpage_url": info.get("webpage_url", url),
        }

    def _is_playlist_url(self, url: str) -> bool:
        """Check if URL is a playlist URL."""
        url_lower = url.lower()
        # YouTube playlist patterns
        if "youtube.com/playlist" in url_lower:
            return True
        if "list=" in url_lower and (
            "youtube.com" in url_lower or "youtu.be" in url_lower
        ):
            return True
        # Vimeo album/showcase
        if "vimeo.com/album" in url_lower or "vimeo.com/showcase" in url_lower:
            return True
        # SoundCloud sets
        return "soundcloud.com" in url_lower and "/sets/" in url_lower

    def validate(self, url: str) -> bool:
        """Check if this engine can handle the given URL."""
        # Use detector's video platform list
        from uld.detector import InputDetector

        detector = InputDetector()
        return detector._is_video_platform(url)

    @classmethod
    def is_available(cls) -> bool:
        """Check if yt-dlp is installed."""
        return _ytdlp_available

    @classmethod
    def get_version(cls) -> str | None:
        """Get yt-dlp version."""
        return _ytdlp_version

    def close(self) -> None:
        """Cleanup (no-op for yt-dlp)."""
        return None
