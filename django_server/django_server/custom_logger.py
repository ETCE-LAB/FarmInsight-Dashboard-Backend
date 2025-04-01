import logging


class DatabaseLogHandler(logging.Handler):
    def emit(self, record):
        from farminsight_dashboard_backend.models.log_message import LogMessage

        resource_id = getattr(record, 'resource_id', None)

        try:
            LogMessage.objects.create(
                message=self.format(record),
                logLevel=record.levelname,
                relatedResourceId=resource_id,
            )
        except Exception as e:
            print(e)
            pass # ignore here, to log somewhere to file in another logger as backup
