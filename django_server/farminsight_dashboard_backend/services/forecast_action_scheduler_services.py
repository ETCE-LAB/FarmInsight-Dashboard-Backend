import threading
from datetime import timedelta, datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from django.utils import timezone
from farminsight_dashboard_backend.models import ActionTrigger, ActionQueue
from farminsight_dashboard_backend.services import process_action_queue
from farminsight_dashboard_backend.utils import get_logger

logger = get_logger()


class ForecastActionScheduler:
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __init__(self):
        if not getattr(self, "_initialized", False):
            self._scheduler = BackgroundScheduler()
            self._initialized = True

    def start(self):
        """Start the scheduler and periodic cleanup task."""
        self._scheduler.add_job(
            self.cleanup_old_forecast_triggers,
            trigger="interval",
            hours=6,  # cleanup every 6 hours
            id="cleanup_forecast_triggers",
            replace_existing=True,
        )
        self._scheduler.start()
        logger.info("ForecastActionScheduler started.")

    def schedule_forecast_chain(self, action, forecast_actions: list[dict]):
        """
        Schedule the next forecast action in the list.
        If the list is empty, nothing is scheduled.
        """
        # Convert timestamps to datetime if needed
        for entry in forecast_actions:
            ts = entry.get("timestamp")
            if isinstance(ts, str):
                try:
                    entry["timestamp"] = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except Exception:
                    entry["timestamp"] = timezone.now()

        now = timezone.now()
        upcoming = []
        for entry in forecast_actions:
            ts = entry["timestamp"]
            if ts.tzinfo is None:
                ts = timezone.make_aware(ts, timezone=timezone.utc)
            if ts > now:
                upcoming.append(entry)

        if not upcoming:
            logger.debug(f"No upcoming forecast actions for {action.name}")
            return

        # Sort by soonest timestamp
        upcoming.sort(key=lambda e: e["timestamp"])
        next_action = upcoming[0]
        timestamp = next_action["timestamp"]
        value = next_action["value"]

        # Remove existing forecast trigger for this action
        ActionTrigger.objects.filter(action=action, type="forecast").delete()

        # Create a one-shot forecast trigger
        trigger = ActionTrigger.objects.create(
            type="forecast",
            actionValueType="float",
            actionValue=str(value),
            triggerLogic=f'{{"timestamp": "{timestamp.isoformat()}"}}',
            description=f"Forecast action for {action.name} at {timestamp}",
            isActive=True,
            action=action
        )

        self._scheduler.add_job(
            func=self._execute_forecast_action,
            trigger=DateTrigger(run_date=timestamp),
            args=[trigger.id, forecast_actions],
            id=f"forecast_trigger_{action.id}",
            replace_existing=True,
        )

        logger.info(f"Scheduled forecast action '{action.name}' at {timestamp} (value={value}).")

    def _execute_forecast_action(self, trigger_id, forecast_actions):
        """Executes a forecast action and schedules the next one."""
        try:
            trigger = ActionTrigger.objects.get(id=trigger_id)
            action = trigger.action

            logger.info(f"Executing forecast action for {action.name}")

            # Add to queue and execute
            ActionQueue.objects.create(action=action, trigger=trigger)
            process_action_queue()

            trigger.isActive = False
            trigger.save(update_fields=["isActive"])

            # Schedule the next one (chain)
            now_time = timezone.now()
            remaining = []

            for f in forecast_actions:
                ts = f["timestamp"]

                if ts.tzinfo is None:
                    ts = timezone.make_aware(ts, timezone=timezone.utc)

                if ts > now_time:
                    remaining.append(f)

            if remaining:
                self.schedule_forecast_chain(action, remaining)

        except Exception as e:
            logger.error(f"Error executing forecast action {trigger_id}: {e}")

    def cleanup_old_forecast_triggers(self):
        """Remove old or inactive forecast triggers (older than 2 days)."""
        cutoff = timezone.now() - timedelta(days=2)
        deleted, _ = ActionTrigger.objects.filter(
            type="forecast",
            isActive=False,
            createdAt__lt=cutoff
        ).delete()
        if deleted:
            logger.debug(f"Cleaned up {deleted} old forecast triggers.")
