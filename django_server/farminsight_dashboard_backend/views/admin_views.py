from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from farminsight_dashboard_backend.serializers import UserprofileSerializer
from farminsight_dashboard_backend.services import set_password_to_random_password, is_system_admin, all_userprofiles, \
    set_active_status
from rest_framework.decorators import api_view, permission_classes


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_reset_userprofile_password(request, userprofile_id: str):
    if not is_system_admin(request.user):
        return Response(status=status.HTTP_403_FORBIDDEN)

    new_password = set_password_to_random_password(userprofile_id)
    return Response(new_password)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_all_userprofiles(request):
    if not is_system_admin(request.user):
        return Response(status=status.HTTP_403_FORBIDDEN)

    return Response(all_userprofiles().data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def post_userprofile_active_status(request, userprofile_id: str):
    if not is_system_admin(request.user):
        Response(status=status.HTTP_403_FORBIDDEN)

    active = request.data['active']
    set_active_status(userprofile_id, active)

    return Response(status=status.HTTP_200_OK)
