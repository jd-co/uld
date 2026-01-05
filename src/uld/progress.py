"""Progress display using Rich for ULD."""

from typing import Any

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from rich.table import Table

from uld.models import DownloadProgress, DownloadResult, TorrentInfo, VideoInfo


class ProgressDisplay:
    """Unified progress display for all download engines."""

    def __init__(self, console: Console | None = None, quiet: bool = False) -> None:
        """Initialize the progress display.

        Args:
            console: Rich console instance.
            quiet: If True, suppress output.
        """
        self.console = console or Console()
        self.quiet = quiet
        self._progress: Progress | None = None
        self._live: Live | None = None
        self._task_id: TaskID | None = None
        self._current_state: str = ""
        # Playlist tracking
        self._current_playlist_index: int | None = None
        self._last_video_title: str | None = None
        self._last_video_size: int = 0

    def create_progress(self) -> Progress:
        """Create a Rich progress bar with download columns."""
        return Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=40),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            console=self.console,
            transient=True,
        )

    def start(self, description: str = "Downloading", total: int = 0) -> None:
        """Start the progress display.

        Args:
            description: Task description.
            total: Total size in bytes.
        """
        if self.quiet:
            return

        self._progress = self.create_progress()
        self._task_id = self._progress.add_task(description, total=total or 100)
        self._live = Live(self._progress, console=self.console, refresh_per_second=4)
        self._live.start()

    def stop(self) -> None:
        """Stop the progress display."""
        # Print last playlist video if applicable
        if (
            self._current_playlist_index is not None
            and self._last_video_title
            and self._live
        ):
            self._live.stop()
            self._live = None
            # Use playlist_count from last known value (approximate with index)
            self.console.print(
                f"[green]✓[/green] [{self._current_playlist_index}] {self._last_video_title[:50]} "
                f"[dim]{_format_size(self._last_video_size)}[/dim]"
            )

        if self._live:
            self._live.stop()
            self._live = None
        self._progress = None
        self._task_id = None
        # Reset playlist tracking
        self._current_playlist_index = None
        self._last_video_title = None
        self._last_video_size = 0

    def update(self, progress: DownloadProgress) -> None:
        """Update the progress display.

        Args:
            progress: Current download progress.
        """
        if self.quiet or self._progress is None or self._task_id is None:
            return

        # Check if playlist video changed - print completed video
        if progress.playlist_index and progress.playlist_count:
            if (
                self._current_playlist_index is not None
                and progress.playlist_index > self._current_playlist_index
                and self._last_video_title
            ):
                # Previous video completed - print it
                self._print_completed_video(
                    self._current_playlist_index,
                    progress.playlist_count,
                    self._last_video_title,
                    self._last_video_size,
                )
                # Reset progress bar for new video
                self._progress.reset(self._task_id)

            # Track current video
            self._current_playlist_index = progress.playlist_index
            self._last_video_title = progress.video_title
            self._last_video_size = progress.total

        # Build description based on state and playlist info
        state = progress.state
        description = "Downloading"

        if state == "fetching_metadata":
            peers = progress.peers or 0
            speed = progress.speed_human if progress.speed > 0 else "0 B/s"
            description = f"Fetching metadata ({peers} peers, {speed})"
        elif state == "seeding":
            description = "Seeding"
        elif state == "downloading":
            # Show playlist progress if available
            if progress.playlist_index and progress.playlist_count:
                title = progress.video_title or "Video"
                # Truncate long titles
                if len(title) > 40:
                    title = title[:37] + "..."
                description = (
                    f"[{progress.playlist_index}/{progress.playlist_count}] {title}"
                )
            else:
                description = "Downloading"

        # Always update description (for playlist, title changes per video)
        self._progress.update(self._task_id, description=description)
        self._current_state = state

        # Update progress values
        if progress.total > 0:
            self._progress.update(
                self._task_id,
                completed=progress.downloaded,
                total=progress.total,
            )
        else:
            # Unknown total, use percentage
            self._progress.update(self._task_id, completed=progress.percentage)

    def _print_completed_video(
        self, index: int, total: int, title: str, size: int
    ) -> None:
        """Print a completed video line above the progress bar."""
        if self._live:
            self._live.stop()

        # Truncate title if needed
        if len(title) > 50:
            title = title[:47] + "..."

        size_str = _format_size(size) if size > 0 else ""
        self.console.print(
            f"[green]✓[/green] [{index}/{total}] {title} [dim]{size_str}[/dim]"
        )

        if self._live and self._progress:
            self._live = Live(
                self._progress, console=self.console, refresh_per_second=4
            )
            self._live.start()

    def show_metadata(self, info: TorrentInfo) -> None:
        """Display torrent metadata.

        Args:
            info: Torrent information.
        """
        if self.quiet:
            return

        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Key", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Name", info.name)
        table.add_row("Size", info.total_size_human)
        table.add_row("Files", str(info.num_files))
        if info.comment:
            table.add_row("Comment", info.comment)

        panel = Panel(table, title="Torrent Info", border_style="blue")
        self.console.print(panel)

    def show_video_metadata(self, info: VideoInfo) -> None:
        """Display video metadata.

        Args:
            info: Video information.
        """
        if self.quiet:
            return

        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Key", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Title", info.title)
        table.add_row("Duration", info.duration_human)
        if info.uploader:
            table.add_row("Uploader", info.uploader)
        if info.view_count:
            table.add_row("Views", f"{info.view_count:,}")
        if info.formats:
            table.add_row("Qualities", ", ".join(info.formats))
        if info.description:
            desc = (
                info.description[:100] + "..."
                if len(info.description) > 100
                else info.description
            )
            table.add_row("Description", desc)

        panel = Panel(table, title="Video Info", border_style="magenta")
        self.console.print(panel)

    def show_complete(self, result: DownloadResult) -> None:
        """Display download completion message.

        Args:
            result: Download result.
        """
        if self.quiet:
            return

        if result.success:
            self.console.print()
            self.console.print(
                f"[green]Download complete![/green] Saved to: {result.file_path}"
            )

            # Show stats
            stats = []
            if result.total_downloaded > 0:
                stats.append(f"Downloaded: {_format_size(result.total_downloaded)}")
            if result.total_uploaded > 0:
                stats.append(f"Uploaded: {_format_size(result.total_uploaded)}")
            if result.duration > 0:
                stats.append(f"Duration: {_format_duration(result.duration)}")
            if result.avg_speed > 0:
                stats.append(f"Avg speed: {_format_size(result.avg_speed)}/s")

            if stats:
                self.console.print(f"[dim]{' | '.join(stats)}[/dim]")
        else:
            self.console.print()
            self.console.print(f"[red]Download failed:[/red] {result.error}")

    def show_error(self, error: Exception) -> None:
        """Display an error message.

        Args:
            error: Exception to display.
        """
        self.console.print(f"[red]Error:[/red] {error}")

    def show_engines(self, engines: list[Any]) -> None:
        """Display available engines status.

        Args:
            engines: List of EngineStatus objects.
        """
        table = Table(title="Available Engines", show_header=True)
        table.add_column("Engine", style="cyan")
        table.add_column("Status", style="white")
        table.add_column("Version", style="dim")
        table.add_column("Install", style="yellow")

        for engine in engines:
            status = (
                "[green]Available[/green]"
                if engine.available
                else "[red]Not installed[/red]"
            )
            version = engine.version or "-"
            install = engine.install_hint or "-"
            table.add_row(engine.name, status, version, install)

        self.console.print(table)

    def print(self, message: str, style: str | None = None) -> None:
        """Print a message to console.

        Args:
            message: Message to print.
            style: Optional Rich style.
        """
        if not self.quiet:
            if style:
                self.console.print(f"[{style}]{message}[/{style}]")
            else:
                self.console.print(message)

    def print_status(self, progress: DownloadProgress) -> None:
        """Print a single-line status update (for non-interactive mode).

        Args:
            progress: Current download progress.
        """
        if self.quiet:
            return

        parts = [
            f"{progress.percentage:.1f}%",
            f"{progress.downloaded_human}/{progress.total_human}",
            f"{progress.speed_human}",
        ]

        if progress.peers > 0 or progress.seeds > 0:
            parts.append(f"Peers: {progress.peers} Seeds: {progress.seeds}")

        if progress.eta:
            parts.append(f"ETA: {_format_duration(progress.eta)}")

        self.console.print(" | ".join(parts), end="\r")


def _format_size(size_bytes: int | float) -> str:
    """Format bytes to human-readable string."""
    if size_bytes == 0:
        return "0 B"

    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    size = float(size_bytes)

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    return f"{size:.2f} {units[unit_index]}"


def _format_duration(seconds: int | float) -> str:
    """Format seconds to human-readable duration."""
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        mins = seconds // 60
        secs = seconds % 60
        return f"{mins}m {secs}s"
    else:
        hours = seconds // 3600
        mins = (seconds % 3600) // 60
        return f"{hours}h {mins}m"
