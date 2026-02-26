from typing import Optional
from dataclasses import dataclass
from enum import Enum

from farminsight_dashboard_backend.models import EnergyConsumer, EnergySource, FPF
from farminsight_dashboard_backend.services.energy_consumer_services import (
    get_active_energy_consumers_by_fpf_id,
    get_total_consumption_by_fpf_id,
    get_consumers_by_priority
)
from farminsight_dashboard_backend.services.energy_source_services import (
    get_active_energy_sources_by_fpf_id,
    get_current_power_output_by_fpf_id,
    get_grid_source
)
from farminsight_dashboard_backend.utils import get_logger

logger = get_logger()


# Default Energy Management Constants (used as fallbacks)
GRID_CONNECT_THRESHOLD = 11  # Connect to grid when battery < 11%
SHUTDOWN_THRESHOLD = 10  # Shutdown non-critical consumers when battery <= 10%
BATTERY_MAX_KWH = 1.6  # Maximum battery capacity in kWh
BATTERY_MAX_WH = BATTERY_MAX_KWH * 1000  # Maximum battery capacity in Wh
CRITICAL_PRIORITY_THRESHOLD = 3  # Priority <= 3 are critical consumers
WARNING_THRESHOLD = 20  # Warning level percentage
GRID_DISCONNECT_THRESHOLD = 50  # Disconnect grid when battery > 50%


def get_fpf_energy_config(fpf_id: str) -> dict:
    """
    Get energy configuration for an FPF.
    Returns FPF-specific thresholds or defaults if not configured.
    """
    try:
        fpf = FPF.objects.get(id=fpf_id)
        return {
            'grid_connect_threshold': fpf.energyGridConnectThreshold,
            'shutdown_threshold': fpf.energyShutdownThreshold,
            'warning_threshold': fpf.energyWarningThreshold,
            'battery_max_wh': fpf.energyBatteryMaxWh,
            'grid_disconnect_threshold': fpf.energyGridDisconnectThreshold,
        }
    except FPF.DoesNotExist:
        return {
            'grid_connect_threshold': GRID_CONNECT_THRESHOLD,
            'shutdown_threshold': SHUTDOWN_THRESHOLD,
            'warning_threshold': WARNING_THRESHOLD,
            'battery_max_wh': BATTERY_MAX_WH,
            'grid_disconnect_threshold': GRID_DISCONNECT_THRESHOLD,
        }


class EnergyAction(Enum):
    """Possible energy management actions"""
    NORMAL = "normal"
    CONNECT_GRID = "connect_grid"
    DISCONNECT_GRID = "disconnect_grid"
    SHUTDOWN_NON_CRITICAL = "shutdown_non_critical"
    EMERGENCY_SHUTDOWN = "emergency_shutdown"


@dataclass
class EnergyState:
    """Represents the current energy state of an FPF"""
    fpf_id: str
    battery_level_wh: float
    battery_percentage: float
    battery_max_wh: float
    total_consumption_watts: float
    total_production_watts: float
    net_power_watts: float  # Positive = surplus, Negative = deficit
    grid_connected: bool
    action: EnergyAction
    consumers_to_shutdown: list
    status: str  # "critical", "warning", "normal"
    message: str


