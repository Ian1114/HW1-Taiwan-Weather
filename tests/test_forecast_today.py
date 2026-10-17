"""Keep the current Taiwan date when CWA has already ended the morning period."""

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from weather_dashboard.cwa import CWAError, REGION_COUNTIES, parse_forecast, require_complete_week
from weather_dashboard.towns import get_town_forecast, parse_towns


def forecast_location(name, today, offsets=range(7)):
    times = {"最低溫度": [], "最高溫度": []}
    for offset in offsets:
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

    def test_next_seven_days_cannot_replace_missing_today(self):
        counties = [county for region in REGION_COUNTIES.values() for county in region]
        payload = {"records": {"Locations": [{"LocationsName": "臺灣",
                                                  "Location": [forecast_location(name, self.today, range(1, 8)) for name in counties]}]}}
        rows = parse_forecast(payload)
        self.assertEqual({row.dataDate for row in rows},
                         {(self.today + timedelta(days=offset)).isoformat() for offset in range(1, 7)})
        with self.assertRaises(CWAError):
            require_complete_week(rows)

    def test_town_forecast_fetches_again_on_each_request(self):
        payload = {"records": {"Locations": [{"LocationsName": "臺中市",
                                                  "Location": [forecast_location("北區", self.today)]}]}}
        with patch("weather_dashboard.towns.fetch_forecast", return_value=payload) as fetch:
            get_town_forecast("test-key", "臺中市")
            get_town_forecast("test-key", "臺中市")
        self.assertEqual(fetch.call_count, 2)


if __name__ == "__main__":
    unittest.main()
