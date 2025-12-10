import datetime

import requests

from farminsight_dashboard_backend.models import Location
from farminsight_dashboard_backend.services import InfluxDBManager, get_all_sensor_data


def fetch_weather_status(locationId):

    location = Location.objects.get(id=locationId)

    latitude = location.latitude
    longitude = location.longitude

    try:
        request_url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={latitude}&longitude={longitude}"
            f"&hourly=temperature_2m"
            f"&daily=weather_code,precipitation_probability_max"
            f"&timezone=Europe%2FBerlin"
        )

        response = requests.get(request_url)
        raw = response.json()

        now = datetime.datetime.now().replace(minute=0, second=0, microsecond=0)
        times = raw["hourly"]["time"]
        temps = raw["hourly"]["temperature_2m"]

        idx_now = times.index(now.isoformat(timespec="minutes"))
        current_temp = temps[idx_now]

        weather_code = raw["daily"]["weather_code"][0]
        rain_prob_today_max = raw["daily"]["precipitation_probability_max"][0]

        data = {
            "current_temperature": current_temp,
            "rain_probability_today": rain_prob_today_max,
            "weather_code": weather_code,
        }

        return data
    except Exception as e:
        raise RuntimeError(f"WeatherStatus fetch failed: {e}")


def get_weather_and_tank_values(location_id: str, sensor_id: str):
    # influx = InfluxDBManager.get_instance()

    weather_status = fetch_weather_status(location_id)
    measurements = get_all_sensor_data(sensor_id)

    return weather_status, measurements
