import json
from datetime import datetime

from farminsight_dashboard_backend.utils import get_logger
from farminsight_dashboard_backend.serializers import ActionQueueSerializer
from farminsight_dashboard_backend.services.trigger.base_trigger_handlers import BaseTriggerHandler

logger = get_logger()

class TimeOfDayTriggerHandler(BaseTriggerHandler):
    def should_trigger(self):
        """
        :return:
        """
        try:
            logic = json.loads(self.trigger.triggerLogic)
            now = datetime.now().time()

            from_time = datetime.strptime(logic["from"], "%H:%M").time()
            to_time = datetime.strptime(logic["to"], "%H:%M").time()

            # Handle range that crosses midnight
            if from_time <= to_time:
                in_range = from_time <= now <= to_time
            else:
                # e.g., 23:00 to 03:00
                in_range = now >= from_time or now <= to_time

            return in_range

        except Exception as e:
            print(f"[TimeOfDayTriggerHandler] Error parsing trigger logic: {e}")
            return False

    def enqueue_if_needed(self):
        from farminsight_dashboard_backend.services.action_queue_services import is_new_action, process_action_queue
        if self.should_trigger() and self.trigger.action.isAutomated:
            if is_new_action(self.trigger.action.id, self.trigger.id):
                serializer = ActionQueueSerializer(data={
                    "actionId": str(self.trigger.action.id),
                    "actionTriggerId": str(self.trigger.id),
                    "value": str(self.trigger.actionValue),
                }, partial=True)
                if serializer.is_valid(raise_exception=True):
                    serializer.save()
                    logger.info(f"Queued timeOfDay trigger {self.trigger.id}", extra={'resource_id': self.trigger.action.FPF_id})


