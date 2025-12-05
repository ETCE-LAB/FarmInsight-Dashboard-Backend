from farminsight_dashboard_backend.exceptions import NotFoundException
from farminsight_dashboard_backend.models import EnergySource, FPF
from farminsight_dashboard_backend.serializers.energy_source_serializer import EnergySourceSerializer
from farminsight_dashboard_backend.utils import get_logger

logger = get_logger()


def get_energy_source_by_id(source_id: str) -> EnergySource:
    """
    Get energy source by id
    :param source_id: UUID of the energy source
    :return: EnergySource
    :raises: NotFoundException
    """
    try:
        return EnergySource.objects.get(id=source_id)
    except EnergySource.DoesNotExist:
        raise NotFoundException(f'Energy source with id: {source_id} was not found.')


def get_energy_sources_by_fpf_id(fpf_id: str) -> list:
    """
    Get all energy sources for a specific FPF
    :param fpf_id: UUID of the FPF
    :return: List of EnergySource objects
    """
    return list(EnergySource.objects.filter(FPF_id=fpf_id))


def get_active_energy_sources_by_fpf_id(fpf_id: str) -> list:
    """
    Get all active energy sources for a specific FPF
    :param fpf_id: UUID of the FPF
    :return: List of active EnergySource objects
    """
    return list(EnergySource.objects.filter(FPF_id=fpf_id, isActive=True))


def get_energy_sources_by_type(fpf_id: str, source_type: str) -> list:
    """
    Get energy sources by type for a specific FPF
    :param fpf_id: UUID of the FPF
    :param source_type: Type of energy source (solar, wind, grid, etc.)
    :return: List of EnergySource objects of the specified type
    """
    return list(EnergySource.objects.filter(FPF_id=fpf_id, sourceType=source_type))


def create_energy_source(fpf_id: str, source_data: dict) -> EnergySource:
    """
    Create a new energy source for an FPF
    :param fpf_id: UUID of the FPF
    :param source_data: Dictionary with source data
    :return: Newly created EnergySource instance
    """
    try:
        fpf = FPF.objects.get(id=fpf_id)
    except FPF.DoesNotExist:
        raise ValueError("FPF with the given ID does not exist")

    serializer = EnergySourceSerializer(data=source_data, partial=True)
    serializer.is_valid(raise_exception=True)
    source = serializer.save(FPF=fpf)

    logger.info(f"Energy source '{source.name}' created successfully", extra={'resource_id': str(source.id)})
    return source


def update_energy_source(source_id: str, source_data: dict) -> EnergySourceSerializer:
    """
    Update an existing energy source
    :param source_id: UUID of the source to update
    :param source_data: New source data
    :return: Updated serializer
    """
    source = get_energy_source_by_id(source_id)
    serializer = EnergySourceSerializer(source, data=source_data, partial=True)
    if serializer.is_valid(raise_exception=True):
        serializer.save()
        logger.info(f"Energy source '{source.name}' updated successfully", extra={'resource_id': str(source.id)})
        return serializer


def delete_energy_source(source: EnergySource) -> None:
    """
    Delete an energy source
    :param source: EnergySource to delete
    """
    source_name = source.name
    source_id = str(source.id)
    source.delete()
    logger.info(f"Energy source '{source_name}' deleted successfully", extra={'resource_id': source_id})


def get_live_output_watts(source: EnergySource) -> float:
    """
    Get the current power output for a source.
    If a sensor is linked, fetches live data from InfluxDB.
    Otherwise, returns the static currentOutputWatts value.

    :param source: EnergySource instance
    :return: Current power output in watts
    """
    if source.sensor and source.sensor.isActive:
        try:
            from farminsight_dashboard_backend.services.influx_services import InfluxDBManager

            influx = InfluxDBManager.get_instance()
            measurements = influx.fetch_latest_sensor_measurements(
                fpf_id=str(source.FPF.id),
                sensor_ids=[str(source.sensor.id)]
            )

            sensor_data = measurements.get(str(source.sensor.id))
            if sensor_data and 'value' in sensor_data:
                return min(float(sensor_data['value']), source.maxOutputWatts)
        except Exception as e:
            logger.warning(f"Could not fetch live output for source {source.name}: {e}")

    return source.currentOutputWatts


def get_total_available_power_by_fpf_id(fpf_id: str, active_only: bool = True) -> float:
    """
    Calculate total available power output for an FPF
    :param fpf_id: UUID of the FPF
    :param active_only: Only include active sources
    :return: Total max output in watts
    """
    sources = EnergySource.objects.filter(FPF_id=fpf_id)
    if active_only:
        sources = sources.filter(isActive=True)
    return sum(s.maxOutputWatts for s in sources)


