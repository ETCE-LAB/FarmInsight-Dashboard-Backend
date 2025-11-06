from __future__ import annotations
from datetime import datetime, UTC
from typing import Optional
import numpy as np
import pandas as pd
import logging

import requests


class OpenMeteoClient:
    """Client, der eine 16‑Tage‑Vorhersage abfragt – mit robustem Fallback."""

    def __init__(self, latitude: float, longitude: float):
        self.latitude = latitude
        self.longitude = longitude

    def fetch(self, forecast_days) -> pd.DataFrame:
        url = (
            f"https://api.open-meteo.com/v1/forecast?latitude={self.latitude}&longitude={self.longitude}"
            f"&daily=rain_sum,sunshine_duration,weather_code,wind_speed_10m_max,wind_direction_10m_dominant,"
            f"wind_gusts_10m_max,temperature_2m_min,temperature_2m_max,sunrise,sunset,"
            f"precipitation_sum,precipitation_probability_max"
            f"&timezone=Europe%2FBerlin&forecast_days={forecast_days}"
        )
        if requests is None:
            logging.warning("requests nicht verfügbar – simuliere Forecast.")
            return self._simulate_forecast(forecast_days)
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            print(resp.json())
            daily = resp.json().get("daily", {})
            if not daily:
                logging.warning("Open‑Meteo liefert keine 'daily' Daten – simuliere Forecast.")
                return self._simulate_forecast(forecast_days)
            df = pd.DataFrame(daily)
            df["date"] = pd.to_datetime(df["time"])  # rename time → date
            if "sunshine_duration" in df.columns:
                df["sunshine_duration_h"] = df["sunshine_duration"].astype(float) / 3600.0
            if df.get("precipitation_sum") is None and "rain_sum" in df:
                df["precipitation_sum"] = df["rain_sum"]
            keep = [
                "date", "precipitation_sum", "sunshine_duration_h", "wind_speed_10m_max",
                "temperature_2m_min", "temperature_2m_max",
            ]
            for c in keep:
                if c not in df.columns:
                    df[c] = np.nan
            return df[keep]
        except Exception as e:
            logging.warning("Open‑Meteo Fehler (%s) – simuliere Forecast.", e)
            return self._simulate_forecast(forecast_days)

    def _simulate_forecast(self, forecast_days: int) -> pd.DataFrame:
        start_date = pd.Timestamp(datetime.now(UTC).date())
        dates = pd.date_range(start_date, periods=forecast_days, freq="D")
        doy = dates.day_of_year.values
        temp_mean = 10 + 10 * np.sin(2 * np.pi * (doy - 170) / 365)
        temp_amp = 7 + 2 * np.cos(2 * np.pi * (doy - 30) / 365)
        tmax = temp_mean + temp_amp + np.random.normal(0, 1.0, len(dates))
        tmin = temp_mean - temp_amp + np.random.normal(0, 1.0, len(dates))
        precip_base = 1.2 + 1.0 * np.sin(2 * np.pi * (doy + 30) / 365)
        precip = np.clip(np.random.gamma(1.2, precip_base), 0, None)
        dry = np.random.rand(len(dates)) < 0.45
        precip[dry] *= 0.15
        daylight = 12 + 4 * np.sin(2 * np.pi * (doy - 172) / 365)
        sunshine = np.clip(daylight - (precip / (precip.max() + 1e-6)) * 4 + np.random.normal(0, 0.5, len(dates)), 0,
                           16)
        wind = np.clip(np.random.normal(20, 6, len(dates)), 0, None)
        return pd.DataFrame({
            "date": dates,
            "precipitation_sum": precip,
            "sunshine_duration_h": sunshine,
            "wind_speed_10m_max": wind,
            "temperature_2m_min": tmin,
            "temperature_2m_max": tmax,
        })
