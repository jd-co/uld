"""Torrent engine using libtorrent for ULD."""

from __future__ import annotations

import asyncio
import contextlib
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.request import urlopen

from uld.config import get_config
from uld.engines.base import BaseEngine, ProgressCallback
from uld.exceptions import (
    DownloadError,
    EngineNotAvailableError,
    TorrentError,
)
from uld.models import (
    DownloadProgress,
    DownloadRequest,
    DownloadResult,
    TorrentFile,
    TorrentInfo,
)

if TYPE_CHECKING:
    import libtorrent as lt

# Try to import libtorrent
_libtorrent_available = False
_libtorrent_version: str | None = None

try:
    # On Windows, import the DLL package first to load OpenSSL dependencies
    if sys.platform == "win32":
        with contextlib.suppress(ImportError):
            import libtorrent_windows_dll  # noqa: F401

    import libtorrent as lt

    _libtorrent_available = True
    _libtorrent_version = lt.__version__
except ImportError:
    lt = None  # type: ignore[assignment]


class TorrentEngine(BaseEngine):
    """Download engine for torrents and magnet links using libtorrent."""

    UPDATE_INTERVAL = 0.5  # seconds between progress updates

    def __init__(self) -> None:
        """Initialize the torrent engine."""
        if not self.is_available():
            raise EngineNotAvailableError(
                "torrent",
                "pip install libtorrent  # or: pip install uld-cli",
            )

        self._session: lt.session | None = None
        self._config = get_config()

    def _get_session(self) -> lt.session:
        """Get or create the libtorrent session."""
        if self._session is None:
            self._session = self._create_session()
        return self._session

    def _create_session(self) -> lt.session:
        """Create a configured libtorrent session."""
        settings: dict[str, Any] = {
            "listen_interfaces": f"0.0.0.0:{self._config.listen_port_start}-{self._config.listen_port_end}",
            "enable_dht": self._config.enable_dht,
            "enable_lsd": self._config.enable_lsd,
            "enable_upnp": self._config.enable_upnp,
            "enable_natpmp": self._config.enable_natpmp,
            "connections_limit": self._config.max_connections,
            "unchoke_slots_limit": self._config.max_upload_slots,
        }

        # Bootstrap DHT nodes
        if self._config.enable_dht:
            settings["dht_bootstrap_nodes"] = (
                "router.bittorrent.com:6881,"
                "router.utorrent.com:6881,"
                "dht.transmissionbt.com:6881"
            )

        # Apply rate limits if set
        if self._config.download_rate_limit > 0:
            settings["download_rate_limit"] = self._config.download_rate_limit * 1024
        if self._config.upload_rate_limit > 0:
            settings["upload_rate_limit"] = self._config.upload_rate_limit * 1024

        session = lt.session(settings)

        return session

    async def download(
        self,
        request: DownloadRequest,
        progress_callback: ProgressCallback | None = None,
    ) -> DownloadResult:
        """Download a torrent or magnet link.

        Args:
            request: Download request with URL and options.
            progress_callback: Optional callback for progress updates.

        Returns:
            DownloadResult with success status and file path.

        Raises:
            DownloadError: If download fails.
        """
        start_time = time.time()
        session = self._get_session()

        try:
            # Add torrent to session
            handle = await self._add_torrent(session, request)

            # Wait for metadata if magnet link
            if not handle.status().has_metadata:
                await self._wait_for_metadata(handle, progress_callback)

            # Get torrent info
            torrent_info = self._extract_torrent_info(handle)

            # Notify callback of metadata
            if progress_callback:
                progress_callback(
                    DownloadProgress(
                        downloaded=0,
                        total=torrent_info.total_size,
                        state="downloading",
                    )
                )

            # Download
            await self._download_loop(handle, request, progress_callback)

            # Seed if configured
            if request.seed_ratio > 0:
                await self._seed_loop(handle, request, progress_callback)

            # Clean up
            session.remove_torrent(handle)

            duration = time.time() - start_time
            status = handle.status()

            return DownloadResult(
                success=True,
                file_path=request.output_dir / torrent_info.name,
                total_downloaded=status.total_done,
                total_uploaded=status.total_upload,
                duration=duration,
                avg_speed=status.total_done / duration if duration > 0 else 0,
            )

        except asyncio.CancelledError:
            # Handle Ctrl+C gracefully - don't wait for cleanup
            # The session.close() in engine.close() will handle it
            raise
        except Exception as e:
            if isinstance(e, (TorrentError, DownloadError)):
                raise
            raise DownloadError(str(e), request.url, cause=e) from e

    def _download_torrent_file(self, url: str) -> bytes:
        """Download a .torrent file from HTTP URL."""
        try:
            with urlopen(url, timeout=30) as response:  # noqa: S310
                return response.read()
        except Exception as e:
            raise TorrentError(f"Failed to download torrent file: {e}") from e

    async def _add_torrent(
        self, session: lt.session, request: DownloadRequest
    ) -> lt.torrent_handle:
        """Add a torrent to the session."""
        params: dict[str, Any] = {
            "save_path": str(request.output_dir),
        }

        url = request.url

        if url.startswith("magnet:"):
            params["url"] = url
        elif url.endswith(".torrent"):
            if url.startswith(("http://", "https://")):
                # Download torrent file first, then parse
                torrent_data = self._download_torrent_file(url)
                info = lt.torrent_info(lt.bdecode(torrent_data))
                params["ti"] = info
            else:
                # Local file
                path = Path(url).expanduser()
                if not path.exists():
                    raise TorrentError(f"Torrent file not found: {path}")
                info = lt.torrent_info(str(path))
                params["ti"] = info
        else:
            raise TorrentError(f"Unsupported torrent input: {url}")

        handle = session.add_torrent(params)
        return handle

    async def _wait_for_metadata(
        self,
        handle: lt.torrent_handle,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        """Wait for torrent metadata to be fetched.

        No timeout - user can press q or Ctrl+C to stop.
        """
        while not handle.status().has_metadata:
            status = handle.status()

            # Update progress with peer info and speed
            if progress_callback:
                progress_callback(
                    DownloadProgress(
                        downloaded=0,
                        total=0,
                        speed=float(status.download_rate),
                        state="fetching_metadata",
                        peers=status.num_peers,
                    )
                )

            await asyncio.sleep(0.5)

    async def _download_loop(
        self,
        handle: lt.torrent_handle,
        _request: DownloadRequest,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        """Main download loop with progress updates."""
        while not handle.status().is_seeding:
            status = handle.status()

            if progress_callback:
                progress = self._status_to_progress(status, "downloading")
                progress_callback(progress)

            # Check for errors
            if status.errc.value() != 0:
                raise TorrentError(f"Torrent error: {status.errc.message()}")

            await asyncio.sleep(self.UPDATE_INTERVAL)

    async def _seed_loop(
        self,
        handle: lt.torrent_handle,
        request: DownloadRequest,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        """Seeding loop until ratio or time is reached."""
        status = handle.status()
        target_upload = int(status.total_done * request.seed_ratio)
        seed_start = time.time()

        while True:
            status = handle.status()

            # Check ratio
            if status.total_upload >= target_upload:
                break

            # Check time limit
            if request.seed_time > 0:
                elapsed_minutes = (time.time() - seed_start) / 60
                if elapsed_minutes >= request.seed_time:
                    break

            if progress_callback:
                progress = self._status_to_progress(status, "seeding")
                progress_callback(progress)

            await asyncio.sleep(self.UPDATE_INTERVAL)

    def _status_to_progress(
        self, status: lt.torrent_status, state: str
    ) -> DownloadProgress:
        """Convert libtorrent status to DownloadProgress."""
        total = status.total_wanted
        downloaded = status.total_done

        # Calculate ETA
        eta = None
        if status.download_rate > 0 and total > downloaded:
            remaining = total - downloaded
            eta = int(remaining / status.download_rate)

        return DownloadProgress(
            downloaded=downloaded,
            total=total,
            speed=float(status.download_rate),
            upload_speed=float(status.upload_rate),
            uploaded=status.total_upload,
            percentage=status.progress * 100,
            eta=eta,
            peers=status.num_peers,
            seeds=status.num_seeds,
            state=state,
        )

    def _extract_torrent_info(self, handle: lt.torrent_handle) -> TorrentInfo:
        """Extract torrent metadata from handle."""
        ti = handle.torrent_file()

        files: list[TorrentFile] = []
        file_storage = ti.files()
        for i in range(file_storage.num_files()):
            files.append(
                TorrentFile(
                    path=file_storage.file_path(i),
                    size=file_storage.file_size(i),
                )
            )

        # Get trackers (handle both dict and object formats)
        trackers = []
        for tracker in handle.trackers():
            if isinstance(tracker, dict):
                trackers.append(tracker.get("url", ""))
            else:
                trackers.append(tracker.url)
        trackers = [t for t in trackers if t]  # Filter empty

        return TorrentInfo(
            name=ti.name(),
            info_hash=str(ti.info_hash()),
            total_size=ti.total_size(),
            files=files,
            piece_length=ti.piece_length(),
            num_pieces=ti.num_pieces(),
            comment=ti.comment() or None,
            creator=ti.creator() or None,
            trackers=trackers,
        )

    def validate(self, url: str) -> bool:
        """Check if this engine can handle the given URL."""
        url_lower = url.lower().strip()
        return url_lower.startswith("magnet:") or url_lower.endswith(".torrent")

    @classmethod
    def is_available(cls) -> bool:
        """Check if libtorrent is installed."""
        return _libtorrent_available

    @classmethod
    def get_version(cls) -> str | None:
        """Get libtorrent version."""
        return _libtorrent_version

    def get_info(self, url: str) -> dict[str, Any]:
        """Get torrent metadata without downloading."""
        session = self._get_session()

        params: dict[str, Any] = {
            "save_path": "/tmp",
            "flags": lt.torrent_flags.upload_mode,  # Don't actually download
        }

        if url.startswith("magnet:"):
            params["url"] = url
        elif url.endswith(".torrent"):
            if url.startswith(("http://", "https://")):
                # Download torrent file first, then parse
                torrent_data = self._download_torrent_file(url)
                info = lt.torrent_info(lt.bdecode(torrent_data))
                params["ti"] = info
            else:
                path = Path(url).expanduser()
                info = lt.torrent_info(str(path))
                params["ti"] = info

        handle = session.add_torrent(params)

        # Wait for metadata (only needed for magnet links)
        # No timeout - user can Ctrl+C to stop
        while not handle.status().has_metadata:
            time.sleep(0.5)

        torrent_info = self._extract_torrent_info(handle)
        session.remove_torrent(handle)

        return torrent_info.model_dump()

    def close(self) -> None:
        """Close the libtorrent session."""
        if self._session is not None:
            # Don't call pause() - it blocks waiting for disk/network
            # Just drop the reference; session cleanup happens on GC
            self._session = None
