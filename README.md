# BinderStethics
A app to visualize TCG binders, great for planning out your favorite aesthetic.

Shouts my gf for the idea.



A desktop Pokémon TCG virtual binder app built with [Flet](https://flet.dev).  
Search cards via the official Pokémon TCG API, drag them into book-style binders, and save your collection to a local SQLite database.

## Features

- **Card search** — search by name and/or set name (AND condition), paginated at 50 results
- **Large preview** — click any result card to see a full preview in the right panel
- **Drag and drop** — drag cards from search results into binder slots; drag slots to swap
- **Book-style binder** — spreads show two facing pages like a real binder, with front and back covers
- **Binder types** — 4-pocket (20 pages), 9-pocket (20 pages), 12-pocket (20 pages), 16-pocket (34 pages)
- **Zoom and pan** — scroll wheel to zoom, click-drag to pan within a spread
- **Arrow key navigation** — left/right arrows turn pages
- **Persistent storage** — binders and slots saved to SQLite; auto-saves on close and binder switch
- **Display presets** — HD, FHD, 2K, 4K, and Fullscreen; all UI elements scale accordingly
- **Responsive layout** — manual window resize snaps to the nearest preset

## Project structure

```
binderstethics/
│
├── src/
│   ├── main.py                        # Entry point — calls ft.run()
│   ├── config.py                      # Typed settings loaded from .env
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   └── pokemon_tcg.py             # Async httpx client for api.pokemontcg.io/v2
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── models.py                  # Card, Binder, BinderSlot, Preset dataclasses
│   │   └── database.py                # SQLite persistence (binders, slots, settings)
│   │
│   ├── gui/
│   │   ├── __init__.py
│   │   ├── app.py                     # Root build_app(): shell, preset, rebuild cycle
│   │   ├── colors.py                  # COLORS dict — edit here to retheme everything
│   │   ├── state.py                   # AppState: shared mutable state + listeners
│   │   ├── sidebar.py                 # Binder list grouped by type + settings nav
│   │   └── views/
│   │       ├── __init__.py
│   │       ├── search_view.py         # Search bar, results grid, preview panel
│   │       ├── binder_view.py         # Book spread, slots, drag/drop, zoom/pan
│   │       └── settings_view.py       # Display preset selector
│   │
│   └── utils/
│       ├── __init__.py
│       └── logger.py                  # setup_logging() — call once at startup
│
├── data/
│   └── binders.db                     # SQLite database (auto-created on first run)
│
├── tests/
│   ├── unit/
│   │   └── test_scraper.py
│   └── integration/
│       └── test_config.py
│
├── .github/workflows/ci.yml           # Lint → typecheck → test
├── .env.example                       # All supported env vars with defaults
├── .gitignore
├── Makefile                           # Dev shortcuts
├── pyproject.toml                     # Dependencies + tool config
└── README.md
```

## Quick start

```bash
# 1. Clone and enter the repo
git clone <repo-url> && cd binderstethics

# 2. Create venv and install deps
make install-dev

# 3. Copy and fill in env vars
cp .env.example .env
$EDITOR .env  # add your POKEMON_TCG_API_KEY

# 4. Run
make run
```

Get a free Pokémon TCG API key at [dev.pokemontcg.io](https://dev.pokemontcg.io).

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `APP_NAME` | `BindersEthics` | Window title |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `POKEMON_TCG_API_KEY` | *(required)* | API key from dev.pokemontcg.io |
| `DB_PATH` | `data/binders.db` | SQLite database path |
| `GUI_WINDOW_WIDTH` | `1920` | Initial window width |
| `GUI_WINDOW_HEIGHT` | `1080` | Initial window height |

## Workflow

| Command | Action |
|---|---|
| `make run` | Launch the app |
| `make test` | Run tests with coverage |
| `make lint` | Ruff lint check |
| `make format` | Auto-format source |
| `make typecheck` | mypy static analysis |
| `make clean` | Remove build/cache artefacts |

## How the binder works

Each binder type has a fixed number of physical pages. Each physical page has a front (side 0) and back (side 1). The view shows a **spread** — two facing pages like an open book:

| Spread | Left page | Right page |
|---|---|---|
| 0 | Front Cover | Page 1 Front |
| 1 | Page 1 Back | Page 2 Front |
| ... | ... | ... |
| N | Page N Back | Back Cover |

Total spreads = physical pages + 1 (including both covers).

| Binder type | Pockets/side | Physical pages | Total slots |
|---|---|---|---|
| 4-pocket | 4 | 20 | 160 |
| 9-pocket | 9 | 20 | 360 |
| 12-pocket | 12 | 20 | 480 |
| 16-pocket | 16 | 34 | 1088 |

## Theming

Edit `COLORS` in `src/gui/colors.py`. Every color in the app references this dict.

## Display presets

Change preset in Settings (sidebar → Settings button). The window resizes and all UI elements scale. Manual window resizes snap to the nearest preset without persisting the change.

| Preset | Resolution | Scale |
|---|---|---|
| HD | 1280×720 | 0.75× |
| FHD | 1920×1080 | 1.0× |
| 2K | 2560×1440 | 1.25× |
| 4K | 3840×2160 | 1.5× |
| Fullscreen | — | 1.0× |

## Adding a new binder size

1. Add an entry to `BinderSize` enum in `src/db/models.py`
2. Add its page count to `PAGES_BY_SIZE`
3. Add a label to `_SIZE_LABELS` in `src/gui/sidebar.py`
4. Add the column layout to `_cols()` in `src/gui/views/binder_view.py`