def get_current_power_output_by_fpf_id(fpf_id: str, use_live_data: bool = False) -> float:
    """
    Get current total power output for an FPF
    :param fpf_id: UUID of the FPF
    :param use_live_data: If True, fetch live data from linked sensors
    :return: Current total output in watts
    """
    sources = EnergySource.objects.filter(FPF_id=fpf_id, isActive=True)

    if use_live_data:
        return sum(get_live_output_watts(s) for s in sources)

    return sum(s.currentOutputWatts for s in sources)


def update_source_output(source_id: str, current_output: float) -> EnergySource:
    """
    Update the current output of an energy source
    :param source_id: UUID of the source
    :param current_output: Current output in watts
    :return: Updated EnergySource
    """
    source = get_energy_source_by_id(source_id)
    source.currentOutputWatts = min(current_output, source.maxOutputWatts)
    source.save()
    return source


def get_grid_source(fpf_id: str) -> EnergySource:
    """
    Get the grid connection source for an FPF
    :param fpf_id: UUID of the FPF
    :return: Grid EnergySource or None
    :raises: NotFoundException if no grid source exists
    """
    try:
        return EnergySource.objects.get(FPF_id=fpf_id, sourceType='grid')
    except EnergySource.DoesNotExist:
        raise NotFoundException(f'No grid connection found for FPF: {fpf_id}')
    except EnergySource.MultipleObjectsReturned:
        # Return the first active one if multiple exist
        return EnergySource.objects.filter(FPF_id=fpf_id, sourceType='grid', isActive=True).first()


def connect_grid(fpf_id: str) -> bool:
    """
    Connect to the grid by triggering the grid source's controllable action.

    :param fpf_id: UUID of the FPF
    :return: True if action was triggered, False otherwise
    """
    try:
        grid_source = get_grid_source(fpf_id)
    except NotFoundException:
        logger.warning(f"No grid source found for FPF {fpf_id}")
        return False

    if not grid_source.controllableAction:
        logger.warning(f"Grid source {grid_source.name} has no linked controllable action")
        return False

    if not grid_source.controllableAction.isActive:
        logger.warning(f"Grid controllable action is not active")
        return False

    try:
        from farminsight_dashboard_backend.models import ActionTrigger, ActionQueue
        from farminsight_dashboard_backend.services.action_queue_services import is_already_enqueued

        trigger = ActionTrigger.objects.create(
            name=f"Energy Management: Connect Grid",
            type="auto",
            actionValue="Connect",  # or "On" depending on the action script
            action=grid_source.controllableAction,
            isActive=True
        )

        if not is_already_enqueued(trigger.id):
            ActionQueue.objects.create(
                action=grid_source.controllableAction,
                trigger=trigger
            )
            logger.info(f"Enqueued grid connection for FPF {fpf_id}")

            grid_source.isActive = True
            grid_source.save(update_fields=['isActive'])
            return True

    except Exception as e:
        logger.error(f"Failed to connect grid for FPF {fpf_id}: {e}")

    return False


def disconnect_grid(fpf_id: str) -> bool:
    """
    Disconnect from the grid by triggering the grid source's controllable action.

    :param fpf_id: UUID of the FPF
    :return: True if action was triggered, False otherwise
    """
    try:
        grid_source = get_grid_source(fpf_id)
    except NotFoundException:
        logger.warning(f"No grid source found for FPF {fpf_id}")
        return False

    if not grid_source.controllableAction:
        logger.warning(f"Grid source {grid_source.name} has no linked controllable action")
        return False

    if not grid_source.controllableAction.isActive:
        logger.warning(f"Grid controllable action is not active")
        return False

    try:
        from farminsight_dashboard_backend.models import ActionTrigger, ActionQueue
        from farminsight_dashboard_backend.services.action_queue_services import is_already_enqueued

        trigger = ActionTrigger.objects.create(
            name=f"Energy Management: Disconnect Grid",
            type="auto",
            actionValue="Disconnect",  # or "Off" depending on the action script
            action=grid_source.controllableAction,
            isActive=True
        )

        if not is_already_enqueued(trigger.id):
            ActionQueue.objects.create(
                action=grid_source.controllableAction,
                trigger=trigger
            )
            logger.info(f"Enqueued grid disconnection for FPF {fpf_id}")

            grid_source.isActive = False
            grid_source.save(update_fields=['isActive'])
            return True

    except Exception as e:
        logger.error(f"Failed to disconnect grid for FPF {fpf_id}: {e}")

    return False

