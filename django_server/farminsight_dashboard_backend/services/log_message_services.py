from farminsight_dashboard_backend.models import LogMessage
from farminsight_dashboard_backend.serializers.log_message_serializer import LogMessageSerializer


def write_log_message(level: str, message: str, related_resource_id='', created_at=None):
    if created_at is None:
        log_message = LogMessage(
            logLevel=level,
            message=message,
            relatedResourceId=related_resource_id,
        )
    else:
        log_message = LogMessage(
            logLevel=level,
            message=message,
            relatedResourceId=related_resource_id,
            createdAt=created_at,
        )

    log_message.save()


def get_log_messages_by_amount(resource_id: str, amount: int) -> LogMessageSerializer:
    messages = LogMessage.objects.filter(relatedResourceId=resource_id).order_by('-createdAt')[:amount]
    return LogMessageSerializer(messages, many=True)


def get_log_messages_by_date(resource_id: str, dt_from, dt_to=None) -> LogMessageSerializer:
    messages = LogMessage.objects.filter(relatedResourceId=resource_id, createdAt__gt=dt_from)
    if dt_to is not None:
        messages = messages.filter(createdAt__lt=dt_to)
    return LogMessageSerializer(messages.order_by('-createdAt'), many=True)
