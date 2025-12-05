from farminsight_dashboard_backend.exceptions import NotFoundException
from farminsight_dashboard_backend.models import EnergyConsumer, FPF
from farminsight_dashboard_backend.serializers.energy_consumer_serializer import EnergyConsumerSerializer
from farminsight_dashboard_backend.utils import get_logger

logger = get_logger()


def get_energy_consumer_by_id(consumer_id: str) -> EnergyConsumer:
    """
    Get energy consumer by id
    :param consumer_id: UUID of the energy consumer
    :return: EnergyConsumer
    :raises: NotFoundException
    """
    try:
        return EnergyConsumer.objects.get(id=consumer_id)
    except EnergyConsumer.DoesNotExist:
        raise NotFoundException(f'Energy consumer with id: {consumer_id} was not found.')


def get_energy_consumers_by_fpf_id(fpf_id: str) -> list:
    """
    Get all energy consumers for a specific FPF
    :param fpf_id: UUID of the FPF
    :return: List of EnergyConsumer objects
    """
    return list(EnergyConsumer.objects.filter(FPF_id=fpf_id))


def get_active_energy_consumers_by_fpf_id(fpf_id: str) -> list:
    """
    Get all active energy consumers for a specific FPF
    :param fpf_id: UUID of the FPF
    :return: List of active EnergyConsumer objects
    """
    return list(EnergyConsumer.objects.filter(FPF_id=fpf_id, isActive=True))


def create_energy_consumer(fpf_id: str, consumer_data: dict) -> EnergyConsumer:
    """
    Create a new energy consumer for an FPF
    :param fpf_id: UUID of the FPF
    :param consumer_data: Dictionary with consumer data
    :return: Newly created EnergyConsumer instance
    """
    try:
        fpf = FPF.objects.get(id=fpf_id)
    except FPF.DoesNotExist:
        raise ValueError("FPF with the given ID does not exist")

    serializer = EnergyConsumerSerializer(data=consumer_data, partial=True)
    serializer.is_valid(raise_exception=True)
    consumer = serializer.save(FPF=fpf)

    logger.info(f"Energy consumer '{consumer.name}' created successfully", extra={'resource_id': str(consumer.id)})
    return consumer


def update_energy_consumer(consumer_id: str, consumer_data: dict) -> EnergyConsumerSerializer:
    """
    Update an existing energy consumer
    :param consumer_id: UUID of the consumer to update
    :param consumer_data: New consumer data
    :return: Updated serializer
    """
    consumer = get_energy_consumer_by_id(consumer_id)
    serializer = EnergyConsumerSerializer(consumer, data=consumer_data, partial=True)
    if serializer.is_valid(raise_exception=True):
        serializer.save()
        logger.info(f"Energy consumer '{consumer.name}' updated successfully", extra={'resource_id': str(consumer.id)})
        return serializer


def delete_energy_consumer(consumer: EnergyConsumer) -> None:
    """
    Delete an energy consumer
    :param consumer: EnergyConsumer to delete
    """
    consumer_name = consumer.name
    consumer_id = str(consumer.id)
    consumer.delete()
    logger.info(f"Energy consumer '{consumer_name}' deleted successfully", extra={'resource_id': consumer_id})


def get_live_consumption_watts(consumer: EnergyConsumer) -> float:
    """
    Get the current power consumption for a consumer.
    If a sensor is linked, fetches live data from InfluxDB.
    Otherwise, returns the static consumptionWatts value.

    :param consumer: EnergyConsumer instance
    :return: Current power consumption in watts
    """
    if consumer.sensor and consumer.sensor.isActive:
        try:
            from farminsight_dashboard_backend.services.influx_services import InfluxDBManager

            influx = InfluxDBManager.get_instance()
            measurements = influx.fetch_latest_sensor_measurements(
                fpf_id=str(consumer.FPF.id),
                sensor_ids=[str(consumer.sensor.id)]
            )

            sensor_data = measurements.get(str(consumer.sensor.id))
            if sensor_data and 'value' in sensor_data:
                return float(sensor_data['value'])
        except Exception as e:
            logger.warning(f"Could not fetch live consumption for consumer {consumer.name}: {e}")

    return consumer.consumptionWatts


