


from __future__ import annotations

def response_wrapper(plans: dict) -> dict:
    """
    Output :
      {
        "forecasts": [
          {"name": "tank-level", "values": [{ "name": "...-case", "value": [{timestamp, value}, ...] }, ...]},
          {"name": "soil-moisture", "values": [{ "name": "...-case", "value": [{timestamp, value}, ...] }, ...]}
        ],
        "actions": [
          {"name": "...-case", "value": [{timestamp, value, action}, ...]},
          ...
        ]
      }
    """

    def series_points(case_key: str, field: str):
        return [
            {"timestamp": row["date"], "value": float(row[field])}
            for row in plans[case_key]["series"]
        ]

    def action_points(case_key: str):
        pts = []
        for row in plans[case_key]["series"]:
            pts.append({
                "timestamp": row["date"],
                "value": float(row["irr_l"]),  # Wassermenge
                "action": "watering" if row["irrigate"] else "none",
            })
        return pts

    forecasts = [
        {
            "name": "tank-level",
            "values": [
                {"name": "best-case", "value": series_points("best_case", "tank_l")},
                {"name": "average-case", "value": series_points("average_case", "tank_l")},
                {"name": "worst-case", "value": series_points("worst_case", "tank_l")},
            ],
        },
        {
            "name": "soil-moisture",
            "values": [
                {"name": "best-case", "value": series_points("best_case", "soil_mm")},
                {"name": "average-case", "value": series_points("average_case", "soil_mm")},
                {"name": "worst-case", "value": series_points("worst_case", "soil_mm")},
            ],
        },
    ]

    actions = [
        {"name": "best-case", "value": action_points("best_case")},
        {"name": "average-case", "value": action_points("average_case")},
        {"name": "worst-case", "value": action_points("worst_case")},
    ]

    return {"forecasts": forecasts, "actions": actions}
