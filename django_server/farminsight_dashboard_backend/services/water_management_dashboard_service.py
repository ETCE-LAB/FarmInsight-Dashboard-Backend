import datetime

import numpy as np
import requests

from farminsight_dashboard_backend.models import Location, FPF
from farminsight_dashboard_backend.services import InfluxDBManager

from farminsight_dashboard_backend.models import Sensor
from collections import defaultdict


def get_current_weather_snapshot(location_id: str) -> dict:
    location = Location.objects.get(id=location_id)
    try:
        request_url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={location.latitude}&longitude={location.longitude}"
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

        return {
            "weatherCode": raw["daily"]["weather_code"][0],
            "currentTemperature": temps[idx_now],
            "rainProbabilityToday": raw["daily"]["precipitation_probability_max"][0],
        }

    except Exception as e:
        raise RuntimeError(f"Failed to fetch weather snapshot: {e}")


def get_latest_water_level(sensor_id: str) -> float | None:
    try:
        sensor = Sensor.objects.get(id=sensor_id)
        influx = InfluxDBManager.get_instance()

        latest = influx.fetch_latest_sensor_measurements(
            fpf_id=str(sensor.FPF.id),
            sensor_ids=[str(sensor_id)]
        )

        value = latest.get(str(sensor_id), {}).get("value")
        return float(value) if value is not None else None

    except Exception as e:
        print(f"Failed to fetch latest water level: {e}")
        return None


def get_weekly_water_levels(sensor_id: str) -> list[dict] | None:
    try:
        sensor = Sensor.objects.get(id=sensor_id)
        influx = InfluxDBManager.get_instance()

        now = datetime.datetime.now(datetime.timezone.utc)
        from_date = (now - datetime.timedelta(days=7)).isoformat()
        to_date = now.isoformat()

        measurements = influx.fetch_sensor_measurements(
            fpf_id=str(sensor.FPF.id),
            sensor_ids=[str(sensor_id)],
            from_date=from_date,
            to_date=to_date
        ).get(str(sensor_id), [])

        if not measurements:
            return None

        # Gruppiere nach Datum (YYYY-MM-DD)
        daily_latest: dict[str, tuple[datetime.datetime, float]] = {}

        for m in measurements:
            measured_at = datetime.datetime.fromisoformat(
                m["measuredAt"].replace("Z", "+00:00")
            )
            day_key = measured_at.date().isoformat()

            value = m.get("value")
            if value is None:
                continue

            # immer den letzten Wert des Tages behalten
            if (
                    day_key not in daily_latest
                    or measured_at > daily_latest[day_key][0]
            ):
                daily_latest[day_key] = (measured_at, value)

        # chronologisch sortieren
        sorted_days = sorted(daily_latest.items(), key=lambda x: x[1][0])

        # auf maximal 7 Einträge begrenzen (letzte 7)
        last_7 = sorted_days[-7:]

        return [
            {
                "date": day,  # z. B. "2025-01-18"
                "level": round(value, 1)
            }
            for day, (_, value) in last_7
        ]

    except Exception as e:
        print(f"Failed to fetch last 7 daily water levels: {e}")
        return None


def get_latest_field_moisture(fpf_id: str) -> list[dict] | None:
    try:
        sensors = Sensor.objects.filter(
            FPF_id=fpf_id,
            parameter__icontains="moisture",
            isActive=True
        )

        if not sensors.exists():
            return None

        influx = InfluxDBManager.get_instance()
        latest = influx.fetch_latest_sensor_measurements(
            fpf_id=str(fpf_id),
            sensor_ids=[str(s.id) for s in sensors]
        )

        result = []
        for idx, sensor in enumerate(sensors, start=1):
            value = latest.get(str(sensor.id), {}).get("value")
            if value is not None:
                result.append({
                    "fieldId": idx,
                    "moisture": round(float(value), 1),
                    "crop": sensor.location or sensor.name
                })

        return result or None

    except Exception as e:
        print(f"Failed to fetch field moisture: {e}")
        return None


def calculate_average_daily_water_usage(water_levels: list[dict]) -> float | None:
    if not water_levels or len(water_levels) < 2:
        return None

    levels = [d["level"] for d in water_levels if "level" in d]

    diffs = [
        prev - curr
        for prev, curr in zip(levels, levels[1:])
        if prev - curr > 0
    ]

    return round(float(np.mean(diffs)), 1) if diffs else None


def get_pump_status(date_pump_last_run):
    this_week_active = (datetime.datetime.now() - date_pump_last_run) < datetime.timedelta(days=7)


def collect_water_management_dashboard_data(
        location_id: str,
        fpf_id: str
):
    fpf = FPF.objects.get(id=fpf_id)
    cfg = fpf.resourceManagementConfig or {}
    print("cfg:", cfg)
    if not cfg.get("rmmActive"):
        return None

    sensors = cfg.get("rmmSensorConfig", {})
    water_sensor_id = sensors.get("waterSensorId")
    soil_sensor_id = sensors.get("soilSensorId")

    if not water_sensor_id or not soil_sensor_id:
        raise ValueError("RMM active but sensor IDs are missing")

    weather = get_current_weather_snapshot(location_id)

    water_level = 10#get_latest_water_level(water_sensor_id)
    water_levels = get_weekly_water_levels(water_sensor_id)
    avg_usage = calculate_average_daily_water_usage(water_levels) if water_levels else None

    field_moisture = get_latest_field_moisture(str(fpf.id))

    water_status = {
        "waterLevel": water_level or -1,
        "avgUsage": avg_usage,
        "capacity": sensors.get("tankCapacity"),
        "pumpStatus": None, # current types in FE 'thisWeekActive' or 'thisWeekInactive'
        "pumpLastRun": None
    }

    return {
        "weatherStatus": weather,
        "waterStatus": water_status,
        "fieldMoisture": field_moisture,
        "waterLevels": water_levels,
    }
