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


def get_water_management_values(location_id: str, sensor_id: str):
    # influx = InfluxDBManager.get_instance()

    weather_status = fetch_weather_status(location_id)
    weather = {"weatherCode": weather_status["weather_code"],
               "currentTemperature": weather_status["current_temperature"],
               "rainProbabilityToday": weather_status["rain_probability_today"]}
    # water_status = get_all_sensor_data(sensor_id)
    water_status = {"waterLevel": 70, "capacity": 210, "dailyUsage": 3, "pumpStatus": "active",
                    "pumpLastRun": datetime.datetime.now().replace(minute=0, second=0, microsecond=0),
                    "tankConnected": True}

    expend = False

    field_moisture = [
        {"fieldId": 1, "moisture": 45, "crop": 'Corn'},
        {"fieldId": 2, "moisture": 72, "crop": 'Soy'},
        {"fieldId": 3, "moisture": 28, "crop": 'Fallow'},
        {"fieldId": 4, "moisture": 65, "crop": 'Soy'},
        {"fieldId": 5, "moisture": 80, "crop": 'Rice'},
        {"fieldId": 6, "moisture": 42, "crop": 'Corn'},
        {"fieldId": 7, "moisture": 35, "crop": 'Wheat'},
        {"fieldId": 8, "moisture": 55, "crop": 'Corn'},
        {"fieldId": 9, "moisture": 60, "crop": 'Soy'},
        {"fieldId": 10, "moisture": 25, "crop": 'Fallow'},
        {"fieldId": 11, "moisture": 70, "crop": 'Wheat'},
        {"fieldId": 12, "moisture": 50, "crop": 'Rice'},
        {"fieldId": 13, "moisture": 45, "crop": 'Corn'},
        {"fieldId": 14, "moisture": 72, "crop": 'Soy'},
        {"fieldId": 15, "moisture": 28, "crop": 'Fallow'},
        {"fieldId": 16, "moisture": 65, "crop": 'Soy'},
        {"fieldId": 17, "moisture": 80, "crop": 'Rice'},
        {"fieldId": 18, "moisture": 42, "crop": 'Corn'},
        {"fieldId": 19, "moisture": 35, "crop": 'Wheat'},
        {"fieldId": 20, "moisture": 55, "crop": 'Corn'},
        {"fieldId": 21, "moisture": 60, "crop": 'Soy'}
    ] if expend else [{"fieldId": 1, "moisture": 100, "crop": "Oxycodone"}]

    water_usage = [
        {"date": 'Mon', "usage": 3.0},
        {"date": 'Tue', "usage": 1.5},
        {"date": 'Wed', "usage": 4.5},
        {"date": 'Thu', "usage": 1.5},
        {"date": 'Fri', "usage": 1.5},
        {"date": 'Sat', "usage": 3.0},
        {"date": 'Sun', "usage": 3.0},
    ]

    return weather, water_status, field_moisture, water_usage
