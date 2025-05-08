from django.utils.timezone import now

from farminsight_dashboard_backend.models import ActionQueue

from farminsight_dashboard_backend.services.action_trigger_services import get_all_active_auto_triggers
from farminsight_dashboard_backend.services.trigger.trigger_handler_factory import TriggerHandlerFactory
from farminsight_dashboard_backend.utils import get_logger
from farminsight_dashboard_backend.action_scripts import TypedActionScriptFactory

typed_action_script_factory = TypedActionScriptFactory()

logger = get_logger()

def get_active_state_of_action(action_id):
    """
    Get the active state (trigger) for an action.
    (Last executed action is the currently active action)
    :param action_id:
    :return:
    """
    return ActionQueue.objects.filter(
        action__id=action_id,
        endedAt__isnull=False,
        startedAt__isnull=False,
    ).order_by('createdAt').last()

def process_action_queue():
    """
    Iterates through all the not finished triggers and processes them (checks if the trigger still triggers and if the
    action is executable)

    :return:
    """

    # Filter out finished and cancelled actions
    pending_actions = ActionQueue.objects.filter(endedAt__isnull=True, startedAt__isnull=True).order_by('createdAt')

    for queue_entry in pending_actions:
        action = queue_entry.action
        trigger = queue_entry.trigger
        hardware = action.hardware

        # Don't execute actions for inactive controllable action
        if not action.isActive:
            logger.info(f"Skipping action {action.id} because it is not active.")
            continue

        # Don't execute auto actions if manual action is active, cancel the auto action in the queue
        # New auto action would need to be triggered again
        if trigger.type != 'manual' and not action.isAutomated:
            logger.info(f"Cancel auto action {action.id} because action is set to manual.")
            queue_entry.endedAt = now()
            queue_entry.save()
            continue

        # TODO - Don't execute if another action for the same hardware is still running

        # If the trigger action is already active skip it.
        # Cancel it. This should never happen anyway, actually.
        #if not is_new_action(action.id, trigger.id):
        #    logger.info(f"Trigger '{trigger}' action is already active for this action.")
        #    queue_entry.endedAt = now()
        #    queue_entry.save()
        #    continue

        # Execute the action
        try:

            logger.info(f"Executing action {action.id} on hardware {hardware}")
            queue_entry.startedAt = now()

            script = typed_action_script_factory.get_typed_action_script_class(str(action.actionClassId))
            script_class = script(action)
            script_class.run(trigger.actionValue)

            queue_entry.endedAt = now()
            queue_entry.save()
            logger.info(f"Finished executing action {action.id}")

        except Exception as e:
            logger.error(f"Failed to execute action {action.id}: {str(e)}")

def create_auto_triggered_actions_in_queue(action_id=None):
    try:
        auto_triggers = get_all_active_auto_triggers(action_id)

        for auto_trigger in auto_triggers:
            handler = TriggerHandlerFactory.get_handler(auto_trigger)
            handler.enqueue_if_needed()

        process_action_queue()

    except Exception as e:
        logger.error(f"Failed to add action {action_id}: {str(e)}")


def get_active_state(controllable_action_id: str):
    """
    Get the most recent queue entry for this action (whether ended or still running)
    :param controllable_action_id:
    :return:
    """
    latest_entry = ActionQueue.objects.filter(
        action__id=controllable_action_id
    ).order_by('-endedAt', '-createdAt').first()

    if latest_entry:
        return latest_entry.trigger
    return None

def is_new_action(action_id, trigger_id):
    """
    Returns if the given trigger id is a new one for the action or not.
    :return:
    """
    active_state = get_active_state_of_action(action_id)
    if active_state is None or active_state.trigger.id != trigger_id:
        return True
    return False