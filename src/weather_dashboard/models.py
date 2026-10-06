"""Data types shared by the dashboard applications."""

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class ForecastRow:
    regionName: str
    dataDate: str
    mint: float
    maxt: float

    def to_dict(self) -> dict[str, str | float]:
        return asdict(self)

    @classmethod
    def from_mapping(cls, row: dict[str, object]) -> "ForecastRow":
        return cls(
            regionName=str(row["regionName"]),
            dataDate=str(row["dataDate"]),
            mint=float(row["mint"]),
            maxt=float(row["maxt"]),
        )
