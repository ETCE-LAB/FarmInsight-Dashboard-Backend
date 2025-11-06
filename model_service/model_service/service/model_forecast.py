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
    FIXED_IRR_L = 1.5
    SOIL_GAIN_PER_EVENT_MM = 0.1875

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

    inflow = forecast_greenhouse()
    inflow["date"] = pd.to_datetime(inflow["date"]).dt.normalize() + pd.Timedelta(hours=8)
    m3_col = "tank_inflow_m3" if "tank_inflow_m3" in inflow.columns else "total_m3"
    inflow_l_by_dt = dict(zip(inflow["date"], inflow[m3_col].astype(float) * 1000.0))

    def run_plan(plan_key: str, plan_factors: list[float]) -> dict[str, dict[str, str | float] | list[dict]]:
        tank_l = float(max(0.0, min(tank_capacity_liters, starting_tank_volume)))
        soil_mm = float(soil_threshold + plan_factors[2])

        rows = []
        for _, r in wx.iterrows():
            dt = r["date"]

            tank_l = min(
                tank_capacity_liters,
                tank_l + float(inflow_l_by_dt.get(dt, 0.0)) * plan_factors[0]
            )

            soil_next_mm = max(0.0, soil_mm - plan_factors[1])

            will_irrigate = False
            give_l = 0.0
            if soil_next_mm < soil_threshold and tank_l >= FIXED_IRR_L:
                will_irrigate = True
                give_l = FIXED_IRR_L
                tank_l -= give_l
                soil_next_mm = min(
                    soil_next_mm + SOIL_GAIN_PER_EVENT_MM,
                    soil_threshold + plan_factors[2]
                )

            soil_mm = soil_next_mm

            rows.append({
                "date": dt.isoformat(), # jeweils 8:00 Uhr
                "tank_l": float(tank_l),
                "soil_mm": float(soil_mm),
                "irr_l": float(give_l),
                "irrigate": bool(will_irrigate),
            })

        df = pd.DataFrame(rows)

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

    plans: dict[str, dict[str, dict[str, str | float] | list[dict]]] = {}
    for key, factors in PLAN_FACTORS.items():
        plans[key] = run_plan(key, factors)

    return plans
