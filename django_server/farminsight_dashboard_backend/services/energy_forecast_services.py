"""
Energy Forecast Services

Handles the retrieval and processing of energy forecasts for the Energy Dashboard.
Integrates with ResourceManagementModels that have model_type='energy'.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from django.utils import timezone

from farminsight_dashboard_backend.models import ResourceManagementModel, EnergyConsumer
from farminsight_dashboard_backend.services.influx_services import InfluxDBManager
from farminsight_dashboard_backend.utils import get_logger

logger = get_logger()


def get_energy_models_by_fpf(fpf_id: str) -> List[ResourceManagementModel]:
    """
    Get all active energy management models for a given FPF.

    :param fpf_id: UUID of the FPF
    :return: List of active energy ResourceManagementModels
    """
    return list(ResourceManagementModel.objects.filter(
        FPF_id=fpf_id,
        model_type='energy',
        isActive=True
    ))


def get_historical_consumption(fpf_id: str, hours_back: int = 12) -> List[Dict[str, Any]]:
    """
    Get historical energy consumption data for a given FPF.
    Aggregates consumption from all active energy consumers.

    :param fpf_id: UUID of the FPF
    :param hours_back: Number of hours to look back
    :return: List of data points with timestamp and value_watts
    """
    try:
        influx = InfluxDBManager.get_instance()
        from_date = (timezone.now() - timedelta(hours=hours_back)).isoformat()
        to_date = timezone.now().isoformat()

        balance_data = influx.fetch_energy_balance(fpf_id, from_date, to_date)

        if balance_data and 'consumption' in balance_data:
            return [
                {"timestamp": dp['timestamp'], "value_watts": dp['watts']}
                for dp in balance_data['consumption'].get('data', [])
            ]
    except Exception as e:
        logger.warning(f"Could not fetch historical consumption for FPF {fpf_id}: {e}")

    return []


def get_forecast_generation(fpf_id: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Get forecast generation data from energy management models.
    Returns expected, worst_case, and best_case forecasts.

    :param fpf_id: UUID of the FPF
    :return: Dict with expected, worst_case, and best_case forecast arrays
    """
    result = {
        "expected": [],
        "worst_case": [],
        "best_case": []
    }

    try:
        influx = InfluxDBManager.get_instance()
        energy_models = get_energy_models_by_fpf(fpf_id)

        for model in energy_models:
            try:
                forecast_data = influx.fetch_latest_model_forecast(
                    fpf_id=fpf_id,
                    model_id=str(model.id),
                    hours=48  # Look back up to 48 hours for recent forecasts
                )

                if not forecast_data or 'data' not in forecast_data:
                    continue

                data = forecast_data.get('data', {})
                forecasts = data.get('forecasts', [])

                # Process each forecast in the model's data
                # Only process "Battery State of Charge" forecast, not solar
                for forecast in forecasts:
                    forecast_name = forecast.get('name', '').lower()
                    
                    # Only process battery SoC data for the graph
                    if 'battery' not in forecast_name and 'soc' not in forecast_name:
                        continue
                    
                    values = forecast.get('values', [])

                    for value_set in values:
                        case_name = value_set.get('name', '').lower().replace('-', '_').replace(' ', '_')
                        value_list = value_set.get('value', [])

                        # Map AI Backend scenario names to our standard keys
                        # AI Backend uses: expected, optimistic, pessimistic
                        if 'optimistic' in case_name or 'best' in case_name:
                            target_key = 'best_case'
                        elif 'pessimistic' in case_name or 'worst' in case_name:
                            target_key = 'worst_case'
                        elif 'expected' in case_name:
                            target_key = 'expected'
                        else:
                            target_key = 'expected'  # Default fallback

                        for v in value_list:
                            result[target_key].append({
                                "timestamp": v.get('timestamp'),
                                "value_watts": v.get('value', 0)
                            })

            except Exception as e:
                logger.warning(f"Could not fetch forecast for model {model.name}: {e}")
                continue

    except Exception as e:
        logger.error(f"Error fetching forecast generation for FPF {fpf_id}: {e}")

    # Sort by timestamp and remove duplicates
    for key in result:
        result[key] = sorted(
            result[key],
            key=lambda x: x.get('timestamp', '')
        )

    return result


