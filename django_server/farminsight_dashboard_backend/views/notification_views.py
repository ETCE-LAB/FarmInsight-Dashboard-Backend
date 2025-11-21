from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from farminsight_dashboard_backend.utils import get_logger
from farminsight_dashboard_backend.serializers.notification_serializer import NotificationSerializer
from farminsight_dashboard_backend.services import (is_system_admin)
from farminsight_dashboard_backend.services.notification_services import (
    create_notification,
    remove_notification,
    get_all_notifications)

logger = get_logger()

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def post_notification(request):
    """
    POST /api/notifications

    Create a new notification room.

    Authentication: Required (Bearer token)
    Permissions: Only system admins can create notifications

    Request Body:
        {
            "room_id": "room_123",  // Required, unique identifier
            "name": "Main Notification Room"  // Required, display name
        }

    Returns:
        201 CREATED: Notification created successfully
            {
                "room_id": "room_123",
                "name": "Main Notification Room"
            }
        403 FORBIDDEN: User is not a system admin
        400 BAD REQUEST: Invalid data (missing fields, duplicate room_id)

    Flow:
        1. Check if user is authenticated
        2. Check if user is system admin
        3. Validate request data
        4. Create notification in database
        5. Return created notification
    """
    if not is_system_admin(request.user):
        return Response(
            {"detail": "Only system administrators can create notification rooms."},
            status=status.HTTP_403_FORBIDDEN
        )

    notification = create_notification(request.data)
    return Response(notification.data, status=status.HTTP_201_CREATED)

@api_view(['GET'])
def get_notifications(request):
    serializer = get_all_notifications()
    return Response(serializer.data, status=status.HTTP_200_OK)



class NotificationView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, room_id):
        if not is_system_admin(request.user):
            return Response(
                {"detail": "Only system administrators can delete notification rooms."},
                status=status.HTTP_403_FORBIDDEN
            )

        remove_notification(room_id)
        return Response(status=status.HTTP_200_OK)
