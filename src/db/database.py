from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from typing import Optional

from src.db.models import (
    Binder, BinderSize, Card, BinderSlot, CardSource,
    Preset, PRESET_BY_KEY, DEFAULT_PRESET,
)

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS binders (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT    NOT NULL,
    size    INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS slots (
    binder_id   INTEGER NOT NULL REFERENCES binders(id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL,
    side        INTEGER NOT NULL,
    position    INTEGER NOT NULL,
    card_json   TEXT,
    PRIMARY KEY (binder_id, page_number, side, position)
);

CREATE TABLE IF NOT EXISTS settings (
    key     TEXT PRIMARY KEY,
    value   TEXT NOT NULL
);
"""


class Database:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()
        logger.info("Database opened at %s", path)

    def close(self) -> None:
        self._conn.close()

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def get_setting(self, key: str, default: str = "") -> str:
        row = self._conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        self._conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?)"
            " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        self._conn.commit()

    def get_preset(self) -> Preset:
        key = self.get_setting("preset_key", DEFAULT_PRESET.key)
        return PRESET_BY_KEY.get(key, DEFAULT_PRESET)

    def save_preset(self, preset: Preset) -> None:
        self.set_setting("preset_key", preset.key)
        logger.info("Saved preset: %s", preset.key)

    # ------------------------------------------------------------------
    # Binders
    # ------------------------------------------------------------------

    def list_binders(self) -> list[Binder]:
        rows = self._conn.execute(
            "SELECT id, name, size FROM binders ORDER BY id"
        ).fetchall()
        return [self._load_binder(row["id"], row["name"], row["size"]) for row in rows]

    def create_binder(self, name: str, size: BinderSize) -> Binder:
        cur = self._conn.execute(
            "INSERT INTO binders (name, size) VALUES (?, ?)", (name, size.value)
        )
        self._conn.commit()
        binder_id = cur.lastrowid
        assert binder_id is not None
        logger.info("Created binder id=%d name=%r size=%d", binder_id, name, size.value)
        return Binder(id=binder_id, name=name, size=size)

    def rename_binder(self, binder_id: int, new_name: str) -> None:
        self._conn.execute(
            "UPDATE binders SET name = ? WHERE id = ?", (new_name, binder_id)
        )
        self._conn.commit()

    def delete_binder(self, binder_id: int) -> None:
        self._conn.execute("DELETE FROM binders WHERE id = ?", (binder_id,))
        self._conn.commit()
        logger.info("Deleted binder id=%d", binder_id)

    def save_binder(self, binder: Binder) -> None:
        with self._conn:
            self._conn.execute(
                "DELETE FROM slots WHERE binder_id = ?", (binder.id,)
            )
            for slot in binder.slots.values():
                if slot.card is not None:
                    self._conn.execute(
                        """
                        INSERT INTO slots
                            (binder_id, page_number, side, position, card_json)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            binder.id,
                            slot.page_number,
                            slot.side,
                            slot.position,
                            _card_to_json(slot.card),
                        ),
                    )
        logger.info(
            "Saved binder id=%d (%d filled slots)", binder.id, len(binder.slots)
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_binder(self, binder_id: int, name: str, size_value: int) -> Binder:
        size = BinderSize(size_value)
        binder = Binder(id=binder_id, name=name, size=size)
        rows = self._conn.execute(
            """
            SELECT page_number, side, position, card_json
            FROM slots WHERE binder_id = ?
            """,
            (binder_id,),
        ).fetchall()
        for row in rows:
            card = _card_from_json(row["card_json"]) if row["card_json"] else None
            key = (row["page_number"], row["side"], row["position"])
            binder.slots[key] = BinderSlot(
                page_number=row["page_number"],
                side=row["side"],
                position=row["position"],
                card=card,
            )
        return binder


def _card_to_json(card: Card) -> str:
    return json.dumps({
        "api_id": card.api_id,
        "name": card.name,
        "set_name": card.set_name,
        "set_id": card.set_id,
        "number": card.number,
        "image_small": card.image_small,
        "image_large": card.image_large,
        "source": card.source.value,
    })


def _card_from_json(raw: str) -> Card:
    data = json.loads(raw)
    return Card(
        api_id=data["api_id"],
        name=data["name"],
        set_name=data["set_name"],
        set_id=data["set_id"],
        number=data["number"],
        image_small=data["image_small"],
        image_large=data["image_large"],
        source=CardSource(data.get("source", "pokemon")),
    )