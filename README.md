# binderstethics
A app to visualize TCG binders, great for planning out your favorite aesthetic.

Shouts my gf for the idea.

# MyApp

Desktop GUI application with web scraping, built with [Flet](https://flet.dev).

## Quick start

```bash
make install-dev   # create .venv, install deps, copy .env.example → .env
make run           # launch the window
```

## Project structure

```
myapp/
│
├── src/                        # All application code
│   ├── main.py                 # Entry point — calls ft.app()
│   ├── config.py               # Typed settings loaded from .env
│   │
│   ├── gui/
│   │   ├── __init__.py
│   │   └── app.py              # Flet window, COLORS theme tokens, view builders
│   │
│   ├── scraper/
│   │   ├── __init__.py
│   │   └── scraper.py          # Async httpx client + BeautifulSoup parser
│   │
│   └── utils/
│       ├── __init__.py
│       └── logger.py           # setup_logging() — call once at startup
│
├── tests/
│   ├── unit/
│   │   └── test_scraper.py     # Scraper tests with mocked HTTP (respx)
│   └── integration/
│       └── test_config.py      # Config smoke tests
│
├── .github/workflows/ci.yml    # Lint → typecheck → test matrix
├── .env.example                # All supported env vars with defaults
├── .gitignore
├── Makefile                    # Dev shortcuts (run / test / lint / format)
├── pyproject.toml              # Dependencies + ruff / mypy / pytest config
└── README.md
```

## Adding a page

1. Write `build_<name>_view(page: ft.Page) -> ft.Control` in `src/gui/app.py`
2. Add `("Label", ft.icons.ICON, ft.icons.ICON_SELECTED)` to `NAV_ITEMS`
3. Append `build_<name>_view(page)` to the `views` list inside `build_app`

## Theming

Edit `COLORS` at the top of `src/gui/app.py`. Every color in the UI references this dict.

## Workflow

| Command          | Action                          |
|------------------|---------------------------------|
| `make run`       | Launch desktop window           |
| `make test`      | Run tests with coverage         |
| `make lint`      | Ruff lint check                 |
| `make format`    | Auto-format source              |
| `make typecheck` | mypy static analysis            |
| `make clean`     | Remove build / cache artefacts  |

## Environment variables

All variables are optional — defaults are defined in `config.py`.

| Variable                  | Default               | Description              |
|---------------------------|-----------------------|--------------------------|
| `APP_NAME`                | `MyApp`               | Window title             |
| `LOG_LEVEL`               | `INFO`                | Logging verbosity        |
| `SCRAPER_BASE_URL`        | `https://example.com` | Default scrape target    |
| `SCRAPER_REQUEST_TIMEOUT` | `10`                  | HTTP timeout (seconds)   |
| `SCRAPER_RATE_LIMIT_DELAY`| `1.0`                 | Pause between requests   |
| `GUI_WINDOW_WIDTH`        | `1100`                | Initial window width     |
| `GUI_WINDOW_HEIGHT`       | `720`                 | Initial window height    |