def get_current_power_output_with_weather(fpf_id: str) -> float:
    """
    Get current power output including weather-based estimates for solar/wind sources.
    Uses weather forecast data to adjust production estimates for weather-dependent sources.

    :param fpf_id: UUID of the FPF
    :return: Estimated total power output in watts
    """
    from farminsight_dashboard_backend.models import EnergySource
    from farminsight_dashboard_backend.services.influx_services import InfluxDBManager
    
    try:
        fpf = FPF.objects.get(id=fpf_id)
    except FPF.DoesNotExist:
        return get_current_power_output_by_fpf_id(fpf_id)
    
    sources = EnergySource.objects.filter(FPF_id=fpf_id, isActive=True)
    total_output = 0.0
    
    # Get weather data if FPF has a location
    weather_factor = 1.0  # Default: no weather adjustment
    sunshine_hours = None
    wind_speed = None
    
    if fpf.location:
        try:
            influx = InfluxDBManager.get_instance()
            # Fetch today's weather forecast
            weather_data = influx.fetch_latest_weather_forecast(
                organization_id=str(fpf.location.organization.id),
                location_id=str(fpf.location.id)
            )
            if weather_data:
                # sunshine_duration is in seconds, convert to hours (max ~14 hours of sunlight)
                sunshine_hours = weather_data.get('sunshine_duration', 0) / 3600
                wind_speed = weather_data.get('wind_speed_10m_max', 0)
        except Exception as e:
            logger.debug(f"Could not fetch weather data for FPF {fpf_id}: {e}")
    
    for source in sources:
        if source.weatherDependent:
            # Prefer live sensor data over weather-based estimates
            if source.sensor and source.sensor.isActive:
                from farminsight_dashboard_backend.services.energy_source_services import get_live_output_watts
                live_value = get_live_output_watts(source)
                # Only use live value if it's a real reading (not the DB default 0)
                if live_value > 0 or source.currentOutputWatts == 0:
                    total_output += live_value
                    continue
            # Fallback: weather-based estimate when no live sensor data
            if source.sourceType == 'solar' and sunshine_hours is not None:
                # Solar output factor based on sunshine hours (0-14 hours typical max)
                # Assume max output at ~10+ hours of sunshine
                solar_factor = min(1.0, sunshine_hours / 10.0)
                total_output += source.maxOutputWatts * solar_factor
            elif source.sourceType == 'wind' and wind_speed is not None:
                # Wind output factor based on wind speed
                # Typical cut-in speed ~3 m/s, rated speed ~12 m/s
                if wind_speed < 3:
                    wind_factor = 0.0
                elif wind_speed < 12:
                    wind_factor = (wind_speed - 3) / 9.0  # Linear ramp from 3-12 m/s
                else:
                    wind_factor = 1.0  # Full output above rated speed
                total_output += source.maxOutputWatts * wind_factor
            else:
                # Weather-dependent but no weather data available
                total_output += source.currentOutputWatts
        else:
            # Non-weather-dependent source (grid, battery, generator)
            total_output += source.currentOutputWatts
    
    return total_output


def calculate_battery_percentage(battery_level_wh: float, max_capacity_wh: float = BATTERY_MAX_WH) -> float:
    """
    Calculate battery percentage from current level
    :param battery_level_wh: Current battery level in Wh
    :param max_capacity_wh: Maximum battery capacity in Wh
    :return: Battery percentage (0-100)
    """
    if max_capacity_wh <= 0:
        return 0.0
    return min(100.0, max(0.0, (battery_level_wh / max_capacity_wh) * 100))


