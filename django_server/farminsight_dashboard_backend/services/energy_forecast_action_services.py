"""
Energy Forecast Action Service

Analyzes SoC forecasts from AI models and schedules consumer shutdowns based on 
individual forecastShutdownThreshold settings.

This provides proactive energy management - consumers are shut down BEFORE 
the battery reaches critical levels, based on AI predictions.
"""

import json
from datetime import timedelta
from django.utils import timezone
from datetime import datetime

from farminsight_dashboard_backend.models import EnergyConsumer, ActionTrigger, ActionQueue, ControllableAction
from farminsight_dashboard_backend.services.action_queue_services import is_already_enqueued, process_action_queue
from farminsight_dashboard_backend.utils import get_logger

logger = get_logger()


def schedule_forecast_based_shutdowns(fpf_id: str, soc_forecast: list, battery_max_wh: float):
    """
    Analyze SoC forecast and schedule consumer shutdowns based on individual thresholds.
    
    This function is called after the AI model returns a battery SoC forecast.
    For each consumer with a forecastShutdownThreshold set, it finds when the 
    predicted SoC will drop to or below that threshold and schedules the shutdown.
    
    :param fpf_id: FPF ID
    :param soc_forecast: List of {timestamp, value_wh} predictions from AI model
    :param battery_max_wh: Maximum battery capacity for percentage calculation
    """
    if not soc_forecast:
        logger.debug(f"No SoC forecast data for FPF {fpf_id}")
        return
    
    if battery_max_wh <= 0:
        logger.warning(f"Invalid battery_max_wh ({battery_max_wh}) for FPF {fpf_id}")
        return
    
    # Get all consumers with forecast thresholds configured
    consumers = EnergyConsumer.objects.filter(
        FPF_id=fpf_id,
        isActive=True,
        forecastShutdownThreshold__gt=0,  # Only consumers with forecast threshold set
        controllableAction__isnull=False   # Only consumers with linked action
    ).select_related('controllableAction')
    
    if not consumers.exists():
        logger.debug(f"No consumers with forecast thresholds for FPF {fpf_id}")
        return
    
    logger.info(f"Processing forecast-based shutdowns for FPF {fpf_id}: {consumers.count()} consumers with thresholds")
    
    for consumer in consumers:
        try:
            _process_consumer_forecast(consumer, soc_forecast, battery_max_wh)
        except Exception as e:
            logger.error(f"Error processing forecast for consumer {consumer.name}: {e}")


def _process_consumer_forecast(consumer: EnergyConsumer, soc_forecast: list, battery_max_wh: float):
    """
    Process a single consumer against the SoC forecast.
    
    :param consumer: EnergyConsumer with forecastShutdownThreshold set
    :param soc_forecast: List of {timestamp, value_wh} predictions
    :param battery_max_wh: Maximum battery capacity
    """
    threshold_percent = consumer.forecastShutdownThreshold
    buffer_days = consumer.forecastBufferDays
    
    # Find first timestamp where SoC drops to or below threshold
    breach_time = None
    breach_soc = None
    
    for point in soc_forecast:
        value_wh = point.get('value_wh') or point.get('value', 0)
        soc_percent = (value_wh / battery_max_wh) * 100
        
        if soc_percent <= threshold_percent:
            # Found the threshold breach point
            breach_time = _parse_timestamp(point['timestamp'])
            breach_soc = soc_percent
            break
    
    if breach_time is None:
        logger.debug(
            f"Consumer {consumer.name}: SoC never drops to {threshold_percent}% in forecast period"
        )
        return
    
    # Calculate shutdown time (apply buffer)
    shutdown_time = breach_time - timedelta(days=buffer_days)
    
    # Don't schedule past actions - execute immediately instead
    now = timezone.now()
    if shutdown_time < now:
        logger.info(
            f"Consumer {consumer.name}: Predicted breach at {breach_time.isoformat()}, "
            f"shutdown time {shutdown_time.isoformat()} is in the past. Executing in 10 seconds."
        )
        shutdown_time = now + timedelta(seconds=10)
    
    # Check if we already have a scheduled action for this consumer
    existing_trigger = ActionTrigger.objects.filter(
        action=consumer.controllableAction,
        type="forecast",
        isActive=True,
    ).filter(
        triggerLogic__contains=str(consumer.id)
    ).first()
    
    if existing_trigger:
        logger.debug(
            f"Consumer {consumer.name}: Already has scheduled forecast action (trigger {existing_trigger.id}), skipping"
        )
        return
    
    # Create the scheduled action
    _schedule_consumer_shutdown(
        consumer=consumer,
        shutdown_time=shutdown_time,
        threshold_percent=threshold_percent,
        breach_time=breach_time,
        buffer_days=buffer_days,
        predicted_soc=breach_soc
    )


