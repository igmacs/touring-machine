# touring-machine

Playlist generator for upcoming concerts.

`touring-machine` automates generating playlists for upcoming concerts and tours. It is designed with a streaming-agnostic core architecture, supporting **Tidal** first, with upcoming support for Setlist.fm-driven track generation and other streaming providers (e.g. Spotify).

---

## Requirements & Tooling

- **Python 3.11+**
- **[uv](https://github.com/astral-sh/uv)** (recommended package manager) or standard `pip` / `venv`
- **[Ruff](https://astral.sh/ruff)** for fast linting and formatting

---

## Installation & Setup

Clone the repository and install dependencies with `uv`:

```bash
# Clone repository
git clone https://github.com/igmacs/touring-machine.git
cd touring-machine

# Install dependencies and sync virtual environment
uv sync
```

---

## Usage

### 1. Check Service Status
Inspect authentication status and session file locations:

```bash
uv run touring-machine status
```

### 2. Log in with Tidal
Authenticate using Tidal's OAuth device flow:

```bash
uv run touring-machine login
```
This prints an authorization link (e.g. `https://link.tidal.com/...`). Open the link in your browser, approve access, and the terminal will securely cache your session tokens in `~/.config/touring-machine/tidal_session.json` (chmod `0600`).

To re-authenticate or switch accounts:
```bash
uv run touring-machine login --force
```

### 3. Create a Playlist
Create an empty playlist on Tidal:

```bash
uv run touring-machine create-playlist "Radiohead Tour 2026" --description "Warmup playlist"
```

---

## Development & Testing

### Run Tests
```bash
uv run pytest
```

### Run Linter & Formatter
```bash
uv run ruff check .
uv run ruff format --check .
```

---

## Architecture Overview

```text
┌────────────────────────────────────────────────────────┐
│                      CLI / UI                          │
│     (touring_machine.cli: login, create-playlist, ...) │
└──────────────────────────┬─────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────┐
│                     Core Engine                        │
│   - Domain Models: Track, Playlist                     │
│   - Service Factory: get_streaming_service             │
└──────────────┬──────────────────────────┬──────────────┘
               │                          │
┌──────────────▼──────────┐    ┌──────────▼──────────────┐
│     StreamingService    │    │    Concert Provider     │
│        (Interface)      │    │     (Coming Soon)       │
├─────────────────────────┤    ├─────────────────────────┤
│ • TidalService (Active) │    │ • SetlistFmService      │
│ • SpotifyService (Future│    │                         │
└─────────────────────────┘    └─────────────────────────┘
```
