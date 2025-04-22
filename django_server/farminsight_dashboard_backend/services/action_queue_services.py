from django.utils.timezone import now
import logging
import importlib
import json
from datetime import datetime, timedelta

from farminsight_dashboard_backend.models import ActionQueue, ControllableAction
from farminsight_dashboard_backend.serializers import ActionQueueSerializer
from farminsight_dashboard_backend.utils import get_logger
from farminsight_dashboard_backend.action_scripts import TypedActionScriptFactory

typed_action_script_factory = TypedActionScriptFactory()

logger = get_logger()

def get_active_action_for_hardware(hardware):
    # Return the oldest unfinished (active) action for this hardware
    return ActionQueue.objects.filter(
        action__hardware=hardware,
        endedAt__isnull=True
    ).order_by('createdAt').first()



def is_blocked_by_manual_trigger(hardware, current_entry=None):
    if current_entry is None:
        return False

    # Only check if the current trigger is a manual one
    if current_entry.trigger.type != 'manual':
        return False

    # Get all pending manual triggers for this hardware, ordered by creation time
    manual_entries = ActionQueue.objects.filter(
        action__hardware=hardware,
        trigger__type='manual',
        endedAt__isnull=True,
    ).order_by('createdAt')

    # Allow only the oldest one (i.e., the first in the ordered list) to proceed
    if manual_entries and manual_entries.first().id != current_entry.id:
        return True  # block if current_entry is not the first
    return False


def process_action_queue():
    """

    :return:
    """
    pending_actions = ActionQueue.objects.filter(endedAt__isnull=True).order_by('createdAt')

    for queue_entry in pending_actions:
        action = queue_entry.action
        trigger = queue_entry.trigger
        hardware = action.hardware

        if is_blocked_by_manual_trigger(hardware, current_entry=queue_entry):
            logger.info(f"Hardware '{hardware}' is blocked by another manual trigger.")
            continue

        active_action = get_active_action_for_hardware(hardware)
        if active_action and active_action.id != queue_entry.id:
            logger.info(f"Hardware '{hardware}' is currently executing another action: {active_action.id}")
            continue  # block this one until the earlier is finished

        if not action.isActive:
            logger.info(f"Skipping action {action.id} because it is not active.")
            continue

        try:
            logger.info(f"Executing action {action.id} on hardware {hardware}")
            queue_entry.startedAt = now()
            queue_entry.save()

            script = typed_action_script_factory.get_typed_action_script_class(str(action.actionClassId))
            script_class = script(action)
            script_class.run(trigger.actionValue)

            queue_entry.endedAt = now()
            queue_entry.save()

            logger.info(f"Finished executing action {action.id}")
        except Exception as e:
            logger.error(f"Failed to execute action {action.id}: {str(e)}")

            # Consider it done anyway for now.
            queue_entry.endedAt = now()
            queue_entry.save()



def create_action_in_queue(action_queue_item)-> None:
    """
    Create a new action(s) in the action queue.

    If the controllable action is set to isAutomated:
    - all active automatic actions are added to the queue

    If isAutomated is False:
    - all running automatic actions will be set to completed
    - the given manual trigger is added to the queue

    If the action is automated, enqueue all non-manual triggers.
    If the action is manual, enqueue it and end any active non-manual queue entries for the same action.
    """
    logger.debug(f"Creating action in queue with: {action_queue_item}")

    action_id = action_queue_item.get("actionId")
    trigger_id = action_queue_item.get("actionTriggerId")

    if not action_id:
        logger.error("Missing 'actionId' in input")
        return None

    try:
        controllable_action = ControllableAction.objects.get(id=action_id)
    except ControllableAction.DoesNotExist:
        logger.error(f"ControllableAction with id={action_id} not found")
        return None

    if controllable_action.isAutomated:
        logger.info(f"ControllableAction {action_id} is in automated mode. Adding all non-manual triggers to queue.")

        non_manual_active_triggers = controllable_action.triggers.filter(
            isActive=True
        ).exclude(
            type='manual'
        )

        for trigger in non_manual_active_triggers:
            serializer = ActionQueueSerializer(data={
                "actionId": str(controllable_action.id),
                "actionTriggerId": str(trigger.id),
            }, partial=True)

            if serializer.is_valid(raise_exception=True):
                serializer.save()
                logger.debug(f"Queued auto trigger {trigger.id} for action {action_id}")
            else:
                logger.warning(f"Failed to queue trigger {trigger.id}: {serializer.errors}")
    else:
        logger.info(f"ControllableAction {action_id} is in manual mode. Preparing to queue manual action.")

        # End all unfinished non-manual queue entries for this action
        unfinished_non_manual = ActionQueue.objects.filter(
            action=controllable_action,
            endedAt__isnull=True,
        ).exclude(trigger__type='manual')

        updated = unfinished_non_manual.update(endedAt=now())
        logger.info(f"Ended {updated} unfinished non-manual queue entries for action {action_id}")

        # Now add the manual action to the queue
        serializer = ActionQueueSerializer(data=action_queue_item, partial=True)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            logger.debug(f"Queued manual action with trigger {trigger_id}")
        else:
            logger.error(f"Failed to queue manual action: {serializer.errors}")




def get_active_state(controllable_action_id: str):
    # Get the most recent queue entry for this action (whether ended or still running)
    latest_entry = ActionQueue.objects.filter(
        action__id=controllable_action_id
    ).order_by('-endedAt', '-createdAt').first()

    if latest_entry:
        return latest_entry.trigger

    return None
