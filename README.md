# touring-machine

Playlist generator for upcoming concerts.

`touring-machine` automates generating playlists for upcoming concerts and tours. It is designed with a streaming-agnostic core architecture, supporting **Tidal** as the primary streaming provider and **Setlist.fm** for concert data and setlist frequency analysis.

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

## Configuration & Usage

### 1. Check Service Status
Inspect authentication status for streaming services and concert providers:

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

### 3. Set your Setlist.fm API Key
Obtain a free Setlist.fm API key at [setlist.fm/settings/api](https://www.setlist.fm/settings/api).

Save it to configuration:
```bash
uv run touring-machine set-key setlistfm "YOUR_API_KEY"
```
Or export it as an environment variable:
```bash
export SETLISTFM_API_KEY="YOUR_API_KEY"
```

### 4. Generate Concert Playlists

#### Most Played Songs Strategy (Default)
Analyzes the artist's last $N$ concerts, counts song frequency, and generates a playlist sorted by most played:

```bash
# Generate playlist from last 5 shows (up to 25 songs)
uv run touring-machine generate "Radiohead"

# Analyze last 10 shows and limit to 20 songs
uv run touring-machine generate "Fontaines D.C." --shows 10 --limit 20
```

#### Latest Show Strategy
Replicates the exact setlist and performance order of the artist's most recent concert:

```bash
uv run touring-machine generate "The Smile" --strategy latest
```

#### Preview Without Creating (Dry Run)
Inspect the resolved tracks and match confidence without creating a playlist on Tidal:

```bash
uv run touring-machine generate "Arctic Monkeys" --dry-run
```

### 5. Create an Empty Playlist Manually
```bash
uv run touring-machine create-playlist "My Custom Playlist" --description "Optional description"
```

---

## Architecture Overview

Touring Machine follows a modular, decoupled architecture:

```text
┌────────────────────────────────────────────────────────┐
│                      CLI / UI                          │
│        (login, status, set-key, generate)              │
└──────────────────────────┬─────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────┐
│                 PlaylistGenerator                      │
│   Coordinates providers, strategies, and matchers      │
└──────────────┬──────────────────────────┬──────────────┘
               │                          │
┌──────────────▼──────────┐    ┌──────────▼──────────────┐
│    Streaming Provider   │    │    Concert Provider     │
│  • TidalService         │    │  • SetlistFmProvider    │
│  • Spotify (Future)     │    │  • Bandsintown (Future) │
└──────────────┬──────────┘    └──────────┬──────────────┘
               │                          │
┌──────────────▼──────────┐    ┌──────────▼──────────────┐
│      TrackMatcher       │    │    PlaylistStrategy     │
│ • Fuzzy Title/Artist    │    │ • MostPlayedStrategy    │
│ • Studio/Live Scoring   │    │ • LatestShowStrategy    │
└─────────────────────────┘    └─────────────────────────┘
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
