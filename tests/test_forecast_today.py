"""Keep the current Taiwan date when CWA has already ended the morning period."""

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from weather_dashboard.cwa import REGION_COUNTIES, parse_forecast
from weather_dashboard.towns import parse_towns


def forecast_location(name, today):
    times = {"最低溫度": [], "最高溫度": []}
    for offset in range(7):
        day = today + timedelta(days=offset)
        for hour in ((12, 18) if offset == 0 else (6, 18)):
            start = datetime(day.year, day.month, day.day, hour, tzinfo=timezone(timedelta(hours=8)))
            end = start + timedelta(hours=6 if hour == 12 else 12)
            low, high = (29, 33) if hour == 12 else (25, 29) if offset == 0 else (24, 28) if hour == 18 else (25, 32)
            for label, field, value in (("最低溫度", "MinTemperature", low), ("最高溫度", "MaxTemperature", high)):
                times[label].append({"StartTime": start.isoformat(), "EndTime": end.isoformat(),
                                     "ElementValue": [{field: str(value)}]})
    return {"LocationName": name, "Latitude": "24.15", "Longitude": "120.68",
            "WeatherElement": [{"ElementName": label, "Time": items} for label, items in times.items()]}


class CurrentDayForecastTests(unittest.TestCase):
    def setUp(self):
        self.today = datetime.now(timezone(timedelta(hours=8))).date()

    def test_regional_forecast_includes_today_and_six_following_days(self):
        counties = [county for region in REGION_COUNTIES.values() for county in region]
        payload = {"records": {"Locations": [{"LocationsName": "臺灣",
                                                  "Location": [forecast_location(name, self.today) for name in counties]}]}}
        rows = parse_forecast(payload)
        central = [row for row in rows if row.regionName == "中部地區"]
        self.assertEqual([row.dataDate for row in central],
                         [(self.today + timedelta(days=offset)).isoformat() for offset in range(7)])
        self.assertEqual((central[0].mint, central[0].maxt), (25, 33))

    def test_town_forecast_includes_today_when_only_afternoon_remains(self):
        payload = {"records": {"Locations": [{"LocationsName": "臺中市",
                                                  "Location": [forecast_location("北區", self.today)]}]}}
        rows = parse_towns(payload, "臺中市")
        self.assertEqual([row["dataDate"] for row in rows],
                         [(self.today + timedelta(days=offset)).isoformat() for offset in range(7)])
        self.assertEqual((rows[0]["mint"], rows[0]["maxt"]), (25, 33))


if __name__ == "__main__":
    unittest.main()
