import logging
import asyncio
import os

from django.conf import settings


from .matrix_notifier import send_matrix_notification, matrix_client, send_matrix_notification_sync

# Farbzuordnung für verschiedene Log-Level zur besseren visuellen Darstellung
LOG_LEVEL_COLORS = {
    'INFO': '#36a64f',      # Grün
    'WARNING': '#ffc107',   # Gelb
    'ERROR': '#dc3545',     # Rot
    'CRITICAL': '#dc3545',  # Rot
    'DEBUG': '#ff00ff',     # Magenta
}


class MatrixLogHandler(logging.Handler):
    def __init__(self, level=logging.NOTSET):
        super().__init__(level)

    def emit(self, record: logging.LogRecord):
        """Sucht den korrekten Raum und sendet den Log-Eintrag an Matrix."""
        # Verhindert eine Endlosschleife, indem Logs vom Notifier selbst ignoriert werden.
        if 'nio' in record.name or 'matrix_notifier' in record.name:
            return
        from farminsight_dashboard_backend.models import Notification

        try:
            room_ids = list(Notification.objects.values_list('room_id', flat=True))
            if not room_ids:
                return
        except Exception as e:
            print(f"MatrixLogHandler failed to query Notification rooms: {e}")
            return

        if not matrix_client.loop or not matrix_client.is_running:
            print(f"[Matrix not ready] {self.format(record)}")
            return


        try:
            plain_text = f"{record.getMessage()}"

            color = LOG_LEVEL_COLORS.get(record.levelname, '#6c757d')

            html_body = (
                f'<p><font color="{color}"><strong>{record.levelname}</strong></font></p>'
                f'<font color="{'#ffffff'}">{plain_text}</font>'
                f'<p><font color="{'#aaaaaa'}"><em>File: {os.path.splitext(record.filename)[0]}:{record.lineno}</em></font></p>'
            )

            coroutines = []
            for room_id in room_ids:
                send_matrix_notification_sync(room_id, plain_text, html_body)


            if coroutines:
                bundled_coro = asyncio.gather(*coroutines)
                asyncio.run_coroutine_threadsafe(bundled_coro, matrix_client.loop)

        except RuntimeError as e:
            # Hier vorsichtig loggen, um keine Schleife zu erzeugen.
            # Ein print ist hier sicherer als logger.error.
            print(f"FATAL: Failed to send log to Matrix from handler: {e}")


class DatabaseLogHandler(logging.Handler):
    def __init__(self, level=logging.NOTSET):
        super().__init__(level)

    def emit(self, record):
        # This is a placeholder for the actual database logging implementation
        pass
