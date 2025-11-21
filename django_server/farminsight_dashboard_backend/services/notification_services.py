from farminsight_dashboard_backend.models import Notification
from farminsight_dashboard_backend.serializers.notification_serializer import NotificationSerializer


def create_notification(data) -> NotificationSerializer:
    serializer = NotificationSerializer(data=data)
    if serializer.is_valid(raise_exception=True):
        serializer.save()
        return serializer


def remove_notification(room_id: str):
    notification = Notification.objects.get(room_id=room_id)
    notification.delete()


def get_all_notifications() -> NotificationSerializer:
    notifications = Notification.objects.all().order_by('name')
    return NotificationSerializer(notifications, many=True)
