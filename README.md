# ULD - Unified Local Downloader

A single CLI tool for downloading content from multiple sources: torrents, magnet links, video platforms, and direct URLs.

[![CI](https://github.com/sheikjaveed/uld/actions/workflows/ci.yml/badge.svg)](https://github.com/sheikjaveed/uld/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Why ULD?

Today, downloading content requires juggling multiple tools:

- Torrent clients for torrents/magnet links
- `yt-dlp` for YouTube/videos
- `wget`/`curl`/`aria2` for direct files

Each has different CLI syntax, progress formats, and configuration. ULD provides:

- **Single interface** - One command for all download types
- **Auto-detection** - Automatically routes to the right engine
- **Unified progress** - Consistent progress display across all downloads
- **Local-first** - Runs entirely on your machine, no cloud dependencies

## Installation

```bash
# Using pip
pip install "uld[torrent]"

# Using uv (recommended)
uv add "uld[torrent]"

# With all engines (torrent + video + http)
pip install "uld[all]"
```

## Quick Start

```bash
# Download a torrent
uld download magnet:?xt=urn:btih:...

# Or just pass the URL directly
uld magnet:?xt=urn:btih:...

# Download a .torrent file
uld download ./ubuntu-24.04.torrent

# Specify output directory
uld download magnet:... -o ~/Downloads/torrents

# Download without seeding
uld download magnet:... --no-seed

# Get torrent info without downloading
uld info magnet:?xt=urn:btih:...
```

## Commands

### `uld download <url>`

Download content from a URL, magnet link, or torrent file.

```bash
uld download <url> [OPTIONS]

Options:
  -o, --output PATH      Output directory
  -r, --seed-ratio FLOAT Seed ratio target (default: 1.0)
  --no-seed              Don't seed after download
  -q, --quiet            Minimal output
  -v, --verbose          Verbose output
```

### `uld info <url>`

Show metadata without downloading.

```bash
uld info magnet:?xt=urn:btih:...
```

### `uld engines`

List available download engines and their status.

```bash
uld engines
```

### `uld config`

Show current configuration.

```bash
uld config
```

## Configuration

Configure via environment variables (prefixed with `ULD_`):

```bash
# Set default download directory
export ULD_DOWNLOAD_DIR=~/Downloads/uld

# Set default seed ratio
export ULD_SEED_RATIO=2.0

# Disable seeding by default
export ULD_SEED_RATIO=0

# Set rate limits (KB/s)
export ULD_DOWNLOAD_RATE_LIMIT=1000
export ULD_UPLOAD_RATE_LIMIT=500
```

### Available Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `ULD_DOWNLOAD_DIR` | `~/Downloads` | Default download directory |
| `ULD_SEED_RATIO` | `1.0` | Default seed ratio (0 = no seeding) |
| `ULD_SEED_TIME` | `0` | Seed time in minutes (0 = use ratio) |
| `ULD_MAX_CONNECTIONS` | `200` | Maximum peer connections |
| `ULD_LISTEN_PORT_START` | `6881` | Start of port range |
| `ULD_LISTEN_PORT_END` | `6891` | End of port range |
| `ULD_ENABLE_DHT` | `true` | Enable DHT |
| `ULD_ENABLE_UPNP` | `true` | Enable UPnP |

## Supported Sources

### v0.1.0 (Current)

- Magnet links (`magnet:?xt=urn:btih:...`)
- Torrent files (`.torrent`)

### Coming Soon (v0.2+)

- YouTube and video platforms (via `yt-dlp`)
- Direct HTTP/HTTPS downloads
- More sources based on feedback

## Development

```bash
# Clone the repository
git clone https://github.com/sheikjaveed/uld.git
cd uld

# Install with uv (recommended)
uv sync --all-extras

# Or with pip
pip install -e ".[dev,torrent]"

# Run tests
uv run pytest
# or: make test

# Run linter
uv run ruff check src tests
# or: make lint

# Format code
uv run ruff format src tests
# or: make format

# Type check
uv run mypy src
# or: make typecheck
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- [libtorrent](https://libtorrent.org/) - Torrent engine
- [Rich](https://rich.readthedocs.io/) - Beautiful terminal output
- [Typer](https://typer.tiangolo.com/) - CLI framework
- [Pydantic](https://pydantic.dev/) - Data validation