def evaluate_energy_state(fpf_id: str, battery_level_wh: float, max_capacity_wh: float = None) -> EnergyState:
    """
    Evaluate the current energy state and determine required actions.

    Decision Logic (using per-FPF thresholds):
    - battery < grid_connect_threshold: Connect to grid
    - battery <= shutdown_threshold: Shutdown non-critical consumers
    - battery <= 5%: Emergency shutdown (all non-critical)
    - battery > grid_disconnect_threshold: Can disconnect grid if solar/wind sufficient

    :param fpf_id: UUID of the FPF
    :param battery_level_wh: Current battery level in Wh
    :param max_capacity_wh: Maximum battery capacity in Wh (optional, uses FPF config if None)
    :return: EnergyState with recommended action
    """
    # Get FPF-specific energy configuration
    config = get_fpf_energy_config(fpf_id)
    
    # Use FPF config for max capacity if not explicitly provided
    if max_capacity_wh is None:
        max_capacity_wh = config['battery_max_wh']
    
    battery_percentage = calculate_battery_percentage(battery_level_wh, max_capacity_wh)

    # Get current consumption and production (including weather-based estimates)
    # Use live data from linked sensors when available
    total_consumption = get_total_consumption_by_fpf_id(fpf_id, active_only=True, use_live_data=True)
    total_production = get_current_power_output_with_weather(fpf_id)
    net_power = total_production - total_consumption

    # Check grid connection status
    grid_connected = False
    try:
        grid_source = get_grid_source(fpf_id)
        grid_connected = grid_source.isActive
    except Exception:
        pass

    # Extract thresholds from config
    grid_connect_threshold = config['grid_connect_threshold']
    shutdown_threshold = config['shutdown_threshold']
    warning_threshold = config['warning_threshold']
    grid_disconnect_threshold = config['grid_disconnect_threshold']

    # Determine action and consumers to shutdown
    action = EnergyAction.NORMAL
    consumers_to_shutdown = []
    status = "normal"
    message = "System operating normally"

    # Get all active consumers with individual shutdown thresholds
    all_consumers = get_active_energy_consumers_by_fpf_id(fpf_id)

    # Find consumers that should be shut down based on their individual thresholds
    consumers_by_individual_threshold = [
        c for c in all_consumers
        if c.shutdownThreshold > 0 and battery_percentage <= c.shutdownThreshold
    ]

    if battery_percentage <= 5:
        # Emergency: shutdown all non-critical
        action = EnergyAction.EMERGENCY_SHUTDOWN
        status = "critical"
        message = f"EMERGENCY: Battery critically low ({battery_percentage:.1f}%). Shutting down all non-critical consumers."
        consumer_groups = get_consumers_by_priority(fpf_id, CRITICAL_PRIORITY_THRESHOLD)
        consumers_to_shutdown = [str(c.id) for c in consumer_groups['non_critical']]

    elif battery_percentage <= shutdown_threshold:
        # Critical: connect grid AND shutdown low-priority consumers
        action = EnergyAction.SHUTDOWN_NON_CRITICAL
        status = "critical"
        message = f"CRITICAL: Battery at {battery_percentage:.1f}%. Connecting grid and reducing load."
        # Shutdown consumers with priority > 5 first
        consumer_groups = get_consumers_by_priority(fpf_id, 5)
        consumers_to_shutdown = [str(c.id) for c in consumer_groups['non_critical']]

    elif battery_percentage < grid_connect_threshold:
        # Low: connect to grid
        action = EnergyAction.CONNECT_GRID
        status = "warning"
        message = f"WARNING: Battery low ({battery_percentage:.1f}%). Grid connection required."
        # Also shutdown consumers with individual thresholds above current battery level
        consumers_to_shutdown = [str(c.id) for c in consumers_by_individual_threshold]

    elif battery_percentage < warning_threshold:
        # Warning level but not critical
        status = "warning"
        message = f"Battery level at {battery_percentage:.1f}%. Monitoring closely."
        if not grid_connected and net_power < 0:
            action = EnergyAction.CONNECT_GRID
            message += " Grid connection recommended due to power deficit."
        # Shutdown consumers with individual thresholds above current battery level
        consumers_to_shutdown = [str(c.id) for c in consumers_by_individual_threshold]

    else:
        # Normal operation
        status = "normal"
        if grid_connected and net_power > 0 and battery_percentage > grid_disconnect_threshold:
            # Can disconnect grid if we have surplus and battery above disconnect threshold
            action = EnergyAction.DISCONNECT_GRID
            message = f"Battery at {battery_percentage:.1f}% (above {grid_disconnect_threshold}% threshold) with power surplus. Grid disconnection possible."
        else:
            message = f"System operating normally. Battery at {battery_percentage:.1f}%."
        # Even in normal operation, shutdown consumers with individual thresholds above current battery level
        consumers_to_shutdown = [str(c.id) for c in consumers_by_individual_threshold]

    # Add individual threshold consumers to the shutdown list if not already there
    if consumers_by_individual_threshold and action == EnergyAction.NORMAL:
        # If we have consumers to shutdown due to individual thresholds, trigger shutdown action
        if consumers_to_shutdown:
            action = EnergyAction.SHUTDOWN_NON_CRITICAL
            if status == "normal":
                status = "warning"
            names = ", ".join([c.name for c in consumers_by_individual_threshold[:3]])
            if len(consumers_by_individual_threshold) > 3:
                names += f" (+{len(consumers_by_individual_threshold) - 3} more)"
            message = f"Shutting down consumers with individual thresholds: {names}"

    logger.info(
        f"Energy state evaluated for FPF {fpf_id}: {status} - {action.value}",
        extra={'resource_id': fpf_id}
    )

    return EnergyState(
        fpf_id=fpf_id,
        battery_level_wh=battery_level_wh,
        battery_percentage=battery_percentage,
        battery_max_wh=max_capacity_wh,
        total_consumption_watts=total_consumption,
        total_production_watts=total_production,
        net_power_watts=net_power,
        grid_connected=grid_connected,
        action=action,
        consumers_to_shutdown=consumers_to_shutdown,
        status=status,
        message=message
    )


