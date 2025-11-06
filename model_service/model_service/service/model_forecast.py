from __future__ import annotations

import pandas as pd
from pandas import DataFrame

from ..utils.forecast import OpenMeteoClient
from ..utils.forecast_calculator import forecast_greenhouse
from ..utils.logging import get_logger

logger = get_logger()


def model_forecast(
        latitude: float,
        longitude: float,
        forecast_days: int,
        tank_capacity_liters: int,
        starting_tank_volume: float,
        soil_threshold: float,
) -> dict[str, dict[str, dict[str, str | float] | list[dict]]]:
    """
    Vereinfachtes What-if:
    - Reaktive Bewässerung, wenn Bodenfeuchte < soil_threshold_mm
    - Jede Bewässerung verbraucht fest 1.5 L
    - Alle Zeitstempel 08:00
    - Sehr simples Bodenmodell (konstanter Tagesverbrauch, optional kleiner Zuwachs durch Bewässerung)

    Zusätzlich: Ausgabe von drei Szenarien (best/average/worst) durch reine Variation des Zufluss-Inputs.
    Die Logik der Berechnung (Trigger, Verläufe etc.) bleibt unverändert.
    """

    FIXED_IRR_L = 1.5  # jede Bewässerung verbraucht 1.5 L
    #DAILY_SOIL_USE_MM = 3.0  # täglicher „Verbrauch“ (mm)
    SOIL_GAIN_PER_EVENT_MM = 0.1875  # um wieviel mm eine Bewässerung die Bodenfeuchte hebt
    #SOIL_START_BUFFER_MM = 15.0  # Start über Threshold

    # 1. inflow_factor
    # 2. DAILY_SOIL_USE_MM: täglicher Verbrauch
    # 3. SOIL_START_BUFFER_MM: Start über Threshold
    PLAN_FACTORS = {
        "best_case": [1.5, 0.10, 0.8],
        "average_case": [1.0, 0.15, 0.8],
        "worst_case": [0.0, 0.30, 0.6],
    }

    om = OpenMeteoClient(latitude, longitude)
    wx = om.fetch(forecast_days)
    wx["date"] = pd.to_datetime(wx["date"]).dt.normalize() + pd.Timedelta(hours=8)  # 08:00
    wx = wx.sort_values("date").reset_index(drop=True)

    # --- Dach-Zufluss -> Liter/Tag (optional weiter nutzen) ---
    inflow = forecast_greenhouse()  # 'date' + total_m3 / tank_inflow_m3
    inflow["date"] = pd.to_datetime(inflow["date"]).dt.normalize() + pd.Timedelta(hours=8)
    m3_col = "tank_inflow_m3" if "tank_inflow_m3" in inflow.columns else "total_m3"
    inflow_l_by_dt = dict(zip(inflow["date"], inflow[m3_col].astype(float) * 1000.0))

    def run_plan(plan_key: str, plan_factors: list[float]) -> dict[str, dict[str, str | float] | list[dict]]:
        # Startzustände je Plan separat (keine Querbeeinflussung)
        tank_l = float(max(0.0, min(tank_capacity_liters, starting_tank_volume)))
        soil_mm = float(soil_threshold + plan_factors[2])

        rows = []
        for _, r in wx.iterrows():
            dt = r["date"]

            # 1) Zufluss in den Tank (nur Input skaliert, Logik unverändert)
            tank_l = min(
                tank_capacity_liters,
                tank_l + float(inflow_l_by_dt.get(dt, 0.0)) * plan_factors[0]
            )

            # 2) Bodenfeuchte „trocken nach vorne“ abschätzen
            soil_next_mm = max(0.0, soil_mm - plan_factors[1])

            # 3) Trigger: unter Threshold? -> Bewässern (falls Tank≥1.5 L)
            will_irrigate = False
            give_l = 0.0
            if soil_next_mm < soil_threshold and tank_l >= FIXED_IRR_L:
                will_irrigate = True
                give_l = FIXED_IRR_L
                tank_l -= give_l
                # einfacher Effekt auf Bodenfeuchte
                soil_next_mm = min(
                    soil_next_mm + SOIL_GAIN_PER_EVENT_MM,
                    soil_threshold + plan_factors[2]
                )

            # 4) Zustand übernehmen
            soil_mm = soil_next_mm

            rows.append({
                "date": dt.isoformat(),  # mit Uhrzeit 08:00
                "tank_l": float(tank_l),
                "soil_mm": float(soil_mm),
                "irr_l": float(give_l),
                "irrigate": bool(will_irrigate),
            })

        df = pd.DataFrame(rows)

        # --- Summary / Score (hier: minimaler Wasserverbrauch, Infozwecke) ---
        total_irrigation = float(df["irr_l"].sum())
        summary = {
            "plan": f"reactive_threshold_{plan_key}",
            "total_irrigation_l": total_irrigation,
            "start_fill_l": float(starting_tank_volume),
            "soil_threshold_mm": float(soil_threshold),
            "days_below_threshold": int((df["soil_mm"] < soil_threshold).sum()),
        }

        logger.info(
            "Plan=%s | Sum Irr=%.1f L | StartFill=%.1f L | Threshold=%.1f mm | Days<Thr=%d",
            summary["plan"], total_irrigation, starting_tank_volume, soil_threshold, summary["days_below_threshold"]
        )

        return {"summary": summary, "series": df.to_dict(orient="records")}

    # --- alle drei Pläne erzeugen ---
    plans: dict[str, dict[str, dict[str, str | float] | list[dict]]] = {}
    for key, factors in PLAN_FACTORS.items():
        plans[key] = run_plan(key, factors)

    return plans
