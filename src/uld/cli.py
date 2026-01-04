"""CLI interface for ULD using Typer."""

from __future__ import annotations

import asyncio
import select
import signal
import sys
import threading
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from uld import __version__
from uld.config import get_config
from uld.detector import detect, get_detector
from uld.engines import get_available_engines, get_engine
from uld.exceptions import DetectionError, EngineNotAvailableError, ULDError
from uld.models import DownloadRequest, EngineType, VideoInfo
from uld.progress import ProgressDisplay

# Create Typer app
app = typer.Typer(
    name="uld",
    help="Unified Local Downloader - Download torrents, videos, and files from anywhere.",
    add_completion=False,
    no_args_is_help=True,
)

console = Console()


def _listen_for_quit(stop_callback: object) -> None:
    """Listen for 'q' key in background. Calls stop_callback when pressed."""
    try:
        if sys.platform == "win32":
            import msvcrt

            while True:
                if msvcrt.kbhit() and msvcrt.getch().lower() == b"q":
                    stop_callback()  # type: ignore[operator]
                    return
        else:
            import termios
            import tty

            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            try:
                tty.setcbreak(fd)
                while True:
                    if (
                        select.select([sys.stdin], [], [], 0.1)[0]
                        and sys.stdin.read(1).lower() == "q"
                    ):
                        stop_callback()  # type: ignore[operator]
                        return
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
    except Exception:
        pass  # Ctrl+C still works as fallback


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"ULD version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            "-V",
            help="Show version and exit.",
            callback=version_callback,
            is_eager=True,
        ),
    ] = None,
) -> None:
    """ULD - Unified Local Downloader.

    A single CLI tool for downloading content from multiple sources:
    torrents, magnet links, video platforms, and direct URLs.
    """
    pass


@app.command()
def download(
    url: Annotated[
        str, typer.Argument(help="URL, magnet link, or torrent file to download")
    ],
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Output directory for downloads.",
        ),
    ] = None,
    seed_ratio: Annotated[
        float,
        typer.Option(
            "--seed-ratio",
            "-r",
            help="Seed ratio target for torrents (0 = no seeding).",
            min=0.0,
        ),
    ] = 1.0,
    no_seed: Annotated[
        bool,
        typer.Option(
            "--no-seed",
            help="Don't seed after torrent download completes.",
        ),
    ] = False,
    quiet: Annotated[
        bool,
        typer.Option(
            "--quiet",
            "-q",
            help="Minimal output (errors only).",
        ),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Verbose output.",
        ),
    ] = False,
    quality: Annotated[
        str | None,
        typer.Option(
            "--quality",
            "-Q",
            help="Video quality (e.g., 'best', '1080p', '720p', 'worst').",
        ),
    ] = None,
    playlist: Annotated[
        bool,
        typer.Option(
            "--playlist",
            "-P",
            help="Download entire playlist (video only).",
        ),
    ] = False,
) -> None:
    """Download content from a URL, magnet link, or torrent file.

    Examples:
        uld download magnet:?xt=urn:btih:...
        uld download ./ubuntu.torrent -o ~/Downloads
        uld download magnet:... --no-seed
        uld download https://youtube.com/watch?v=... -Q 720p
        uld download https://youtube.com/playlist?list=... --playlist
    """
    config = get_config()
    progress = ProgressDisplay(console=console, quiet=quiet)

    # Determine output directory
    output_dir = output or config.download_dir

    # Create output directory if needed
    output_dir.mkdir(parents=True, exist_ok=True)

    # Detect input type
    try:
        engine_type = detect(url)
    except DetectionError as e:
        progress.show_error(e)
        raise typer.Exit(1) from e

    if verbose:
        info = get_detector().get_info(url)
        progress.print(f"Detected: {engine_type.value}", style="dim")
        if "info_hash" in info:
            progress.print(f"Info hash: {info['info_hash']}", style="dim")

    # Get engine
    try:
        engine = get_engine(engine_type)
    except EngineNotAvailableError as e:
        progress.show_error(e)
        raise typer.Exit(1) from e

    # Build request
    request = DownloadRequest(
        url=url,
        output_dir=output_dir,
        seed_ratio=0.0 if no_seed else seed_ratio,
        quality=quality,
        playlist=playlist,
    )

    # Run download with proper cancellation handling
    with engine:
        try:
            if not quiet:
                console.print("[dim]Press q or Ctrl+C to stop or exit[/dim]")
            progress.start(description="Starting download...", total=0)

            async def run_download() -> None:
                loop = asyncio.get_running_loop()
                task = asyncio.current_task()

                def trigger_stop() -> None:
                    progress.print("\nStopping...", style="yellow")
                    if task:
                        loop.call_soon_threadsafe(task.cancel)

                # Start 'q' key listener in background
                quit_thread = threading.Thread(
                    target=_listen_for_quit, args=(trigger_stop,), daemon=True
                )
                quit_thread.start()

                signal.signal(signal.SIGINT, lambda *_: trigger_stop())
                signal.signal(signal.SIGTERM, lambda *_: trigger_stop())

                try:
                    result = await engine.download(
                        request, progress_callback=progress.update
                    )
                    progress.stop()
                    progress.show_complete(result)
                    if not result.success:
                        raise typer.Exit(1)
                except asyncio.CancelledError:
                    progress.stop()
                    progress.print("Stopped.", style="yellow")
                    raise SystemExit(0) from None

            asyncio.run(run_download())

        except KeyboardInterrupt:
            progress.stop()
            progress.print("Stopped.", style="yellow")
            raise SystemExit(0) from None
        except ULDError as e:
            progress.stop()
            progress.show_error(e)
            raise typer.Exit(1) from e
        except SystemExit:
            raise
        except Exception as e:
            progress.stop()
            progress.show_error(e)
            if verbose:
                console.print_exception()
            raise typer.Exit(1) from e