def get_total_consumption_by_fpf_id(fpf_id: str, active_only: bool = True, use_live_data: bool = False) -> float:
    """
    Calculate total power consumption for an FPF
    :param fpf_id: UUID of the FPF
    :param active_only: Only include active consumers
    :param use_live_data: If True, fetch live data from linked sensors
    :return: Total consumption in watts
    """
    consumers = EnergyConsumer.objects.filter(FPF_id=fpf_id)
    if active_only:
        consumers = consumers.filter(isActive=True)

    if use_live_data:
        return sum(get_live_consumption_watts(c) for c in consumers)

    return sum(c.consumptionWatts for c in consumers)


def get_consumers_by_priority(fpf_id: str, priority_threshold: int = 5) -> dict:
    """
    Get consumers grouped by priority threshold
    :param fpf_id: UUID of the FPF
    :param priority_threshold: Threshold to split critical vs non-critical
    :return: Dict with 'critical' and 'non_critical' consumer lists
    """
    consumers = EnergyConsumer.objects.filter(FPF_id=fpf_id, isActive=True)
    return {
        'critical': list(consumers.filter(priority__lte=priority_threshold)),
        'non_critical': list(consumers.filter(priority__gt=priority_threshold))
    }


def get_controllable_consumers(fpf_id: str) -> list:
    """
    Get all consumers that have a linked controllable action.
    These are the consumers that can be automatically controlled.

    :param fpf_id: UUID of the FPF
    :return: List of EnergyConsumer objects with linked controllableAction
    """
    return list(EnergyConsumer.objects.filter(
        FPF_id=fpf_id,
        isActive=True,
        controllableAction__isnull=False,
        controllableAction__isActive=True
    ))


def shutdown_consumer(consumer: EnergyConsumer) -> bool:
    """
    Shutdown an energy consumer by triggering its linked controllable action.

    :param consumer: EnergyConsumer to shutdown
    :return: True if action was triggered, False otherwise
    """
    if not consumer.controllableAction:
        logger.warning(f"Consumer {consumer.name} has no linked controllable action - cannot shutdown")
        return False

    if not consumer.controllableAction.isActive:
        logger.warning(f"Controllable action for consumer {consumer.name} is not active")
        return False

    try:
        from farminsight_dashboard_backend.models import ActionTrigger, ActionQueue
        from farminsight_dashboard_backend.services.action_queue_services import is_already_enqueued

        # Create a system trigger for automatic shutdown
        trigger = ActionTrigger.objects.create(
            name=f"Energy Management: Shutdown {consumer.name}",
            type="auto",
            actionValue="Off",
            action=consumer.controllableAction,
            isActive=True
        )

        if not is_already_enqueued(trigger.id):
            ActionQueue.objects.create(
                action=consumer.controllableAction,
                trigger=trigger
            )
            logger.info(f"Enqueued shutdown for consumer {consumer.name}")

            # Update consumer isActive status
            consumer.isActive = False
            consumer.save(update_fields=['isActive'])
            return True

    except Exception as e:
        logger.error(f"Failed to shutdown consumer {consumer.name}: {e}")

    return False


def activate_consumer(consumer: EnergyConsumer) -> bool:
    """
    Activate an energy consumer by triggering its linked controllable action.

    :param consumer: EnergyConsumer to activate
    :return: True if action was triggered, False otherwise
    """
    if not consumer.controllableAction:
        logger.warning(f"Consumer {consumer.name} has no linked controllable action - cannot activate")
        return False

    if not consumer.controllableAction.isActive:
        logger.warning(f"Controllable action for consumer {consumer.name} is not active")
        return False

    try:
        from farminsight_dashboard_backend.models import ActionTrigger, ActionQueue
        from farminsight_dashboard_backend.services.action_queue_services import is_already_enqueued

        # Create a system trigger for automatic activation
        trigger = ActionTrigger.objects.create(
            name=f"Energy Management: Activate {consumer.name}",
            type="auto",
            actionValue="On",
            action=consumer.controllableAction,
            isActive=True
        )

        if not is_already_enqueued(trigger.id):
            ActionQueue.objects.create(
                action=consumer.controllableAction,
                trigger=trigger
            )
            logger.info(f"Enqueued activation for consumer {consumer.name}")

            # Update consumer isActive status
            consumer.isActive = True
            consumer.save(update_fields=['isActive'])
            return True

    except Exception as e:
        logger.error(f"Failed to activate consumer {consumer.name}: {e}")

    return False

