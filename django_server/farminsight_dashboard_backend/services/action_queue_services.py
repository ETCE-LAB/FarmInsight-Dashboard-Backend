from django.utils.timezone import now

from farminsight_dashboard_backend.models import ActionQueue, ControllableAction, ActionTrigger
from farminsight_dashboard_backend.serializers import ActionQueueSerializer
from farminsight_dashboard_backend.services.action_trigger_services import get_all_auto_action_triggers, get_action_trigger
from farminsight_dashboard_backend.services.trigger_handlers import TriggerHandlerFactory
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
    pending_actions = ActionQueue.objects.filter(endedAt__isnull=True).order_by('createdAt')

    for queue_entry in pending_actions:
        action = queue_entry.action
        trigger = queue_entry.trigger
        hardware = action.hardware

        # Don't execute actions for inactive controllable action
        if not action.isActive:
            logger.info(f"Skipping action {action.id} because it is not active.")
            continue

        # Don't execute auto actions if manual action is active
        if trigger.type != 'manual' and not action.isAutomated:
            logger.info(f"Skipping auto action {action.id} because action is set to manual.")
            continue

        # TODO - Don't execute if another action for the same hardware is still running

        # If the trigger action is already active skip it.
        if not is_new_action(action.id, trigger.id):
            logger.info(f"Trigger '{trigger}' action is already active for this action.")
            continue

        # Execute the action
        try:
            handler = TriggerHandlerFactory.get_handler(trigger)

            # Recheck if the trigger still triggers, else delete the entry
            if handler.should_trigger():
                logger.info(f"Executing action {action.id} on hardware {hardware}")
                queue_entry.startedAt = now()

                script = typed_action_script_factory.get_typed_action_script_class(str(action.actionClassId))
                script_class = script(action)
                script_class.run(trigger.actionValue)

                queue_entry.endedAt = now()
                queue_entry.save()
                logger.info(f"Finished executing action {action.id}")
            else:
                queue_entry.delete()
                logger.info(f"Deleted entry from action queue {queue_entry} for action {action.id} because the trigger did no longer trigger.")

        except Exception as e:
            logger.error(f"Failed to execute action {action.id}: {str(e)}")


def create_auto_triggered_actions_in_queue(action_id=None):
    """
    This function will be called periodically and checks for all existing, active auto-triggers if they are triggering.
    Trigger Type Logic will be called to check if it triggers and
    the action queue will be checked that this trigger is not already active.
    If a trigger triggers, an entry in the action queue will be created.
    After all auto triggers are processed, process the action queue to start the actions.

    An action_id can be passed to call the process only for one action. This will happen when the user actively selects the
    "AUTO" button in the frontend.
    :return:
    """
    try:
        auto_triggers = get_all_auto_action_triggers(action_id)

        for auto_trigger in auto_triggers:
            # Trigger type logic to check for triggering && currently active trigger for the action must not be this trigger.
            handler = TriggerHandlerFactory.get_handler(auto_trigger)
            if handler.should_trigger() and auto_trigger.action.isAutomated:
                if is_new_action(auto_trigger.action.id, auto_trigger.id):
                    serializer = ActionQueueSerializer(data={
                                    "actionId": str(auto_trigger.action.id),
                                    "actionTriggerId": str(auto_trigger.id),
                                }, partial=True)
                    if serializer.is_valid(raise_exception=True):
                            serializer.save()
                            logger.info(f"Queued auto trigger {auto_trigger.id} for action {auto_trigger.action.id}")

        process_action_queue()

    except Exception as e:
        logger.error(f"Failed to add action {action_id}: {str(e)}")

def create_manual_triggered_action_in_queue(action_id, trigger_id):
    """
    When the user manually selects a manual button in the frontend, the trigger will be activated and
    an entry in the action queue will be created. (If no other actions for the same controllable actions are currently
    running.
    :param action_id:
    :param trigger_id:
    :return:
    """
    try:
        trigger = get_action_trigger(trigger_id)
        if trigger.isActive and is_new_action(action_id, trigger.id):
            serializer = ActionQueueSerializer(data={
                "actionId": action_id,
                "actionTriggerId": trigger_id,
            }, partial=True)
            if serializer.is_valid(raise_exception=True):
                serializer.save()
                logger.debug(f"Queued auto trigger {trigger_id} for action {action_id}")

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