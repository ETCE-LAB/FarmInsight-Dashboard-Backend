from farminsight_dashboard_backend.models import Notification
from farminsight_dashboard_backend.serializers.notification_serializer import NotificationSerializer
from django_server.custom_logger import MatrixLogHandler


def create_notification(data) -> NotificationSerializer:
    serializer = NotificationSerializer(data=data)
    if serializer.is_valid(raise_exception=True):
        serializer.save()
        # Invalidiere den Cache damit neue Räume sofort erkannt werden
        MatrixLogHandler.invalidate_cache()
        return serializer


def remove_notification(room_id: str):
    notification = Notification.objects.get(room_id=room_id)
    notification.delete()
    # Invalidiere den Cache damit der Raum sofort entfernt wird
    MatrixLogHandler.invalidate_cache()


def get_all_notifications() -> NotificationSerializer:
    notifications = Notification.objects.all().order_by('name')
    return NotificationSerializer(notifications, many=True)
