
from farminsight_dashboard_backend.utils import get_logger
from farminsight_dashboard_backend.serializers import ActionQueueSerializer
from farminsight_dashboard_backend.services.trigger.base_trigger_handlers import BaseTriggerHandler

logger = get_logger()

class ManualTriggerHandler(BaseTriggerHandler):
    def should_trigger(self):
        # Manual triggers are always ready when created
        return True

    def enqueue_if_needed(self):
        pass


def create_manual_triggered_action_in_queue(action_id, trigger_id):
    """
    When the user manually selects a manual button in the frontend, the trigger will be activated and
    an entry in the action queue will be created. (If no other actions for the same controllable actions are currently
    running.
    :param action_id:
    :param trigger_id:
    :return:
    """
    from farminsight_dashboard_backend.services.action_queue_services import is_new_action, process_action_queue
    from farminsight_dashboard_backend.services.action_trigger_services import get_action_trigger

    try:
        trigger = get_action_trigger(trigger_id)
        if trigger.isActive: #and is_new_action(action_id, trigger.id): Disabled for now.
            # We would need to check all controllable actions with the same hardware in the active state and maybe the
            # user want to trigger a manual action more than once in case of network failure.

            serializer = ActionQueueSerializer(data={
                "actionId": action_id,
                "actionTriggerId": trigger_id,
                "value": trigger.actionValue,
            }, partial=True)
            if serializer.is_valid(raise_exception=True):
                serializer.save()
                logger.debug(f"Queued auto trigger {trigger_id} for action {action_id}", extra={'resource_id': trigger.action.FPF_id})

        process_action_queue()

    except Exception as e:
        logger.error(f"Failed to add action {action_id}: {str(e)}")
