from apscheduler.schedulers.background import BackgroundScheduler
import json
from datetime import timedelta
from django.utils.timezone import now

from farminsight_dashboard_backend.utils import get_logger
from farminsight_dashboard_backend.serializers import ActionQueueSerializer
from farminsight_dashboard_backend.services.trigger.base_trigger_handlers import BaseTriggerHandler

logger = get_logger()

scheduler = BackgroundScheduler()
scheduler.start()

class IntervalTriggerHandler(BaseTriggerHandler):
    def should_trigger(self, interval, **kwargs):
        pass

    def enqueue_if_needed(self):
        logic = json.loads(self.trigger.triggerLogic)
        delay = logic.get("delayInSeconds", 0)

        interval = delay + int(json.loads(self.trigger.action.additionalInformation).get("delay", 0))

        job_id = f"interval_trigger_{self.trigger.id}"

        if scheduler.get_job(job_id):
            return

        scheduler.add_job(
            func=enqueue_interval_action,
            args=[self.trigger.id],
            id=job_id,
            trigger="interval",
            seconds=interval,
            next_run_time=now() + timedelta(seconds=delay)
        )


def enqueue_interval_action(trigger_id):
    """
    Add the action to the queue and process the queue
    :param trigger_id:
    :return:
    """
    from farminsight_dashboard_backend.services.action_trigger_services import get_action_trigger
    from farminsight_dashboard_backend.services.action_queue_services import process_action_queue, is_already_enqueued

    trigger = get_action_trigger(trigger_id)

    if trigger and trigger.action.isAutomated and trigger.isActive:
        # Only enqueue if the action is new (there must not be a created action by the same trigger in the queue, which has not ended yet.)
        if not is_already_enqueued(trigger_id):
            serializer = ActionQueueSerializer(data={
                "actionId": str(trigger.action.id),
                "actionTriggerId": str(trigger.id),
                "value": trigger.actionValue
            }, partial=True)

            if serializer.is_valid(raise_exception=True):
                serializer.save()
                logger.info(f"Queued by interval trigger {trigger.description} with value {trigger.actionValue}", extra={'resource_id': trigger.action.id})

            process_action_queue()