@app.command()
def info(
    url: Annotated[str, typer.Argument(help="URL or magnet link to get info for")],
) -> None:
    """Show metadata information without downloading.

    Examples:
        uld info magnet:?xt=urn:btih:...
        uld info ./ubuntu.torrent
    """
    progress = ProgressDisplay(console=console)

    # Detect input type
    try:
        engine_type = detect(url)
    except DetectionError as e:
        progress.show_error(e)
        raise typer.Exit(1) from e

    # Get engine
    try:
        engine = get_engine(engine_type)
    except EngineNotAvailableError as e:
        progress.show_error(e)
        raise typer.Exit(1) from e

    # Get and display info
    with engine:
        try:
            progress.print("Fetching metadata...", style="dim")
            metadata = engine.get_info(url)

            if engine_type == EngineType.TORRENT:
                from uld.models import TorrentInfo

                info_obj = TorrentInfo(**metadata)
                progress.show_metadata(info_obj)
            elif engine_type == EngineType.VIDEO:
                info_obj = VideoInfo(**metadata)
                progress.show_video_metadata(info_obj)
            else:
                # Generic display
                for key, value in metadata.items():
                    progress.print(f"{key}: {value}")

        except ULDError as e:
            progress.show_error(e)
            raise typer.Exit(1) from e
        except Exception as e:
            progress.show_error(e)
            raise typer.Exit(1) from e


@app.command()
def engines() -> None:
    """List available download engines and their status."""
    progress = ProgressDisplay(console=console)
    available = get_available_engines()
    progress.show_engines(available)


@app.command()
def config() -> None:
    """Show current configuration."""
    cfg = get_config()

    console.print("[bold]ULD Configuration[/bold]\n")

    # General
    console.print("[cyan]General:[/cyan]")
    console.print(f"  Download directory: {cfg.download_dir}")
    console.print(f"  Verbose: {cfg.verbose}")
    console.print(f"  Quiet: {cfg.quiet}")

    # Torrent
    console.print("\n[cyan]Torrent:[/cyan]")
    console.print(f"  Seed ratio: {cfg.seed_ratio}")
    console.print(f"  Seed time: {cfg.seed_time} min")
    console.print(f"  Max connections: {cfg.max_connections}")
    console.print(f"  Port range: {cfg.listen_port_start}-{cfg.listen_port_end}")
    console.print(f"  DHT: {cfg.enable_dht}")
    console.print(f"  UPnP: {cfg.enable_upnp}")

    if cfg.download_rate_limit > 0:
        console.print(f"  Download limit: {cfg.download_rate_limit} KB/s")
    if cfg.upload_rate_limit > 0:
        console.print(f"  Upload limit: {cfg.upload_rate_limit} KB/s")

    console.print(
        "\n[dim]Configure via environment variables (ULD_*) or ~/.config/uld/config.toml[/dim]"
    )


# Allow running as `uld <url>` without subcommand
@app.command(name="", hidden=True)
def default_download(
    url: Annotated[str, typer.Argument(help="URL to download")],
) -> None:
    """Default command: download the given URL."""
    # Delegate to download command with defaults
    download(url=url)


def run() -> None:
    """Entry point for the CLI."""
    # Handle case where first arg looks like a URL (no subcommand)
    if len(sys.argv) > 1 and sys.argv[1] not in [
        "download",
        "info",
        "engines",
        "config",
        "--help",
        "-h",
        "--version",
        "-V",
    ]:
        # Looks like a URL, insert "download" subcommand
        first_arg = sys.argv[1]
        if (
            first_arg.startswith("magnet:")
            or first_arg.endswith(".torrent")
            or first_arg.startswith("http://")
            or first_arg.startswith("https://")
        ):
            sys.argv.insert(1, "download")

    app()


if __name__ == "__main__":
    run()
