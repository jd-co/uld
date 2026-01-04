"""Input type detection for ULD.

Automatically detects the type of input and routes to the appropriate engine.
"""

import re
from pathlib import Path
from urllib.parse import urlparse

from uld.exceptions import DetectionError
from uld.models import EngineType


class InputDetector:
    """Detects input type and returns the appropriate engine type."""

    # Magnet URI pattern
    MAGNET_PATTERN = re.compile(
        r"^magnet:\?xt=urn:btih:[a-fA-F0-9]{40,}", re.IGNORECASE
    )

    # Magnet URI with base32 hash (more common now)
    MAGNET_BASE32_PATTERN = re.compile(
        r"^magnet:\?xt=urn:btih:[a-zA-Z2-7]{32}", re.IGNORECASE
    )

    # Video platform domains
    VIDEO_PLATFORMS = frozenset(
        {
            "youtube.com",
            "www.youtube.com",
            "youtu.be",
            "vimeo.com",
            "www.vimeo.com",
            "dailymotion.com",
            "www.dailymotion.com",
            "twitch.tv",
            "www.twitch.tv",
            "twitter.com",
            "x.com",
            "tiktok.com",
            "www.tiktok.com",
            "instagram.com",
            "www.instagram.com",
            "facebook.com",
            "www.facebook.com",
            "fb.watch",
            "reddit.com",
            "www.reddit.com",
            "v.redd.it",
            "streamable.com",
            "soundcloud.com",
            "www.soundcloud.com",
            "bandcamp.com",
        }
    )

    # File extensions that indicate direct downloads
    DIRECT_DOWNLOAD_EXTENSIONS = frozenset(
        {
            ".zip",
            ".tar",
            ".gz",
            ".bz2",
            ".xz",
            ".7z",
            ".rar",
            ".iso",
            ".exe",
            ".msi",
            ".dmg",
            ".deb",
            ".rpm",
            ".AppImage",
            ".pdf",
            ".doc",
            ".docx",
            ".apk",
        }
    )

    def detect(self, input_str: str) -> EngineType:
        """Detect the type of input and return the appropriate engine type.

        Args:
            input_str: URL, magnet link, or file path.

        Returns:
            EngineType indicating which engine should handle this input.

        Raises:
            DetectionError: If input type cannot be determined.
        """
        input_str = input_str.strip()

        if not input_str:
            raise DetectionError(input_str)

        # Check for magnet links first (most specific)
        if self._is_magnet(input_str):
            return EngineType.TORRENT

        # Check for torrent files
        if self._is_torrent_file(input_str):
            return EngineType.TORRENT

        # Check for video platforms
        if self._is_video_platform(input_str):
            return EngineType.VIDEO

        # Check for direct URLs
        if self._is_direct_url(input_str):
            return EngineType.HTTP

        raise DetectionError(input_str)

    def _is_magnet(self, s: str) -> bool:
        """Check if string is a magnet URI."""
        if not s.lower().startswith("magnet:"):
            return False
        return bool(self.MAGNET_PATTERN.match(s) or self.MAGNET_BASE32_PATTERN.match(s))

    def _is_torrent_file(self, s: str) -> bool:
        """Check if string is a path to a torrent file."""
        # Check file extension
        if s.lower().endswith(".torrent"):
            # Could be a URL or a local file
            if s.startswith(("http://", "https://")):
                return True
            # Check if local file exists
            path = Path(s).expanduser()
            return path.exists() and path.is_file()
        return False

    def _is_video_platform(self, s: str) -> bool:
        """Check if URL is from a known video platform."""
        if not s.startswith(("http://", "https://")):
            return False

        try:
            parsed = urlparse(s)
            domain = parsed.netloc.lower()
            # Remove www. prefix for comparison if not in set
            domain_without_www = domain.removeprefix("www.")
            return domain in self.VIDEO_PLATFORMS or domain_without_www in {
                d.removeprefix("www.") for d in self.VIDEO_PLATFORMS
            }
        except Exception:
            return False

    def _is_direct_url(self, s: str) -> bool:
        """Check if string is a direct download URL."""
        if not s.startswith(("http://", "https://")):
            return False

        try:
            parsed = urlparse(s)
            # Must have a valid netloc
            if not parsed.netloc:
                return False

            # Check for known download extensions
            path_lower = parsed.path.lower()
            for ext in self.DIRECT_DOWNLOAD_EXTENSIONS:
                if path_lower.endswith(ext):
                    return True

            # Generic HTTP URL (could be anything)
            return True
        except Exception:
            return False

    def get_info(self, input_str: str) -> dict[str, str | EngineType]:
        """Get detailed information about the detected input.

        Returns:
            Dictionary with 'type', 'original', and additional metadata.
        """
        engine_type = self.detect(input_str)

        info: dict[str, str | EngineType] = {
            "type": engine_type,
            "original": input_str,
        }

        if engine_type == EngineType.TORRENT:
            if self._is_magnet(input_str):
                info["subtype"] = "magnet"
                # Extract info hash
                match = re.search(r"btih:([a-fA-F0-9]{40}|[a-zA-Z2-7]{32})", input_str)
                if match:
                    info["info_hash"] = match.group(1)
            else:
                info["subtype"] = "torrent_file"

        elif engine_type == EngineType.VIDEO:
            parsed = urlparse(input_str)
            info["platform"] = parsed.netloc

        elif engine_type == EngineType.HTTP:
            parsed = urlparse(input_str)
            info["host"] = parsed.netloc

        return info


# Singleton instance
_detector: InputDetector | None = None


def get_detector() -> InputDetector:
    """Get the singleton detector instance."""
    global _detector
    if _detector is None:
        _detector = InputDetector()
    return _detector


def detect(input_str: str) -> EngineType:
    """Convenience function to detect input type.

    Args:
        input_str: URL, magnet link, or file path.

    Returns:
        EngineType indicating which engine should handle this input.
    """
    return get_detector().detect(input_str)
