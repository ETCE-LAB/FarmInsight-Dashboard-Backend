import json
from django.utils import timezone
from influxdb_client import Point, WritePrecision
from farminsight_dashboard_backend.exceptions import InfluxDBWriteException


def _validate_forecasts_structure(data: dict) -> tuple[bool, str]:
    """
    Validates the structure of the forecast + action payload before writing it to InfluxDB.
    Returns (is_valid: bool, error_message: str)
    """

    # --- Validate main keys ---
    if not isinstance(data, dict):
        return False, "Forecast payload is not a dictionary."

    if "forecasts" not in data or not isinstance(data["forecasts"], list):
        return False, "Missing or invalid 'forecasts' list."

    if "actions" not in data or not isinstance(data["actions"], list):
        return False, "Missing or invalid 'actions' list."

    # --- Validate forecasts ---
    for forecast in data["forecasts"]:
        if "name" not in forecast or not isinstance(forecast["name"], str):
            return False, "Each forecast must contain a string 'name'."

        if "values" not in forecast or not isinstance(forecast["values"], list):
            return False, f"Forecast '{forecast}' missing 'values'."

        for series in forecast["values"]:
            if "name" not in series or not isinstance(series["name"], str):
                return False, f"Forecast series entry missing 'name': {series}"

            if "value" not in series or not isinstance(series["value"], list):
                return False, f"Forecast series missing 'value' array: {series}"

            for point in series["value"]:
                if "timestamp" not in point:
                    return False, f"Forecast point missing 'timestamp': {point}"

                if "value" not in point:
                    return False, f"Forecast point missing 'value': {point}"

    # --- Validate actions ---
    for action_group in data["actions"]:
        if "name" not in action_group:
            return False, f"Action group missing 'name': {action_group}"

        if "value" not in action_group or not isinstance(action_group["value"], list):
            return False, f"Action group missing 'value' list: {action_group}"

        for point in action_group["value"]:
            if "timestamp" not in point:
                return False, f"Action entry missing 'timestamp': {point}"

            if "value" not in point:
                return False, f"Action entry missing 'value': {point}"

            if "action" not in point:
                return False, f"Action entry missing 'action': {point}"

    return True, ""
