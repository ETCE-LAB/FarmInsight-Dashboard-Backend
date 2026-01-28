from datetime import datetime, timedelta
from django.utils import timezone

from farminsight_dashboard_backend.models import FPF, Sensor
from farminsight_dashboard_backend.utils import get_logger

logger = get_logger()


def check_all_fpf_health():
    """
    Checks the health of all FPFs by checking if any sensor has received
    data recently from InfluxDB. This is more reliable than pinging the
    FPF backend directly, as it works even when the Dashboard Backend
    cannot reach the FPF Backend network.
    
    An FPF is considered active if:
    - It has at least one sensor with recent measurements (within 2x the sensor's interval), OR
    - It has no sensors configured (new FPF, keep it as active by default)
    """
    from farminsight_dashboard_backend.services import InfluxDBManager
    
    fpfs = FPF.objects.all()
    logger.info(f'Checking health of {len(fpfs)} FPFs based on sensor data freshness...')

    influx = InfluxDBManager.get_instance()
    
    for fpf in fpfs:
        try:
            is_active = check_fpf_health(fpf, influx)
            
            # Only update the database if the status has changed
            if fpf.isActive != is_active:
                fpf.isActive = is_active
                fpf.save()
                status_str = "online" if is_active else "offline"
                logger.info(f'FPF {fpf.name} marked as {status_str}.')
        except Exception as e:
            # On error, don't change the status (keep current state)
            logger.warning(f'Error checking FPF {fpf.name} health: {type(e).__name__}: {e}')

    logger.info('Successfully updated FPF health statuses.')


def check_fpf_health(fpf: FPF, influx) -> bool:
    """
    Check if a single FPF is active based on sensor data freshness.
    
    Returns True (active) if:
    - Any sensor has received data within 2x its measurement interval
    - The FPF has no sensors (new FPF, considered active by default)
    - InfluxDB is not available (fail-open, keep FPF as active)
    
    Returns False (inactive) if:
    - All sensors have stale data (no measurements within 2x their intervals)
    """
    sensors = Sensor.objects.filter(FPF=fpf, isActive=True)
    
    # If no active sensors, consider FPF as active (could be newly created or in setup)
    if not sensors.exists():
        logger.debug(f'FPF {fpf.name} has no active sensors, marking as active by default.')
        return True
    
    sensor_ids = [str(sensor.id) for sensor in sensors]
    
    try:
        # Fetch latest measurements for all sensors at once
        latest_measurements = influx.fetch_latest_sensor_measurements(str(fpf.id), sensor_ids)
    except Exception as e:
        # If InfluxDB is not available, fail-open (keep as active)
        logger.warning(f'Could not fetch sensor data for FPF {fpf.name}: {e}. Keeping as active.')
        return True
    
    now = timezone.now()
    
    # Check if any sensor has recent data
    for sensor in sensors:
        sensor_id = str(sensor.id)
        measurement = latest_measurements.get(sensor_id)
        
        if measurement:
            try:
                measured_at_str = measurement.get('measuredAt', '')
                if measured_at_str:
                    measured_at = datetime.fromisoformat(measured_at_str.replace('Z', '+00:00'))
                    # Allow 2x the interval as tolerance (plus 5 min buffer)
                    max_age = timedelta(seconds=sensor.intervalSeconds * 2 + 300)
                    
                    if now - measured_at < max_age:
                        logger.debug(f'FPF {fpf.name} sensor {sensor.name} has fresh data.')
                        return True
            except (ValueError, TypeError) as e:
                logger.debug(f'Error parsing measurement time for sensor {sensor.name}: {e}')
                continue
    
    # No fresh data found from any sensor
    logger.info(f'FPF {fpf.name} has no fresh sensor data, marking as offline.')
    return False