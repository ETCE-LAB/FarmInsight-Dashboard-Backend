import logging
from math import radians, cos, nan
from typing import List, Dict, Tuple

import pandas as pd
import requests


def compute_greenhouse_roof_rain(
        forecast: Dict,
        face_azimuth_deg: float,
        face_area_m2: float,
        slope_deg: float,
        *,
        precip_key: str = "rain_sum",
        wind_bias_strength: float = 0.5,  # 0..1: wie stark Wind die Verteilung verschiebt
        wind_exposure_factors: Tuple[float, float] = (1.0, 1.0)  # Abschirmung/Downwash A,B (0..1+)
) -> List[Dict]:
    """
    Verteilung der Tagesregenmenge auf zwei geneigte Dachflächen (Satteldach) **ohne Tropfenphysik**.
    Nutzt nur Dachneigung, Azimut, Windrichtung (woher) und optionale Abschirmung.

    Modell:
      Basis = cos(alpha)
      c = cos(beta - phi_to),  phi_to = (wind_from + 180°) mod 360
      raw_scale_A = max(0, Basis * (1 + w * c_A))
      raw_scale_B = max(0, Basis * (1 + w * c_B)),    c_B = -c_A (weil Flächen um 180° versetzt)
      scale_A = raw_scale_A * C_sA
      scale_B = raw_scale_B * C_sB

      mm_on_face = rain_mm * scale_face
      m³ = mm_on_face/1000 * A_geneigt

    Hinweise:
    - Ohne Clamping und mit C_sA=C_sB=1 bleibt die SUMME = 2*Basis*rain_mm (windunabhängig).
    - Clamping (Lee=0) und C_s != 1 verändern die **Gesamtmenge** (Regenschatten/Abschirmung).
    """
    daily = forecast.get("daily", {})
    times = daily.get("time")
    rains = daily.get(precip_key)
    winds = daily.get("wind_direction_10m_dominant")

    if not (times and rains is not None and winds):
        raise ValueError(
            "Forecast.daily muss 'time', "
            f"'{precip_key}' und 'wind_direction_10m_dominant' enthalten."
        )
    if not (len(times) == len(rains) == len(winds)):
        raise ValueError("Längen der daily-Arrays sind inkonsistent.")

    # Winkel vorbereiten
    alpha = radians(slope_deg)
    base = cos(alpha)
    beta_A = radians(face_azimuth_deg % 360)
    beta_B = radians((face_azimuth_deg + 180.0) % 360)
    Cs_A, Cs_B = wind_exposure_factors

    # Clamp w in [0, 1]
    w = max(0.0, min(1.0, float(wind_bias_strength)))

    results: List[Dict] = []
    for i in range(min(len(times), len(rains), len(winds))):
        date = times[i]
        if date is None:
            continue

        R_h = rains[i]
        R_h = 0.0 if R_h is None else float(R_h)

        phi_from = winds[i]
        if phi_from is None:
            # kein Wind-Bias + numerische Platzhalter
            w_eff = 0.0
            c_A = c_B = 0.0
            phi_from_val = nan
            phi_to_deg = nan
        else:
            phi_from_val = float(phi_from)
            phi_to_deg = (phi_from_val + 180.0) % 360.0
            phi_to = radians(phi_to_deg)
            c_A = cos(beta_A - phi_to)
            c_B = cos(beta_B - phi_to)
            w_eff = w

        # Roh-Skalen (ggf. mit Normalisierung wie bei dir)
        raw_A = max(0.0, base * (1.0 + w_eff * c_A))
        raw_B = max(0.0, base * (1.0 + w_eff * c_B))
        # (optional) normalize_bias ...

        scale_A = raw_A * Cs_A
        scale_B = raw_B * Cs_B

        mm_on_A = R_h * scale_A
        mm_on_B = R_h * scale_B
        m3_on_A = (mm_on_A * face_area_m2) / 1000.0
        m3_on_B = (mm_on_B * face_area_m2) / 1000.0

        results.append({
            "date": date,
            "rain_mm": R_h,
            "mm_on_A": mm_on_A,
            "mm_on_B": mm_on_B,
            "m3_on_A": m3_on_A,
            "m3_on_B": m3_on_B,
            "total_m3": m3_on_A + m3_on_B,
            "scale_A": scale_A,
            "scale_B": scale_B,
            "wind_from_deg": phi_from_val,  # **nie None, ggf. NaN**
            "wind_to_deg": phi_to_deg,  # **nie None, ggf. NaN**
        })
    return results


def forecast_greenhouse():
    latitude = 51.9
    longitude = 10.42
    url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}"
        f"&daily=rain_sum,sunshine_duration,weather_code,wind_speed_10m_max,wind_direction_10m_dominant,"
        f"wind_gusts_10m_max,temperature_2m_min,temperature_2m_max,sunrise,sunset,"
        f"precipitation_sum,precipitation_probability_max"
        f"&timezone=Europe%2FBerlin&forecast_days={16}"
    )

    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    forecast = resp.json()

    face_azimuth_deg = 30.0  # Dachfläche A schaut nach NordOstNord
    face_area_m2 = 10.0  # Fläche je Dachseite (geneigte Fläche), z.B. 10 m²
    slope_deg = 30.0  # Dachneigung 30°
    precip_key = "rain_sum"  # nur Regen; alternativ "precipitation_sum"
    wind_bias_strength = 0.3
    wind_exposure_factors = (0.8, 0.9)  # A (luv) leicht zugeneigt, B (lee) abgeschirmt

    result = compute_greenhouse_roof_rain(
        forecast,
        face_azimuth_deg=face_azimuth_deg,  # NordOstNordSeite
        face_area_m2=face_area_m2,  # pro Dachseite
        slope_deg=slope_deg,  # Neigung
        precip_key=precip_key,
        wind_bias_strength=wind_bias_strength,  # Windverteilungsstärke
        wind_exposure_factors=wind_exposure_factors,  # A leicht zugeneigt, B leicht abgeschirmt
    )

    logging.info("Datum        Regen(mm)   A(mm)   B(mm)   A(m³)   B(m³)   Gesamt(m³)  Wind aus (°)  Wind nach (°)")
    logging.info("-" * 100)
    for r in result:
        logging.info(
            f"{r['date']}  "
            f"{r['rain_mm']:>8.2f}  "
            f"{r['mm_on_A']:>6.2f}  "
            f"{r['mm_on_B']:>6.2f}  "
            f"{r['m3_on_A']:>6.3f}  "
            f"{r['m3_on_B']:>6.3f}  "
            f"{r['total_m3']:>7.3f}  "
            f"{r['wind_from_deg']:>10.1f}  "
            f"{r['wind_to_deg']:>10.1f}"
        )

    # Summen-Logging
    total_m3 = sum(r["total_m3"] for r in result)
    logging.info(f"\nGesamtzufluss über Zeitraum: {round(total_m3, 3)} m³")

    df = pd.DataFrame(result)
    df = df[["date", "total_m3"]].rename(columns={"total_m3": "tank_inflow_m3"})

    return df