def get_forecast_consumption(fpf_id: str, hours_ahead: int = 24) -> List[Dict[str, Any]]:
    """
    Get forecast consumption data.
    Uses historical averages to predict future consumption.

    :param fpf_id: UUID of the FPF
    :param hours_ahead: Number of hours to forecast ahead
    :return: List of forecast data points
    """
    try:
        influx = InfluxDBManager.get_instance()

        # Get 7 days of historical data for averaging
        from_date = (timezone.now() - timedelta(days=7)).isoformat()
        to_date = timezone.now().isoformat()

        balance_data = influx.fetch_energy_balance(fpf_id, from_date, to_date)

        if not balance_data or 'consumption' not in balance_data:
            return []

        consumption_data = balance_data['consumption'].get('data', [])

        if not consumption_data:
            # Fallback: Use current total consumption as constant forecast
            consumers = EnergyConsumer.objects.filter(FPF_id=fpf_id, isActive=True)
            total_consumption = sum(c.consumptionWatts for c in consumers)

            forecasts = []
            now = timezone.now()
            for h in range(hours_ahead):
                forecasts.append({
                    "timestamp": (now + timedelta(hours=h)).isoformat(),
                    "value_watts": total_consumption
                })
            return forecasts

        # Calculate hourly averages from historical data
        hourly_averages = {}
        for dp in consumption_data:
            try:
                ts = datetime.fromisoformat(dp['timestamp'].replace('Z', '+00:00'))
                hour = ts.hour
                if hour not in hourly_averages:
                    hourly_averages[hour] = []
                hourly_averages[hour].append(dp['watts'])
            except Exception:
                continue

        # Calculate mean for each hour
        for hour in hourly_averages:
            values = hourly_averages[hour]
            hourly_averages[hour] = sum(values) / len(values) if values else 0

        # Generate forecast based on hourly averages
        forecasts = []
        now = timezone.now()

        for h in range(hours_ahead):
            future_time = now + timedelta(hours=h)
            hour = future_time.hour
            avg_consumption = hourly_averages.get(hour, 0)

            # If no data for this hour, use overall average
            if avg_consumption == 0 and hourly_averages:
                avg_consumption = sum(hourly_averages.values()) / len(hourly_averages)

            forecasts.append({
                "timestamp": future_time.isoformat(),
                "value_watts": round(avg_consumption, 2)
            })

        return forecasts

    except Exception as e:
        logger.warning(f"Could not generate consumption forecast for FPF {fpf_id}: {e}")

    return []


def get_energy_graph_data(fpf_id: str, hours_back: int = 12, hours_ahead: int = 24) -> Dict[str, Any]:
    """
    Get complete graph data for the energy dashboard.
    Returns battery_soc forecast data in the format expected by the Frontend.

    :param fpf_id: UUID of the FPF
    :param hours_back: Hours of historical data to include
    :param hours_ahead: Hours of forecast data to include
    :return: Complete graph data dict with battery_soc and battery_max_wh
    """
    from farminsight_dashboard_backend.services.energy_decision_services import get_fpf_energy_config
    
    config = get_fpf_energy_config(fpf_id)
    battery_max_wh = config['battery_max_wh']
    
    # Get forecast generation data (expected, worst_case, best_case)
    forecast_data = get_forecast_generation(fpf_id)
    
    # Transform to battery_soc format expected by Frontend
    # Frontend expects: { timestamp: string, value_wh: number }
    battery_soc = {
        "expected": [],
        "worst_case": [],
        "best_case": []
    }
    
    for key in ["expected", "worst_case", "best_case"]:
        for dp in forecast_data.get(key, []):
            battery_soc[key].append({
                "timestamp": dp.get("timestamp"),
                "value_wh": dp.get("value_watts", 0)  # Treat as Wh for battery capacity
            })
    
    return {
        "battery_soc": battery_soc,
        "battery_max_wh": battery_max_wh,
        # Also include original data for backwards compatibility
        "historical_consumption": get_historical_consumption(fpf_id, hours_back),
        "forecast_consumption": get_forecast_consumption(fpf_id, hours_ahead)
    }
