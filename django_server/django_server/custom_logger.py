import logging


class DatabaseLogHandler(logging.Handler):
    def emit(self, record):
        from farminsight_dashboard_backend.models.log_message import LogMessage

        resource_id = getattr(record, 'resource_id', None)

        try:
            '''
            Messages coming straight from django itself are in async context because we're using channels and daphne
            and thus can't synchronously write to the DB, so just using the acreate function in this case.
            '''
            LogMessage.objects.acreate(
                message=self.format(record),
                logLevel=record.levelname,
                relatedResourceId=resource_id,
            )
            return
        except Exception as e:
            # print(f'DatabaseLogHandler: {e}')
            pass
