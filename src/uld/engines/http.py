"""HTTP engine using httpx for direct file downloads."""

from __future__ import annotations

import asyncio
import re
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import unquote, urlparse

from uld.engines.base import BaseEngine, ProgressCallback
from uld.exceptions import DownloadError, EngineNotAvailableError
from uld.models import DownloadProgress, DownloadRequest, DownloadResult

if TYPE_CHECKING:
    import httpx

# Try to import httpx
_httpx_available = False
_httpx_version: str | None = None

try:
    import httpx

    _httpx_available = True
    _httpx_version = httpx.__version__
except ImportError:
    httpx = None  # type: ignore[assignment]

# Chunk size for streaming (64KB)
CHUNK_SIZE = 64 * 1024


class HTTPEngine(BaseEngine):
    """Download engine for direct HTTP/HTTPS file downloads."""

    def __init__(self) -> None:
        """Initialize the HTTP engine."""
        if not self.is_available():
            raise EngineNotAvailableError(
                "http",
                'pip install httpx  # or: pip install "uld-cli[http]"',
            )
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the async HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                follow_redirects=True,
                timeout=httpx.Timeout(30.0, connect=10.0),
            )
        return self._client

    async def download(
        self,
        request: DownloadRequest,
        progress_callback: ProgressCallback | None = None,
    ) -> DownloadResult:
        """Download a file from URL.

        Args:
            request: Download request with URL and options.
            progress_callback: Optional callback for progress updates.

        Returns:
            DownloadResult with success status and file path.
        """
        start_time = time.time()
        client = await self._get_client()

        try:
            async with client.stream("GET", request.url) as response:
                response.raise_for_status()

                # Get total size from Content-Length header
                total_size = int(response.headers.get("content-length", 0))

                # Determine filename
                filename = request.filename or self._extract_filename(
                    request.url, response.headers
                )
                output_path = request.output_dir / filename

                # Ensure output directory exists
                request.output_dir.mkdir(parents=True, exist_ok=True)

                # Send initial progress (0 speed) before download starts
                if progress_callback:
                    progress_callback(
                        DownloadProgress(
                            downloaded=0,
                            total=total_size,
                            speed=0.0,
                            percentage=0,
                            state="downloading",
                        )
                    )

                # Download with progress tracking
                downloaded = 0
                last_update = time.time()
                speed_bytes = 0
                speed_window: list[tuple[float, int]] = []

                with open(output_path, "wb") as f:
                    async for chunk in response.aiter_bytes(CHUNK_SIZE):
                        f.write(chunk)
                        downloaded += len(chunk)

                        # Calculate speed using sliding window
                        now = time.time()
                        speed_window.append((now, len(chunk)))
                        # Keep only last 2 seconds of data
                        speed_window = [
                            (t, s) for t, s in speed_window if now - t < 2.0
                        ]
                        if speed_window:
                            window_time = now - speed_window[0][0]
                            if window_time > 0:
                                speed_bytes = (
                                    sum(s for _, s in speed_window) / window_time
                                )

                        # Update progress (throttle to ~10 updates/sec)
                        if progress_callback and now - last_update >= 0.1:
                            last_update = now
                            percentage = (
                                (downloaded / total_size * 100) if total_size > 0 else 0
                            )
                            eta = (
                                int((total_size - downloaded) / speed_bytes)
                                if speed_bytes > 0 and total_size > 0
                                else None
                            )

                            progress_callback(
                                DownloadProgress(
                                    downloaded=downloaded,
                                    total=total_size,
                                    speed=speed_bytes,
                                    percentage=percentage,
                                    eta=eta,
                                    state="downloading",
                                )
                            )

                duration = time.time() - start_time

                return DownloadResult(
                    success=True,
                    file_path=output_path,
                    total_downloaded=downloaded,
                    duration=duration,
                    avg_speed=(downloaded / duration if duration > 0 else 0),
                )

        except httpx.HTTPStatusError as e:
            raise DownloadError(
                f"HTTP {e.response.status_code}: {e.response.reason_phrase}",
                request.url,
                cause=e,
            ) from e
        except httpx.RequestError as e:
            raise DownloadError(str(e), request.url, cause=e) from e
        except asyncio.CancelledError:
            raise
        except Exception as e:
            raise DownloadError(str(e), request.url, cause=e) from e

    def _extract_filename(self, url: str, headers: httpx.Headers) -> str:
        """Extract filename from Content-Disposition header or URL."""
        # Try Content-Disposition header first
        content_disp = headers.get("content-disposition", "")
        if content_disp:
            # Try filename*= (RFC 5987)
            match = re.search(r"filename\*=(?:UTF-8'')?([^;]+)", content_disp, re.I)
            if match:
                return unquote(match.group(1).strip('"'))
            # Try filename=
            match = re.search(r'filename=(["\']?)(.+?)\1(?:;|$)', content_disp, re.I)
            if match:
                return unquote(match.group(2).strip())

        # Fall back to URL path
        parsed = urlparse(url)
        path = unquote(parsed.path)
        if path and path != "/":
            filename = Path(path).name
            if filename:
                return filename

        # Last resort: use domain + timestamp
        return f"download_{int(time.time())}"

    def get_info(self, url: str) -> dict[str, Any]:
        """Get file metadata without downloading (HEAD request)."""
        import asyncio

        async def _get_info() -> dict[str, Any]:
            client = await self._get_client()
            try:
                response = await client.head(url, follow_redirects=True)
                response.raise_for_status()

                size = int(response.headers.get("content-length", 0))
                content_type = response.headers.get("content-type", "unknown")
                filename = self._extract_filename(url, response.headers)

                return {
                    "url": url,
                    "filename": filename,
                    "size": size,
                    "content_type": content_type,
                    "accepts_ranges": response.headers.get("accept-ranges") == "bytes",
                }
            except Exception as e:
                return {"url": url, "error": str(e)}

        return asyncio.get_event_loop().run_until_complete(_get_info())

    def validate(self, url: str) -> bool:
        """Check if this engine can handle the given URL."""
        return url.startswith(("http://", "https://"))

    @classmethod
    def is_available(cls) -> bool:
        """Check if httpx is installed."""
        return _httpx_available

    @classmethod
    def get_version(cls) -> str | None:
        """Get httpx version."""
        return _httpx_version

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            # httpx clients are safe to leave for garbage collection
            # Explicit async close can cause issues when event loop is closed
            self._client = None
