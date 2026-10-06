"""SQLite cache for normalized temperature forecasts."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from .models import ForecastRow

DEFAULT_DB_PATH = "data/weather.db"


def _connect(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


@contextmanager
def _connection(db_path: str = DEFAULT_DB_PATH) -> Iterator[sqlite3.Connection]:
    connection = _connect(db_path)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    with _connection(db_path) as connection:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS TemperatureForecasts (
                id INTEGER PRIMARY KEY,
                regionName TEXT NOT NULL,
                dataDate TEXT NOT NULL,
                mint REAL NOT NULL,
                maxt REAL NOT NULL,
                UNIQUE (regionName, dataDate)
            )"""
        )
        connection.execute(
            """CREATE TABLE IF NOT EXISTS AppMetadata (
                metadataKey TEXT PRIMARY KEY,
                metadataValue TEXT NOT NULL
            )"""
        )


def upsert_forecasts(rows: list[ForecastRow], db_path: str = DEFAULT_DB_PATH) -> int:
    if not rows:
        return 0
    init_db(db_path)
    with _connection(db_path) as connection:
        before = connection.total_changes
        connection.executemany(
            """INSERT INTO TemperatureForecasts
               (regionName, dataDate, mint, maxt) VALUES (?, ?, ?, ?)
               ON CONFLICT(regionName, dataDate) DO UPDATE SET
                 mint = excluded.mint, maxt = excluded.maxt""",
            [(row.regionName, row.dataDate, row.mint, row.maxt) for row in rows],
        )
        return connection.total_changes - before


def get_regions(db_path: str = DEFAULT_DB_PATH) -> list[str]:
    init_db(db_path)
    with _connection(db_path) as connection:
        result = connection.execute(
            "SELECT DISTINCT regionName FROM TemperatureForecasts ORDER BY regionName"
        ).fetchall()
    return [str(row["regionName"]) for row in result]


def get_forecasts(region_name: str, db_path: str = DEFAULT_DB_PATH) -> list[ForecastRow]:
    init_db(db_path)
    with _connection(db_path) as connection:
        result = connection.execute(
            """SELECT regionName, dataDate, mint, maxt FROM TemperatureForecasts
               WHERE regionName = ? ORDER BY dataDate""",
            (region_name,),
        ).fetchall()
    return [ForecastRow.from_mapping(dict(row)) for row in result]


def get_forecasts_for_date(
    data_date: str, db_path: str = DEFAULT_DB_PATH
) -> list[ForecastRow]:
    init_db(db_path)
    with _connection(db_path) as connection:
        result = connection.execute(
            """SELECT regionName, dataDate, mint, maxt FROM TemperatureForecasts
               WHERE dataDate = ? ORDER BY regionName""",
            (data_date,),
        ).fetchall()
    return [ForecastRow.from_mapping(dict(row)) for row in result]


def set_last_successful_refresh(
    refreshed_at: datetime | None = None, db_path: str = DEFAULT_DB_PATH
) -> str:
    timestamp = (refreshed_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    value = timestamp.isoformat(timespec="seconds")
    with _connection(db_path) as connection:
        connection.execute(
            """INSERT INTO AppMetadata (metadataKey, metadataValue)
               VALUES ('last_successful_refresh', ?)
               ON CONFLICT(metadataKey) DO UPDATE SET metadataValue = excluded.metadataValue""",
            (value,),
        )
    return value


def get_last_successful_refresh(db_path: str = DEFAULT_DB_PATH) -> str | None:
    init_db(db_path)
    with _connect(db_path) as connection:
        row = connection.execute(
            "SELECT metadataValue FROM AppMetadata WHERE metadataKey = ?",
            ("last_successful_refresh",),
        ).fetchone()
    return str(row["metadataValue"]) if row else None
