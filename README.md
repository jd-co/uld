# ULD - Unified Local Downloader

A single CLI tool for downloading content from multiple sources: torrents, magnet links, video platforms, and direct URLs.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PyPI](https://img.shields.io/pypi/v/uld-cli.svg)](https://pypi.org/project/uld-cli/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Why ULD?

Stop juggling multiple tools for different download types:

| Before | After |
|--------|-------|
| `qbittorrent` for torrents | Just use `uld` |
| `yt-dlp` for videos | Just use `uld` |
| `wget`/`curl` for files | Just use `uld` |

ULD auto-detects the URL type and uses the right engine automatically.

---

## Installation

```bash
pip install uld-cli
```

That's it! Both video (yt-dlp) and torrent (libtorrent) support are included.

**Using uv (faster):**
```bash
uv add uld-cli
```

---

## Quick Start

### Step 1: Download anything

```bash
# YouTube video
uld "https://youtube.com/watch?v=dQw4w9WgXcQ"

# Magnet link
uld "magnet:?xt=urn:btih:..."

# Torrent file
uld ./ubuntu-24.04.torrent
```

### Step 2: Watch the progress

```
Press q or Ctrl+C to stop or exit
⠋ Downloading [████████████░░░░░░░░] 60% 125.0 MB 5.2 MB/s 0:02:30
```

### Step 3: Done!

```
✓ Download complete! Saved to: ~/Downloads/video.mp4
Downloaded: 208.5 MB | Duration: 1m 23s | Avg speed: 2.5 MB/s
```

---

## Usage Examples

### Videos

```bash
# Best quality (default)
uld "https://youtube.com/watch?v=..."

# Specific quality
uld "https://youtube.com/watch?v=..." -Q 720p

# Download entire playlist
uld "https://youtube.com/playlist?list=..."

# Just get info (no download)
uld info "https://youtube.com/watch?v=..."
```

**Playlist Progress:**
```
✓ [1/5] First Video Title 45.2 MB
✓ [2/5] Second Video Title 32.1 MB
⠋ [3/5] Third Video Title [████████░░░░] 45% 5.2 MB/s
```

> **Resume Support:** If you stop a playlist download (q or Ctrl+C) and run the same command again, it automatically skips already downloaded videos and continues from where it left off.

### Torrents

```bash
# Magnet link
uld "magnet:?xt=urn:btih:..."

# Torrent file
uld ./file.torrent

# Download without seeding
uld "magnet:..." --no-seed

# Custom seed ratio
uld "magnet:..." --seed-ratio 2.0

# Just get torrent info
uld info "magnet:?xt=urn:btih:..."
```

### Output Options

```bash
# Custom output directory
uld "https://youtube.com/watch?v=..." -o ~/Videos

# Quiet mode (errors only)
uld "magnet:..." -q

# Verbose mode (debug info)
uld "magnet:..." -v
```

---

## Commands Reference

| Command | Description |
|---------|-------------|
| `uld <url>` | Download from URL (auto-detects type) |
| `uld download <url>` | Same as above (explicit) |
| `uld info <url>` | Show metadata without downloading |
| `uld engines` | List available engines and status |
| `uld config` | Show current configuration |
| `uld --help` | Show help |

### Download Options

| Option | Short | Description |
|--------|-------|-------------|
| `--output` | `-o` | Output directory |
| `--quality` | `-Q` | Video quality (best, 1080p, 720p, 480p, 360p, worst) |
| `--playlist` | `-P` | Force playlist download |
| `--seed-ratio` | `-r` | Torrent seed ratio (default: 1.0) |
| `--no-seed` | | Don't seed after torrent download |
| `--quiet` | `-q` | Minimal output |
| `--verbose` | `-v` | Verbose output |

---

## Controls

While downloading, you can:

| Key | Action |
|-----|--------|
| `q` | Stop download and exit |
| `Ctrl+C` | Stop download and exit |

---

## Configuration

Set defaults via environment variables:

```bash
# Default download directory
export ULD_DOWNLOAD_DIR=~/Downloads/uld

# Default seed ratio (0 = no seeding)
export ULD_SEED_RATIO=1.0

# Rate limits in KB/s
export ULD_DOWNLOAD_RATE_LIMIT=1000
export ULD_UPLOAD_RATE_LIMIT=500
```

### All Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `ULD_DOWNLOAD_DIR` | `~/Downloads` | Default download directory |
| `ULD_SEED_RATIO` | `1.0` | Seed ratio (0 = no seeding) |
| `ULD_SEED_TIME` | `0` | Seed time in minutes |
| `ULD_MAX_CONNECTIONS` | `200` | Max peer connections |
| `ULD_DOWNLOAD_RATE_LIMIT` | `0` | Download limit KB/s (0 = unlimited) |
| `ULD_UPLOAD_RATE_LIMIT` | `0` | Upload limit KB/s (0 = unlimited) |
| `ULD_ENABLE_DHT` | `true` | Enable DHT for torrents |
| `ULD_ENABLE_UPNP` | `true` | Enable UPnP |

---

## Supported Platforms

### Video Sites (1000+ supported)
- YouTube (videos & playlists)
- Vimeo
- Twitter/X
- Reddit
- Instagram
- TikTok
- Twitch
- And many more... (powered by yt-dlp)

### Torrent
- Magnet links
- .torrent files (local or HTTP URLs)

---

## Development

```bash
# Clone
git clone https://github.com/jd-co/uld.git
cd uld

# Install with dev dependencies
uv sync --all-extras

# Run tests
uv run pytest

# Run linter
uv run ruff check src tests

# Format code
uv run ruff format src tests
```

---

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

Built with these amazing projects:
- [libtorrent](https://libtorrent.org/) - Torrent engine
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - Video engine
- [Rich](https://rich.readthedocs.io/) - Terminal UI
- [Typer](https://typer.tiangolo.com/) - CLI framework
- [Pydantic](https://pydantic.dev/) - Data validation
