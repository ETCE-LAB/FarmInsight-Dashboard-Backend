import pandas as pd

from ..utils.logging import get_logger

logger = get_logger()


class SensorDataLoader:
    """Lädt und vereinheitlicht Regen- und Füllstandsdaten aus CSV-Dateien."""

    def __init__(self, rain_path: str, water_path: str, tank_capacity: float):
        self.rain_path = rain_path
        self.water_path = water_path
        self.tank_capacity = tank_capacity

    def load(self) -> pd.DataFrame:
        logger.info("Lade reale Sensordaten aus CSV-Dateien…")

        rain = pd.read_csv(self.rain_path)
        # rain["_time"] = pd.to_datetime(rain["_time"])
        # rain = rain.rename(columns={"_value": "precipitation_sum"})
        # rain = rain.groupby(rain["_time"].dt.date)["precipitation_sum"].sum().reset_index()
        rain = correct_values(rain)

        water = pd.read_csv(self.water_path)
        water["_time"] = pd.to_datetime(water["_time"], utc=True).dt.tz_convert("Europe/Berlin")
        water["date"] = water["_time"].dt.tz_localize(None).dt.normalize()  # dtype: datetime64[ns]

        # 2) Werte-Spalte vereinheitlichen
        water["fill"] = pd.to_numeric(water["_value"], errors="coerce")

        # 3) Auf Tagesebene aggregieren (über die *Spalte* 'date' – kein rename von _time!)
        water = (
            water.groupby("date", as_index=False)
            .agg(fill=("fill", "max"))  # Aggregationen nach Bedarf anpassen
        )

        water = water.rename(columns={water.columns[0]: "date"})  # erste Spalte ist date

        # Auf Datum mergen
        df = pd.merge(rain, water, on="date", how="outer").sort_values("date")

        df["rain_capture"] = df["rain_mm"]

        # TODO: check if this col is needed
        df["tank_capacity"] = float(self.tank_capacity)

        df["precip_roll_three_days"] = df["rain_mm"].rolling(3, min_periods=1).sum()
        df["precip_roll_seven_days"] = df["rain_mm"].rolling(7, min_periods=1).sum()

        cap = float(self.tank_capacity or 0)
        df["fill_ratio"] = (df["fill"] / cap).clip(0, 1) if cap > 0 else (df["fill"] / df["fill"].max())

        df["fill_level_yesterday"] = df["fill_ratio"].shift(1)
        df["fill_level_three_days_ago"] = df["fill_ratio"].shift(3)
        df["fill_level_seven_days_ago"] = df["fill_ratio"].shift(7)

        for h in range(1, 8):
            df[f"target_t_plus_{h}"] = df["fill_ratio"].shift(-h)

        df = df.dropna().reset_index(drop=True)
        logger.info(f"Sensorhistorie geladen: {len(df)} Tage ({df['date'].iloc[0]} – {df['date'].iloc[-1]})")
        print("df after load(): \n", df)
        return df


def correct_values(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values("_time").reset_index(drop=True)

    dt = pd.to_datetime(df["_time"], utc=True).dt.tz_convert("Europe/Berlin")
    vals = pd.to_numeric(df["_value"], errors="coerce").fillna(0.0)

    rows = []
    for i in range(1, len(df)):
        t0, t1 = dt.iloc[i - 1], dt.iloc[i]
        v = float(vals.iloc[i])
        if t1 <= t0:
            continue

        duration = (t1 - t0).total_seconds()
        current = t0
        while current < t1:
            day_end = (current + pd.Timedelta(days=1)).normalize()  # tz-aware Mitternacht
            chunk_end = min(t1, day_end)
            frac = (chunk_end - current).total_seconds() / duration

            # <- HIER: tz-naiv + normalisiert als Join-Key
            rows.append({
                "date": current.tz_localize(None).normalize(),
                "rain_mm": v * frac
            })
            current = chunk_end

    rain_per_day = (
        pd.DataFrame(rows)
        .groupby("date", as_index=False)["rain_mm"]
        .sum()
    )
    return rain_per_day