def get_energy_state_summary(fpf_id: str, battery_level_wh: float) -> dict:
    """
    Get a JSON-serializable summary of the energy state
    :param fpf_id: UUID of the FPF
    :param battery_level_wh: Current battery level in Wh
    :return: Dictionary with energy state information
    """
    state = evaluate_energy_state(fpf_id, battery_level_wh)
    config = get_fpf_energy_config(fpf_id)

    return {
        "fpf_id": state.fpf_id,
        "battery": {
            "level_wh": state.battery_level_wh,
            "percentage": round(state.battery_percentage, 2),
            "max_wh": state.battery_max_wh,
        },
        "power": {
            "consumption_watts": state.total_consumption_watts,
            "production_watts": state.total_production_watts,
            "net_watts": state.net_power_watts,
        },
        "grid_connected": state.grid_connected,
        "action": state.action.value,
        "consumers_to_shutdown": [str(c) for c in state.consumers_to_shutdown],
        "status": state.status,
        "message": state.message,
        "thresholds": {
            "grid_connect": config['grid_connect_threshold'],
            "shutdown": config['shutdown_threshold'],
            "warning": config['warning_threshold'],
            "grid_disconnect": config['grid_disconnect_threshold'],
        }
    }


def should_connect_grid(fpf_id: str, battery_level_wh: float) -> bool:
    """
    Simple check if grid should be connected
    :param fpf_id: UUID of the FPF
    :param battery_level_wh: Current battery level in Wh
    :return: True if grid should be connected
    """
    state = evaluate_energy_state(fpf_id, battery_level_wh)
    return state.action in [EnergyAction.CONNECT_GRID, EnergyAction.SHUTDOWN_NON_CRITICAL, EnergyAction.EMERGENCY_SHUTDOWN]


def should_shutdown_consumers(fpf_id: str, battery_level_wh: float) -> list:
    """
    Get list of consumers that should be shutdown
    :param fpf_id: UUID of the FPF
    :param battery_level_wh: Current battery level in Wh
    :return: List of consumer IDs to shutdown
    """
    state = evaluate_energy_state(fpf_id, battery_level_wh)
    return state.consumers_to_shutdown


def estimate_runtime_hours(fpf_id: str, battery_level_wh: float) -> float:
    """
    Estimate remaining runtime in hours based on current consumption
    :param fpf_id: UUID of the FPF
    :param battery_level_wh: Current battery level in Wh
    :return: Estimated runtime in hours
    """
    total_consumption = get_total_consumption_by_fpf_id(fpf_id, active_only=True)
    total_production = get_current_power_output_by_fpf_id(fpf_id)
    net_consumption = total_consumption - total_production

    if net_consumption <= 0:
        return float('inf')  # Battery is charging or stable

    return battery_level_wh / net_consumption

