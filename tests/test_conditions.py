"""Regression checks for real observation formats and warning validity."""
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from weather_dashboard.conditions import (
    _download, get_conditions, number, parse_air, parse_marine,
    parse_stations, parse_typhoon, wind_direction,
)


class ConditionsTests(unittest.TestCase):
    def test_zero_rain_and_missing_rain_are_distinct(self):
        station = {"StationName": "示範站", "GeoInfo": {"CountyName": "臺中市"},
                   "RainfallElement": {"Past10Min": {"Precipitation": "0"}, "Past1hr": {"Precipitation": "-99"}}}
        row = parse_stations({"records": {"Station": [station]}}, "rain", "臺中市")[0]
        self.assertEqual(row["rain10m"], 0)
        self.assertIsNone(row["rain1h"])
        self.assertIsNone(row["rain24h"])
        self.assertIsNone(number("NaN"))

    def test_wind_compass_calm_and_missing(self):
        self.assertEqual(wind_direction(90, 2), "東風")
        self.assertEqual(wind_direction(360, 2), "北風")
        self.assertEqual(wind_direction(990, 2), "風向不定")
        self.assertEqual(wind_direction(-99, None), "缺測")
        self.assertEqual(wind_direction(0, 0), "靜風")

    def test_expired_and_cancelled_warnings_not_active(self):
        now = datetime.now(timezone.utc)
        info = {"language": "zh-TW", "headline": "颱風警報", "effective": (now-timedelta(hours=1)).isoformat(), "expires": (now+timedelta(hours=1)).isoformat()}
        payload = {"records": {"info": [info]}}
        self.assertEqual(parse_typhoon(payload)[0]["state"], "有效警報")
        info["headline"] = "解除颱風警報"
        self.assertNotEqual(parse_typhoon(payload)[0]["state"], "有效警報")
        info["headline"] = "颱風警報"
        info["expires"] = (now-timedelta(minutes=1)).isoformat()
        self.assertNotEqual(parse_typhoon(payload)[0]["state"], "有效警報")

    def test_marine_values_join_by_period_not_array_order(self):
        location = {"LocationName": "測試海域", "WeatherElement": [
            {"Time": [{"StartTime": "day1", "EndTime": "day2", "ElementValue": {"WaveHeightDescription": "2公尺"}}]},
            {"Time": [{"StartTime": "day2", "EndTime": "day3", "ElementValue": {"WindDirectionDescription": "南風"}},
                      {"StartTime": "day1", "EndTime": "day2", "ElementValue": {"WindDirectionDescription": "北風"}}]},
        ]}
        rows = parse_marine({"cwaopendata": {"Dataset": {"Locations": {"Location": [location]}}}})
        first = next(row for row in rows if row["start"] == "day1")
        self.assertEqual((first["wave"], first["direction"]), ("2公尺", "北風"))

    @patch("weather_dashboard.conditions.get_secret", return_value="test-placeholder")
    @patch("weather_dashboard.conditions.requests.Session")
    def test_environment_api_top_level_array(self, session_class, secret):
        response = MagicMock(ok=True)
        response.json.return_value = [{"county": "臺中市", "sitename": "測試站", "aqi": "0", "pm2.5": "-99"}]
        session_class.return_value.__enter__.return_value.get.return_value = response
        rows = parse_air(_download("air"), "臺中市")
        self.assertEqual(rows[0]["aqi"], 0)
        self.assertIsNone(rows[0]["pm25"])

    @patch("weather_dashboard.conditions.get_secret", return_value=None)
    def test_missing_air_key_has_explicit_status(self, secret):
        result = get_conditions("air")
        self.assertEqual(result["status"], "unconfigured")
        self.assertEqual(result["rows"], [])


if __name__ == "__main__":
    unittest.main()
