"""Small shared presentation helpers for both maps."""

from .models import ForecastRow
from .regions import REGION_COORDINATES


def temperature_color(value: float) -> str:
    if value < 20:
        return "#1976d2"
    if value < 25:
        return "#16a765"
    if value <= 30:
        return "#f4cf24"
    return "#e85935"


def build_map_rows(rows: list[ForecastRow], data_date: str) -> list[dict[str, object]]:
    points: list[dict[str, object]] = []
    for row in rows:
        if row.dataDate != data_date or row.regionName not in REGION_COORDINATES:
            continue
        latitude, longitude = REGION_COORDINATES[row.regionName]
        points.append(
            {
                **row.to_dict(),
                "latitude": latitude,
                "longitude": longitude,
                "color": temperature_color((row.mint + row.maxt) / 2),
            }
        )
    return points
