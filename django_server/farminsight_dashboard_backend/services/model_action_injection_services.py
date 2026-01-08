import json
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.base import STATE_RUNNING
from apscheduler.triggers.date import DateTrigger
from django.utils.timezone import make_aware
from django.utils.timezone import make_aware

from farminsight_dashboard_backend.models import (
    ActionTrigger,
    ActionQueue,
    ControllableAction,
    ResourceManagementModel,
    ActionMapping,
)
from farminsight_dashboard_backend.utils import get_logger
from farminsight_dashboard_backend.services import process_action_queue

logger = get_logger()


class ForecastActionScheduler:
    """Scheduler for injecting model-predicted actions into the queue."""
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_scheduler"):
            self._scheduler = BackgroundScheduler()
        if self._scheduler.state != STATE_RUNNING:
            try:
                self._scheduler.start()
                logger.info("ForecastActionScheduler started.")
            except Exception as e:
                logger.warning(f"ForecastActionScheduler already running: {e}")

    def schedule_action(self, run_at, fn, *args):
        self._scheduler.add_job(
            fn,
            trigger=DateTrigger(run_date=run_at),
            args=args,
            misfire_grace_time=30,
            replace_existing=False,
        )


def _infer_value_type_and_str(val):
    if isinstance(val, bool):
        return "boolean", str(val).lower()
    if isinstance(val, int):
        return "integer", str(val)
    if isinstance(val, float):
        return "float", str(val)
    return "string", str(val)


def _parse_timestamp_aware(ts: str):
    # Accepts "....Z" or ISO8601 with offset
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return dt if dt.tzinfo else make_aware(dt)


def _enqueue_forecast_action(controllable_action_id: str, trigger_id: str):
    try:
        action = ControllableAction.objects.get(id=controllable_action_id)
        trigger = ActionTrigger.objects.get(id=trigger_id)
        ActionQueue.objects.create(action=action, trigger=trigger)
        logger.info(f"Forecast action '{action.name}' enqueued.")
        process_action_queue()
    except Exception as e:
        logger.error(f"Failed to enqueue forecast action {controllable_action_id}: {e}")


def inject_model_actions_into_queue(model_id: str, model_actions: list[dict]):
    """
    Inject forecast actions for the given model:
    - Resolve ControllableAction via ActionMapping (per model)
    - Only consider actions for the model.activeScenario
    - Schedule execution at the provided timestamp
    - Put the 'value' into ActionTrigger.actionValue
    """
    scheduler = ForecastActionScheduler.get_instance()

    try:
        model = ResourceManagementModel.objects.get(id=model_id)
    except ResourceManagementModel.DoesNotExist:
        logger.warning(f"ResourceManagementModel {model_id} not found.")
        return

    active_scenario = (model.activeScenario or "").strip()
    if not active_scenario:
        logger.info(f"Model {model.name} has no activeScenario set; no actions will be scheduled.")
        return

    for scenario in model_actions or []:
        scenario_name = (scenario.get("name") or "").strip()
        if scenario_name.lower() != active_scenario.lower():
            # skip actions from other scenarios
            continue

        for action_entry in scenario.get("value", []):
            action_name = action_entry.get("action")
            timestamp_str = action_entry.get("timestamp")
            action_value = action_entry.get("value")

            if not action_name or not timestamp_str:
                continue

            # Resolve mapping: per-model mapping from model action_name -> ControllableAction
            mapping = (
                ActionMapping.objects
                .filter(resource_management_model=model, action_name=action_name)
                .select_related("controllable_action")
                .first()
            )
            if not mapping:
                logger.warning(
                    f"No ActionMapping for model '{model.name}' "
                    f"and action_name='{action_name}'. Skipping."
                )
                continue

            controllable_action = mapping.controllable_action
            if not controllable_action or not controllable_action.isActive:
                logger.info(
                    f"Mapped ControllableAction inactive or missing for '{action_name}' on model '{model.name}'."
                )
                continue

            # Parse schedule time
            try:
                run_at = _parse_timestamp_aware(timestamp_str)
            except Exception:
                logger.error(f"Invalid timestamp format: {timestamp_str}")
                continue

            # Deduplicate (same action, same timestamp, same value)
            value_type, value_str = _infer_value_type_and_str(action_value)
            dup_exists = ActionTrigger.objects.filter(
                type="forecast",
                action=controllable_action,
                actionValue=value_str,
                triggerLogic__contains=timestamp_str,
                isActive=True,
            ).exists()
            if dup_exists:
                logger.info(
                    f"Duplicate forecast trigger exists for action='{controllable_action.name}' "
                    f"at '{timestamp_str}' with value '{value_str}'. Skipping."
                )
                continue

            # Create synthetic trigger
            trigger = ActionTrigger.objects.create(
                type="forecast",
                actionValueType=value_type,
                actionValue=value_str,
                triggerLogic=json.dumps(
                    {"timestamp": timestamp_str, "source": "forecast_model", "scenario": scenario_name}
                ),
                description=f"Forecast-injected ({scenario_name})",
                isActive=True,
                action=controllable_action,
            )

            # Schedule the enqueue at the exact time
            scheduler.schedule_action(run_at, _enqueue_forecast_action, str(controllable_action.id), str(trigger.id))
            logger.info(
                f"Scheduled forecast action '{controllable_action.name}' for {run_at.isoformat()} "
                f"(scenario='{scenario_name}', value='{value_str}')"
            )
