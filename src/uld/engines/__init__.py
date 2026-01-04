"""Download engines for ULD."""

from uld.engines.base import BaseEngine
from uld.models import EngineStatus, EngineType

__all__ = [
    "BaseEngine",
    "get_engine",
    "get_available_engines",
]


def get_engine(engine_type: EngineType) -> BaseEngine:
    """Get an engine instance by type.

    Args:
        engine_type: The type of engine to get.

    Returns:
        An instance of the appropriate engine.

    Raises:
        EngineNotAvailableError: If the engine is not available.
    """
    if engine_type == EngineType.TORRENT:
        from uld.engines.torrent import TorrentEngine

        return TorrentEngine()
    elif engine_type == EngineType.VIDEO:
        from uld.engines.video import VideoEngine

        return VideoEngine()
    elif engine_type == EngineType.HTTP:
        from uld.engines.http import HTTPEngine

        return HTTPEngine()
    else:
        from uld.exceptions import EngineNotAvailableError

        raise EngineNotAvailableError(str(engine_type))


def get_available_engines() -> list[EngineStatus]:
    """Get status of all engines.

    Returns:
        List of EngineStatus for all engines.
    """
    engines: list[EngineStatus] = []

    # Torrent engine
    try:
        from uld.engines.torrent import TorrentEngine

        engines.append(
            EngineStatus(
                name="torrent",
                engine_type=EngineType.TORRENT,
                available=TorrentEngine.is_available(),
                version=TorrentEngine.get_version(),
                install_hint='pip install "uld-cli[torrent]"',
            )
        )
    except ImportError:
        engines.append(
            EngineStatus(
                name="torrent",
                engine_type=EngineType.TORRENT,
                available=False,
                install_hint='pip install "uld-cli[torrent]"',
            )
        )

    # Video engine
    try:
        from uld.engines.video import VideoEngine

        engines.append(
            EngineStatus(
                name="video",
                engine_type=EngineType.VIDEO,
                available=VideoEngine.is_available(),
                version=VideoEngine.get_version(),
                install_hint='pip install "uld-cli[video]"',
            )
        )
    except ImportError:
        engines.append(
            EngineStatus(
                name="video",
                engine_type=EngineType.VIDEO,
                available=False,
                install_hint='pip install "uld-cli[video]"',
            )
        )

    # HTTP engine
    try:
        from uld.engines.http import HTTPEngine

        engines.append(
            EngineStatus(
                name="http",
                engine_type=EngineType.HTTP,
                available=HTTPEngine.is_available(),
                version=HTTPEngine.get_version(),
                install_hint='pip install "uld-cli[http]"',
            )
        )
    except ImportError:
        engines.append(
            EngineStatus(
                name="http",
                engine_type=EngineType.HTTP,
                available=False,
                install_hint='pip install "uld-cli[http]"',
            )
        )

    return engines
