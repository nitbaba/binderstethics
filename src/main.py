from __future__ import annotations

import logging
import sys

import flet as ft

from src.config import config
from src.gui import build_app
from src.utils import setup_logging


def main() -> int:
    setup_logging(config.app.log_level)
    logger = logging.getLogger(__name__)
    logger.info("Starting %s", config.app.name)

    try:
        ft.app(target=build_app, view=ft.AppView.FLET_APP)
    except Exception:
        logger.exception("Unhandled exception — application will exit.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
