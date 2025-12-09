import logging
import asyncio
import os

from asgiref.sync import sync_to_async
from django.conf import settings

from enum import Enum
from .matrix_notifier import matrix_client, send_matrix_notification_sync

# Farbzuordnung für verschiedene Log-Level
LOG_LEVEL_COLORS = {
    'INFO': '#36a64f',      # Grün
    'WARNING': '#ffc107',   # Gelb
    'ERROR': '#dc3545',     # Rot
    'CRITICAL': '#dc3545',  # Rot
    'DEBUG': '#ff00ff',     # Magenta
}

class LogCategory(Enum):
    GENERAL = 'General'

    SYSTEM = 'System'
    ACTION = 'Action'
    DATABASE = 'Database'
    SENSOR = 'Sensor'
    FORECAST = 'Forecast'
    MODEL = 'Model'
    CAMERA = 'Camera'
    EMAIL = 'Email'

class MatrixLogHandler(logging.Handler):
    def __init__(self, level=logging.NOTSET):
        super().__init__(level)

    def emit(self, record: logging.LogRecord):
        """Sucht den korrekten Raum und sendet den Log-Eintrag an Matrix."""
        # Verhindert eine Endlosschleife, indem Logs vom Notifier selbst ignoriert werden.
        if 'nio' in record.name or 'matrix_notifier' in record.name:
            return
        from farminsight_dashboard_backend.models import Notification

        if not matrix_client.loop or not matrix_client.is_running:
            return

        get_room_ids_async = sync_to_async(list, thread_sensitive=True)
        send_matrix_notification_async = sync_to_async(send_matrix_notification_sync, thread_sensitive=True)

        try:
            plain_text = f"{record.getMessage()}"

            color = LOG_LEVEL_COLORS.get(record.levelname, '#6c757d')

            category = getattr(record, 'category', None)

            log_category = (f'<font color="#ffffff">'
                            f'<strong>Category: [{category.value}]</strong>'
                            f'</font>') if category is not None else ""

            html_body = (
                f'<p><font color="{color}"><strong>{record.levelname}</strong></font></p>'
                f'{log_category}'
                f'<font color="{'#ffffff'}">{plain_text}</font>'
                f'<p><font color="{'#aaaaaa'}"><em>Function: {record.funcName} File: {os.path.splitext(record.filename)[0]}:{record.lineno}</em></font></p>'
            )
        async def _async_emit():
            try:
                room_ids = await get_room_ids_async(Notification.objects.values_list('room_id', flat=True))
                if not room_ids:
                    return
            except Exception as e:
                print(f"MatrixLogHandler failed to query Notification rooms: {e}")
                return

            try:
                plain_text = f"{record.getMessage()}"
                color = LOG_LEVEL_COLORS.get(record.levelname, '#6c757d')
                html_body = (
                    f'<p><font color="{color}"><strong>{record.levelname}</strong></font></p>'
                    f'<font color="{'#ffffff'}">{plain_text}</font>'
                    f'<p><font color="{'#aaaaaa'}"><em>Function: {record.funcName} File: {os.path.splitext(record.filename)[0]}:{record.lineno}</em></font></p>'
                )

                for room_id in room_ids:
                    await send_matrix_notification_async(room_id, plain_text, html_body)

            except Exception as e:
                print(f"FATAL: Failed to send log to Matrix from handler: {e}")

        asyncio.run_coroutine_threadsafe(_async_emit(), matrix_client.loop)


class DatabaseLogHandler(logging.Handler):
    def __init__(self, level=logging.NOTSET):
        super().__init__(level)

    def emit(self, record):
        # This is a placeholder for the actual database logging implementation
        pass
