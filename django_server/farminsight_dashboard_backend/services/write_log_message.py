from farminsight_dashboard_backend.models import LogMessage


def write_log_message(level: str, message: str, related_resource_id='', created_at = None):
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
