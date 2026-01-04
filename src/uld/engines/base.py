"""Base engine interface for ULD."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from uld.models import DownloadProgress, DownloadRequest, DownloadResult

# Type alias for progress callback
ProgressCallback = Callable[[DownloadProgress], None]


class BaseEngine(ABC):
    """Abstract base class for all download engines.

    All engines must implement:
    - download(): Main download method
    - validate(): Check if engine can handle the input
    - is_available(): Check if engine dependencies are installed
    """

    @abstractmethod
    async def download(
        self,
        request: DownloadRequest,
        progress_callback: ProgressCallback | None = None,
    ) -> DownloadResult:
        """Download content from the given request.

        Args:
            request: Download request with URL and options.
            progress_callback: Optional callback for progress updates.

        Returns:
            DownloadResult with success status and file path.

        Raises:
            DownloadError: If download fails.
        """
        pass

    @abstractmethod
    def validate(self, url: str) -> bool:
        """Check if this engine can handle the given URL.

        Args:
            url: URL or input string to validate.

        Returns:
            True if this engine can handle the input.
        """
        pass

    @classmethod
    @abstractmethod
    def is_available(cls) -> bool:
        """Check if engine dependencies are installed and available.

        Returns:
            True if the engine can be used.
        """
        pass

    @classmethod
    def get_version(cls) -> str | None:
        """Get the version of the underlying library.

        Returns:
            Version string or None if not available.
        """
        return None

    @classmethod
    def get_name(cls) -> str:
        """Get the engine name.

        Returns:
            Human-readable engine name.
        """
        return cls.__name__.replace("Engine", "")

    def get_info(self, url: str) -> dict[str, Any]:
        """Get metadata information without downloading.

        Args:
            url: URL to get info for.

        Returns:
            Dictionary with metadata.
        """
        return {"url": url}

    def close(self) -> None:
        """Clean up engine resources.

        Override in subclasses if cleanup is needed.
        """
        return None

    def __enter__(self) -> "BaseEngine":
        """Enter context manager."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Exit context manager and clean up resources."""
        self.close()
