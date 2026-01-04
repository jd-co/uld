"""Custom exceptions for ULD."""


class ULDError(Exception):
    """Base exception for all ULD errors."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(self.message)


class DetectionError(ULDError):
    """Raised when input type cannot be detected."""

    def __init__(self, input_str: str) -> None:
        self.input_str = input_str
        super().__init__(f"Could not detect input type for: {input_str}")


class InvalidURLError(ULDError):
    """Raised when URL is invalid or malformed."""

    def __init__(self, url: str, reason: str | None = None) -> None:
        self.url = url
        self.reason = reason
        message = f"Invalid URL: {url}"
        if reason:
            message += f" ({reason})"
        super().__init__(message)


class EngineNotAvailableError(ULDError):
    """Raised when required engine is not installed or available."""

    def __init__(self, engine_name: str, install_hint: str | None = None) -> None:
        self.engine_name = engine_name
        self.install_hint = install_hint
        message = f"Engine '{engine_name}' is not available"
        if install_hint:
            message += f". Install with: {install_hint}"
        super().__init__(message)


class DownloadError(ULDError):
    """Raised when download fails."""

    def __init__(
        self,
        message: str,
        url: str | None = None,
        cause: Exception | None = None,
    ) -> None:
        self.url = url
        self.cause = cause
        full_message = message
        if url:
            full_message = f"{message} (URL: {url})"
        super().__init__(full_message)


class TorrentError(DownloadError):
    """Raised for torrent-specific errors."""

    pass


class MetadataFetchError(TorrentError):
    """Raised when torrent metadata cannot be fetched."""

    def __init__(self, magnet_or_file: str, timeout: int | None = None) -> None:
        self.magnet_or_file = magnet_or_file
        self.timeout = timeout
        message = f"Failed to fetch metadata for: {magnet_or_file}"
        if timeout:
            message += f" (timeout: {timeout}s)"
        super().__init__(message)