def _schedule_consumer_shutdown(
    consumer: EnergyConsumer,
    shutdown_time: datetime,
    threshold_percent: int,
    breach_time: datetime,
    buffer_days: int,
    predicted_soc: float
):
    """
    Create an ActionTrigger and schedule it for execution.
    
    :param consumer: Consumer to shut down
    :param shutdown_time: When to execute the shutdown
    :param threshold_percent: The consumer's threshold that was predicted to be reached
    :param breach_time: When the threshold will actually be reached
    :param buffer_days: How many days before breach we're shutting down
    :param predicted_soc: The actual predicted SoC percentage at breach
    """
    from farminsight_dashboard_backend.services.forecast_action_scheduler_services import ForecastActionScheduler
    
    scheduler = ForecastActionScheduler.get_instance()
    
    # Create trigger with detailed metadata
    trigger = ActionTrigger.objects.create(
        name=f"Forecast Shutdown: {consumer.name}",
        type="forecast",
        actionValueType="string",
        actionValue="Off",
        triggerLogic=json.dumps({
            "consumer_id": str(consumer.id),
            "consumer_name": consumer.name,
            "threshold_percent": threshold_percent,
            "predicted_breach_time": breach_time.isoformat(),
            "predicted_soc_percent": round(predicted_soc, 1),
            "buffer_days": buffer_days,
            "scheduled_time": shutdown_time.isoformat()
        }),
        description=f"AI predicted SoC will reach {threshold_percent}% at {breach_time.strftime('%Y-%m-%d %H:%M')} - shutting down {buffer_days} days early",
        isActive=True,
        action=consumer.controllableAction
    )
    
    # Schedule the execution
    scheduler.schedule_action(
        shutdown_time,
        _execute_consumer_shutdown,
        str(consumer.controllableAction.id),
        str(trigger.id)
    )
    
    logger.info(
        f"Scheduled forecast shutdown for {consumer.name} at {shutdown_time.isoformat()} "
        f"(predicted {threshold_percent}% at {breach_time.strftime('%Y-%m-%d %H:%M')}, buffer: {buffer_days} days)"
    )


def _execute_consumer_shutdown(action_id: str, trigger_id: str):
    """
    Execute the scheduled consumer shutdown by enqueueing the action.
    
    This is called by the ForecastActionScheduler at the scheduled time.
    
    :param action_id: ControllableAction ID
    :param trigger_id: ActionTrigger ID
    """
    try:
        action = ControllableAction.objects.get(id=action_id)
        trigger = ActionTrigger.objects.get(id=trigger_id)
        
        # Check if already executed
        if not trigger.isActive:
            logger.debug(f"Trigger {trigger_id} already inactive, skipping")
            return
        
        # Enqueue the action
        if not is_already_enqueued(trigger.id):
            ActionQueue.objects.create(action=action, trigger=trigger)
            logger.info(f"Executing forecast shutdown: {action.name}")
            
            # Mark trigger as executed
            trigger.isActive = False
            trigger.save()
            
            # Process the action queue
            process_action_queue()
        else:
            logger.debug(f"Action {action.name} already enqueued")
        
    except ControllableAction.DoesNotExist:
        logger.error(f"ControllableAction {action_id} not found")
    except ActionTrigger.DoesNotExist:
        logger.error(f"ActionTrigger {trigger_id} not found")
    except Exception as e:
        logger.error(f"Failed to execute forecast shutdown {action_id}: {e}")


def _parse_timestamp(ts: str) -> datetime:
    """
    Parse ISO timestamp to timezone-aware datetime.
    
    Handles formats:
    - "2026-01-08T07:00:00Z"
    - "2026-01-08T07:00:00+00:00"
    - "2026-01-08T07:00:00"
    
    :param ts: ISO timestamp string
    :return: Timezone-aware datetime
    """
    from django.utils.timezone import make_aware, is_aware
    
    if ts.endswith('Z'):
        ts = ts[:-1] + '+00:00'
    
    try:
        dt = datetime.fromisoformat(ts)
    except ValueError:
        # Try alternative format
        dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S")
    
    if not is_aware(dt):
        dt = make_aware(dt)
    
    return dt


def cancel_forecast_shutdown(consumer_id: str):
    """
    Cancel any scheduled forecast-based shutdown for a consumer.
    
    Called when a consumer is manually turned on or thresholds are changed.
    
    :param consumer_id: EnergyConsumer ID
    """
    triggers = ActionTrigger.objects.filter(
        type="forecast",
        isActive=True,
        triggerLogic__contains=consumer_id
    )
    
    count = triggers.count()
    if count > 0:
        triggers.update(isActive=False)
        logger.info(f"Cancelled {count} forecast shutdown(s) for consumer {consumer_id}")


def get_scheduled_forecast_actions(fpf_id: str) -> list:
    """
    Get all scheduled forecast actions for an FPF.
    
    Useful for displaying upcoming automated shutdowns in the UI.
    
    :param fpf_id: FPF ID
    :return: List of scheduled action details
    """
    consumers = EnergyConsumer.objects.filter(
        FPF_id=fpf_id,
        controllableAction__isnull=False
    ).values_list('controllableAction_id', flat=True)
    
    triggers = ActionTrigger.objects.filter(
        action_id__in=consumers,
        type="forecast",
        isActive=True
    ).select_related('action')
    
    result = []
    for trigger in triggers:
        try:
            logic = json.loads(trigger.triggerLogic) if trigger.triggerLogic else {}
            result.append({
                'trigger_id': str(trigger.id),
                'consumer_name': logic.get('consumer_name', 'Unknown'),
                'threshold_percent': logic.get('threshold_percent'),
                'predicted_breach_time': logic.get('predicted_breach_time'),
                'scheduled_time': logic.get('scheduled_time'),
                'buffer_days': logic.get('buffer_days'),
                'action_name': trigger.action.name if trigger.action else None
            })
        except json.JSONDecodeError:
            continue
    
    return result
