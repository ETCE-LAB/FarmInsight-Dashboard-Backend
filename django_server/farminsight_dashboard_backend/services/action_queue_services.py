from datetime import timedelta

from django.utils.timezone import now

from farminsight_dashboard_backend.models import ActionQueue, ControllableAction
from farminsight_dashboard_backend.services import get_controllable_action_by_id

from farminsight_dashboard_backend.services.action_trigger_services import get_all_active_auto_triggers
from farminsight_dashboard_backend.services.trigger.trigger_handler_factory import TriggerHandlerFactory
from farminsight_dashboard_backend.utils import get_logger
from farminsight_dashboard_backend.action_scripts import TypedActionScriptFactory

typed_action_script_factory = TypedActionScriptFactory()

logger = get_logger()

def get_active_state_of_action(controllable_action_id):
    """
    Get the active state (trigger) for an action.
    (Last executed action is the currently active action)
    :param controllable_action_id:
    :return:
    """

    last_action =  ActionQueue.objects.filter(
        action__id=controllable_action_id,
        endedAt__isnull=False,
        startedAt__isnull=False,
    ).order_by('createdAt').last()

    if last_action is None:
        return None

    # For auto actions, return them always. (we check here anyway if the action has a matching isAutomated)
    if last_action.trigger.type != 'manual' and get_controllable_action_by_id(controllable_action_id).isAutomated:
        return last_action

    # Return manual action only if the action is in manual mode.
    # We need this to activate a manual trigger which was in auto mode.
    if last_action.trigger.type == 'manual' and not get_controllable_action_by_id(controllable_action_id).isAutomated:
        return last_action
    else:
        return None

def get_active_state_of_hardware(hardware_id):
    """
    Get the active state (trigger) for a hardware.
    (Last executed action is the currently active action)
    :param hardware_id:
    :return:
    """
    print(hardware_id)
    last_action = ActionQueue.objects.filter(
        action__hardware_id=hardware_id,
        endedAt__isnull=False,
        startedAt__isnull=False,
    ).order_by('createdAt').last()

    return last_action

def is_already_enqueued(trigger_id):
    """
    Return if the trigger is already enqueued in the queue but not started or finished yet.
    This prevents overloading the queue with the same action multiple times.
    :param trigger_id:
    :return:
    """
    return ActionQueue.objects.filter(
        trigger_id=trigger_id,
        endedAt__isnull=True,
        startedAt__isnull=True,
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

        # Don't execute if another action for the same hardware is still running
        if hardware is not None:
            last_action = ActionQueue.objects.filter(
                action__hardware=hardware,
                endedAt__isnull=False,
                startedAt__isnull=False,
            ).order_by('-endedAt').first()
            print(last_action)
            if last_action and last_action.endedAt > now():
                logger.info(
                    f"Skipping action {action.id} because hardware {hardware} is busy until {last_action.endedAt}")
                continue

            # Don't execute if other actions with the same hardware are on Manual mode while this one is on auto.
            manual_action = ActionQueue.objects.filter(
                action__hardware=hardware,
                trigger__type='manual',
                endedAt__isnull=False,
                startedAt__isnull=False,
            ).exclude(
                id=queue_entry.id
            ).order_by('createdAt').last()

            # No other active manual action for the same hardware when the action is in manual mode
            # when this action is in auto mode
            if manual_action and not manual_action.action.isAutomated and action.isAutomated:
                logger.info(
                    f"Skipping action {action.id} because hardware {hardware} has another action in MANUAL mode, which is blocking this auto trigger.")
                continue


        # Execute the action
        try:

            logger.info(f"Executing action {action.id} on hardware {hardware}", extra={'resource_id': action.FPF_id })
            queue_entry.startedAt = now()

            script = typed_action_script_factory.get_typed_action_script_class(str(action.actionClassId))
            script_class = script(action)
            script_class.run(trigger.actionValue)

            # Set endedAt with the given maximum duration of the action
            queue_entry.endedAt = now() + timedelta(seconds=action.maximumDurationSeconds or 0)
            queue_entry.save()
            logger.info(f"Finished executing action {action.id}", extra={'resource_id': action.FPF_id })

        except Exception as e:
            logger.error(f"Failed to execute action {action.id}: {str(e)}", extra={'resource_id': action.FPF_id })

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
    Returns if the given trigger id is a new one for the controllable action (or for the hardware) or not.
    We call this function to prevent spamming the queue with the same action multiple times.
    :return:
    """

    if get_controllable_action_by_id(action_id).hardware is not None:
        active_state = get_active_state_of_hardware(get_controllable_action_by_id(action_id).hardware.id)
    else:
        active_state = get_active_state_of_action(action_id)
    if active_state is None or active_state.trigger.id != trigger_id:
        return True
    return False